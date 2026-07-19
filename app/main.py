"""Inspection Autopilot: FastAPI backend.

Endpoints drive the full loop: ingest a batch of new inspections, run the
Qwen triage agent, queue proposals for human approval, record decisions,
and roll approved rechecks up into the inspector's schedule.
"""
from __future__ import annotations

import json
import logging
import os
import threading
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse

from .qwen import QwenClient
from .rules import RULES, auto_approve
from .schemas import DecideBody
from .store import ProposalStore, SourceData
from .triage import build_fact_sheet, run_inspection

logging.basicConfig(level=logging.INFO,
                    format="%(asctime)s %(levelname)s %(name)s: %(message)s")
log = logging.getLogger("autopilot")

app = FastAPI(title="Inspection Autopilot")

source = SourceData()
store = ProposalStore()
client = QwenClient()

UI_DIR = Path(__file__).resolve().parent.parent / "ui"
OUTCOMES_PATH = Path(__file__).resolve().parent.parent / "evals" / "backtest_results.json"

# single-flight guard: the public demo must never double-process a batch
_run_lock = threading.Lock()

MAX_RUNS_PER_DAY = int(os.environ.get("MAX_RUNS_PER_DAY", "50"))


def _date_key(d: str) -> str:
    try:
        m, day, y = d.split("-")
        return f"{y}-{m}-{day}"
    except ValueError:
        return d


@app.get("/")
def index():
    return FileResponse(UI_DIR / "index.html")


@app.get("/api/health")
def health():
    return {"ok": True, "mode": client.mode, "model": client.model,
            "facilities": len(source.facilities), "inspections": len(source.inspections)}


@app.get("/api/rules")
def rules():
    return {"rules": RULES}


@app.get("/api/stats")
def stats():
    return store.stats()


@app.post("/api/run")
def run_batch(batch: int = 5):
    """Process the next `batch` unprocessed inspections (most recent first)."""
    if batch < 1 or batch > 10:
        raise HTTPException(400, "batch must be 1-10")
    if store.runs_today() >= MAX_RUNS_PER_DAY:
        raise HTTPException(429, "daily agent-run budget reached; the queue and log remain browsable")
    if not _run_lock.acquire(blocking=False):
        raise HTTPException(409, "an agent run is already in progress; try again in a moment")
    try:
        done = store.processed_inspection_ids()
        unprocessed = [i for i in source.inspections.values() if i.inspection_id not in done]
        todo = sorted(unprocessed, key=lambda i: _date_key(i.date), reverse=True)[:batch]

        results = []
        n_props = 0
        total_dropped = 0
        n_errors = 0
        consecutive_errors = 0
        log.info("run start: batch=%d mode=%s", len(todo), client.mode)
        for insp in todo:
            try:
                viols = source.violations.get(insp.inspection_id, [])
                triage, actions, dropped = run_inspection(insp, source, client)
            except Exception as e:
                # failed inspections create no proposals, so the next run retries them
                log.exception("inspection %s (%s) failed", insp.inspection_id, insp.name)
                n_errors += 1
                consecutive_errors += 1
                results.append({"inspection_id": insp.inspection_id, "facility": insp.name,
                                "date": insp.date, "score": insp.score,
                                "error": str(e)[:200]})
                if consecutive_errors >= 3:
                    log.warning("3 consecutive failures; stopping batch early")
                    break
                continue
            consecutive_errors = 0
            total_dropped += dropped
            for act in actions:
                rule = auto_approve(triage, act, insp, viols)
                store.add_proposal(
                    inspection_id=insp.inspection_id, facility_id=insp.facility_id,
                    facility_name=insp.name, risk_tier=triage.risk_tier,
                    action_type=act.action_type, params=act.params,
                    draft_text=act.draft_text,
                    rationale=(act.rationale or triage.rationale),
                    citations=triage.citations,
                    source=f"rule:{rule}" if rule else f"agent:{client.mode}",
                    auto_approved=rule is not None)
                n_props += 1
            log.info("inspection %s: tier=%s actions=%d dropped_citations=%d",
                     insp.inspection_id, triage.risk_tier, len(actions), dropped)
            results.append({"inspection_id": insp.inspection_id, "facility": insp.name,
                            "date": insp.date, "score": insp.score,
                            "risk_tier": triage.risk_tier, "n_actions": len(actions),
                            "dropped_citations": dropped})
        store.record_run(client.mode, client.model, len(todo), n_props, total_dropped)
        return {"processed": results, "mode": client.mode, "n_errors": n_errors,
                "remaining": len(unprocessed) - len(todo)}
    finally:
        _run_lock.release()


@app.get("/api/proposals")
def proposals(status: Optional[str] = None):
    out = []
    for p in store.list_proposals(status):
        d = p.model_dump()
        insp = source.inspections.get(p.inspection_id)
        d["score"] = insp.score if insp else None
        d["inspection_date"] = insp.date if insp else None
        out.append(d)
    return {"proposals": out}


@app.post("/api/proposals/{proposal_id}/decide")
def decide(proposal_id: int, body: DecideBody):
    ok = store.decide(proposal_id, body.decision, body.decided_by)
    if not ok:
        raise HTTPException(409, "unknown proposal, already decided, or auto-approved by rule"
                                 " (decisions are final)")
    return {"ok": True}


@app.get("/api/inspections/{inspection_id}/record")
def inspection_record(inspection_id: int):
    """The exact fact sheet the agent read for this inspection (source of truth for citations)."""
    insp = source.inspections.get(inspection_id)
    if insp is None:
        raise HTTPException(404, "unknown inspection")
    return {"inspection_id": inspection_id, "text": build_fact_sheet(insp, source)}


@app.get("/api/schedule")
def schedule():
    """Approved re-inspections as a dated, risk-ordered work queue."""
    tier_rank = {"URGENT": 0, "ELEVATED": 1, "ROUTINE": 2}
    rows = []
    for p in store.list_proposals():
        if p.action_type != "schedule_reinspection" or p.status not in ("approved", "auto_approved"):
            continue
        window = p.params.get("window_days", 14)
        try:
            window = int(window)
        except (TypeError, ValueError):
            window = 14
        base = p.decided_at or p.created_at
        try:
            due = (datetime.fromisoformat(base) + timedelta(days=window)).date().isoformat()
        except ValueError:
            continue
        fac = source.facilities.get(p.facility_id)
        insp = source.inspections.get(p.inspection_id)
        rows.append({"due_date": due, "risk_tier": p.risk_tier,
                     "facility_name": p.facility_name,
                     "address": fac.address if fac else "",
                     "window_days": window,
                     "score": insp.score if insp else None,
                     "approved_by": p.decided_by or "automation rule",
                     "proposal_id": p.proposal_id})
    rows.sort(key=lambda r: (r["due_date"], tier_rank.get(r["risk_tier"], 9)))
    return {"schedule": rows}


@app.get("/api/outcomes")
def outcomes():
    """Cached outcome backtest: agent tiers vs what actually happened next."""
    if not OUTCOMES_PATH.exists():
        raise HTTPException(404, "backtest results not generated yet")
    return json.loads(OUTCOMES_PATH.read_text(encoding="utf-8"))
