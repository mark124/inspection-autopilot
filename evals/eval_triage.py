"""Eval harness: run the triage agent over a sample and check hard invariants.

Works in stub mode (deterministic heuristic) and live mode (real Qwen calls).
Run:  python -m evals.eval_triage --n 25
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.qwen import QwenClient  # noqa: E402
from app.store import SourceData  # noqa: E402
from app.triage import run_inspection  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=25, help="number of inspections to sample")
    args = ap.parse_args()

    source = SourceData()
    client = QwenClient()

    def key(d: str) -> str:
        try:
            m, day, y = d.split("-")
            return f"{y}-{m}-{day}"
        except ValueError:
            return d

    sample = sorted(source.inspections.values(), key=lambda i: key(i.date), reverse=True)[:args.n]

    n = len(sample)
    citation_drops = 0
    citation_total = 0
    safety_misses = []      # dangerous inspections triaged ROUTINE
    consistency_misses = [] # action set does not match tier rules
    tiers = {"URGENT": 0, "ELEVATED": 0, "ROUTINE": 0}

    for insp in sample:
        viols = source.violations.get(insp.inspection_id, [])
        triage, actions, dropped = run_inspection(insp, source, client)
        tiers[triage.risk_tier] += 1
        citation_drops += dropped
        citation_total += dropped + len(triage.citations)

        dangerous = (any(v.is_priority and not v.corrected for v in viols)
                     and (insp.score or 100) < 85)
        if dangerous and triage.risk_tier == "ROUTINE":
            safety_misses.append(insp.inspection_id)

        types = {a.action_type for a in actions}
        if triage.risk_tier == "URGENT" and "schedule_reinspection" not in types:
            consistency_misses.append(insp.inspection_id)
        if triage.risk_tier == "ROUTINE" and types != {"acknowledge"}:
            consistency_misses.append(insp.inspection_id)

    report = {
        "mode": client.mode,
        "model": client.model if client.mode == "live" else None,
        "n_inspections": n,
        "tier_distribution": tiers,
        "citation_hallucination_rate": round(citation_drops / citation_total, 4) if citation_total else 0.0,
        "citations_checked": citation_total,
        "safety_floor_misses": safety_misses,
        "tier_action_consistency_misses": consistency_misses,
        "pass": not safety_misses and not consistency_misses,
    }
    print(json.dumps(report, indent=2))
    return 0 if report["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
