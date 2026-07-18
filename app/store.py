"""Data access: read-only source records + append-only proposal/decision log.

Source inspection data (JSONL) is never mutated. All agent output and every
human decision are INSERTs; status is derived from the latest decision row.
"""
from __future__ import annotations

import json
import sqlite3
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from .schemas import Facility, Inspection, Proposal, Violation

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
DB_PATH = Path(__file__).resolve().parent.parent / "autopilot.db"

_lock = threading.Lock()


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _parse_score(raw) -> Optional[int]:
    try:
        return int(str(raw).strip())
    except (ValueError, TypeError):
        return None


class SourceData:
    """Read-only view of the county's inspection records."""

    def __init__(self, data_dir: Path = DATA_DIR):
        self.facilities: dict[str, Facility] = {}
        self.inspections: dict[int, Inspection] = {}
        self.violations: dict[int, list[Violation]] = {}

        with open(data_dir / "clayton_facilities.jsonl", encoding="utf-8") as f:
            for line in f:
                rec = json.loads(line)
                fac = Facility(**{k: rec.get(k, "") for k in
                                  ("facility_id", "name", "address", "permit_type", "permit_number")})
                self.facilities[fac.facility_id] = fac

        with open(data_dir / "clayton_inspections.jsonl", encoding="utf-8") as f:
            for line in f:
                rec = json.loads(line)
                rec["score"] = _parse_score(rec.get("score"))
                insp = Inspection(**rec)
                self.inspections[insp.inspection_id] = insp

        with open(data_dir / "clayton_violations.jsonl", encoding="utf-8") as f:
            for line in f:
                v = Violation(**json.loads(line))
                self.violations.setdefault(v.inspection_id, []).append(v)

    def history_for_facility(self, facility_id: str, before_date: str) -> list[Inspection]:
        """Prior inspections for a facility, sorted most recent first.

        Dates in the source are MM-DD-YYYY; convert for comparison.
        """
        def key(d: str) -> str:
            try:
                m, day, y = d.split("-")
                return f"{y}-{m}-{day}"
            except ValueError:
                return d

        cutoff = key(before_date)
        hist = [i for i in self.inspections.values()
                if i.facility_id == facility_id and key(i.date) < cutoff]
        return sorted(hist, key=lambda i: key(i.date), reverse=True)


class ProposalStore:
    """Append-only store: proposals and decisions are separate insert-only tables."""

    def __init__(self, db_path: Path = DB_PATH):
        self.db_path = db_path
        with self._conn() as c:
            c.executescript("""
                CREATE TABLE IF NOT EXISTS proposals (
                    proposal_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    inspection_id INTEGER NOT NULL,
                    facility_id TEXT NOT NULL,
                    facility_name TEXT NOT NULL,
                    risk_tier TEXT NOT NULL,
                    action_type TEXT NOT NULL,
                    params TEXT NOT NULL,
                    draft_text TEXT NOT NULL,
                    rationale TEXT NOT NULL,
                    citations TEXT NOT NULL,
                    source TEXT NOT NULL,
                    auto_approved INTEGER NOT NULL DEFAULT 0,
                    created_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS decisions (
                    decision_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    proposal_id INTEGER NOT NULL,
                    decision TEXT NOT NULL,
                    decided_by TEXT NOT NULL,
                    decided_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS runs (
                    run_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    started_at TEXT NOT NULL,
                    mode TEXT NOT NULL,
                    model TEXT NOT NULL,
                    n_inspections INTEGER NOT NULL,
                    n_proposals INTEGER NOT NULL
                );
            """)

    def _conn(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def add_proposal(self, inspection_id: int, facility_id: str, facility_name: str,
                     risk_tier: str, action_type: str, params: dict, draft_text: str,
                     rationale: str, citations: list[str], source: str,
                     auto_approved: bool = False) -> int:
        with _lock, self._conn() as c:
            cur = c.execute(
                "INSERT INTO proposals (inspection_id, facility_id, facility_name, risk_tier,"
                " action_type, params, draft_text, rationale, citations, source, auto_approved, created_at)"
                " VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
                (inspection_id, facility_id, facility_name, risk_tier, action_type,
                 json.dumps(params), draft_text, rationale, json.dumps(citations),
                 source, int(auto_approved), _now()))
            return cur.lastrowid

    def decide(self, proposal_id: int, decision: str, decided_by: str) -> bool:
        with _lock, self._conn() as c:
            row = c.execute("SELECT proposal_id FROM proposals WHERE proposal_id=?",
                            (proposal_id,)).fetchone()
            if row is None:
                return False
            existing = c.execute("SELECT decision_id FROM decisions WHERE proposal_id=?",
                                 (proposal_id,)).fetchone()
            if existing is not None:
                return False  # decisions are final; no overwrite
            c.execute("INSERT INTO decisions (proposal_id, decision, decided_by, decided_at)"
                      " VALUES (?,?,?,?)", (proposal_id, decision, decided_by, _now()))
            return True

    def record_run(self, mode: str, model: str, n_inspections: int, n_proposals: int) -> None:
        with _lock, self._conn() as c:
            c.execute("INSERT INTO runs (started_at, mode, model, n_inspections, n_proposals)"
                      " VALUES (?,?,?,?,?)", (_now(), mode, model, n_inspections, n_proposals))

    def processed_inspection_ids(self) -> set[int]:
        with self._conn() as c:
            return {r["inspection_id"] for r in
                    c.execute("SELECT DISTINCT inspection_id FROM proposals")}

    def list_proposals(self, status: Optional[str] = None) -> list[Proposal]:
        with self._conn() as c:
            rows = c.execute("""
                SELECT p.*, d.decision, d.decided_by, d.decided_at
                FROM proposals p LEFT JOIN decisions d ON d.proposal_id = p.proposal_id
                ORDER BY p.proposal_id DESC
            """).fetchall()
        out = []
        for r in rows:
            if r["auto_approved"]:
                st = "auto_approved"
            elif r["decision"] is not None:
                st = r["decision"]
            else:
                st = "proposed"
            if status and st != status:
                continue
            out.append(Proposal(
                proposal_id=r["proposal_id"], inspection_id=r["inspection_id"],
                facility_id=r["facility_id"], facility_name=r["facility_name"],
                risk_tier=r["risk_tier"], action_type=r["action_type"],
                params=json.loads(r["params"]), draft_text=r["draft_text"],
                rationale=r["rationale"], citations=json.loads(r["citations"]),
                source=r["source"], status=st, created_at=r["created_at"],
                decided_at=r["decided_at"], decided_by=r["decided_by"]))
        return out

    def stats(self) -> dict:
        with self._conn() as c:
            n_p = c.execute("SELECT COUNT(*) n FROM proposals").fetchone()["n"]
            n_d = c.execute("SELECT COUNT(*) n FROM decisions").fetchone()["n"]
            n_auto = c.execute("SELECT COUNT(*) n FROM proposals WHERE auto_approved=1").fetchone()["n"]
            runs = c.execute("SELECT COUNT(*) n FROM runs").fetchone()["n"]
        return {"proposals": n_p, "human_decisions": n_d, "auto_approved": n_auto,
                "pending": n_p - n_d - n_auto, "runs": runs}
