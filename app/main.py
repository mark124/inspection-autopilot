"""Inspection Autopilot: FastAPI backend.

Endpoints drive the full loop: ingest a batch of new inspections, run the
Qwen triage agent, queue proposals for human approval, record decisions.
"""
from __future__ import annotations

from pathlib import Path
from typing import Optional

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel

from .qwen import QwenClient
from .rules import RULES, auto_approve
from .store import ProposalStore, SourceData
from .triage import run_inspection

app = FastAPI(title="Inspection Autopilot")

source = SourceData()
store = ProposalStore()
client = QwenClient()

UI_DIR = Path(__file__).resolve().parent.parent / "ui"


class DecideBody(BaseModel):
    decision: str  # approved | rejected
    decided_by: str = "supervisor"


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
    if batch < 1 or batch > 50:
        raise HTTPException(400, "batch must be 1-50")
    done = store.processed_inspection_ids()

    def key(d: str) -> str:
        try:
            m, day, y = d.split("-")
            return f"{y}-{m}-{day}"
        except ValueError:
            return d

    todo = sorted((i for i in source.inspections.values() if i.inspection_id not in done),
                  key=lambda i: key(i.date), reverse=True)[:batch]

    results = []
    n_props = 0
    for insp in todo:
        viols = source.violations.get(insp.inspection_id, [])
        triage, actions, dropped = run_inspection(insp, source, client)
        for act in actions:
            rule = auto_approve(triage, act, insp, viols)
            pid = store.add_proposal(
                inspection_id=insp.inspection_id, facility_id=insp.facility_id,
                facility_name=insp.name, risk_tier=triage.risk_tier,
                action_type=act.action_type, params=act.params,
                draft_text=act.draft_text,
                rationale=(act.rationale or triage.rationale),
                citations=triage.citations,
                source=f"rule:{rule}" if rule else f"agent:{client.mode}",
                auto_approved=rule is not None)
            n_props += 1
        results.append({"inspection_id": insp.inspection_id, "facility": insp.name,
                        "date": insp.date, "score": insp.score,
                        "risk_tier": triage.risk_tier, "n_actions": len(actions),
                        "dropped_citations": dropped})
    store.record_run(client.mode, client.model, len(todo), n_props)
    return {"processed": results, "mode": client.mode}


@app.get("/api/proposals")
def proposals(status: Optional[str] = None):
    return {"proposals": [p.model_dump() for p in store.list_proposals(status)]}


@app.post("/api/proposals/{proposal_id}/decide")
def decide(proposal_id: int, body: DecideBody):
    if body.decision not in ("approved", "rejected"):
        raise HTTPException(400, "decision must be approved or rejected")
    ok = store.decide(proposal_id, body.decision, body.decided_by)
    if not ok:
        raise HTTPException(409, "unknown proposal or already decided (decisions are final)")
    return {"ok": True}
