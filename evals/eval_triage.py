"""Eval harness: run the triage agent over a sample and check hard invariants.

Modes:
  python -m evals.eval_triage --n 25                 # recency sample
  python -m evals.eval_triage --n 25 --dangerous 25  # + stratified dangerous cases
  python -m evals.eval_triage --sabotage 25          # fault-inject the citation validator
  ... --out evals/results/<file>.json                # persist the report

Notes on honesty: in stub mode the tier/action invariants hold by construction
(the stub heuristic embeds them), so a stub pass proves wiring, not the model.
Numbers quoted in the README come from committed live-mode runs. The sabotage
mode exists because a validator that never fires is indistinguishable from one
that does not work: we forge citations (invented items AND real items lifted
from OTHER inspections) and verify every forgery is caught and every legitimate
citation preserved.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from app.qwen import QwenClient
from app.store import SourceData
from app.triage import _stub_triage, run_inspection, validate_citations


def date_key(d: str) -> str:
    try:
        m, day, y = d.split("-")
        return f"{y}-{m}-{day}"
    except ValueError:
        return d


def is_dangerous(source: SourceData, insp) -> bool:
    viols = source.violations.get(insp.inspection_id, [])
    return (any(v.is_priority and not v.corrected for v in viols)
            and (insp.score or 100) < 85)


def run_sabotage(source: SourceData, k: int) -> dict:
    """Fault-inject the citation validator; no model calls, fully deterministic."""
    all_items = sorted({v.item for vs in source.violations.values() for v in vs})
    with_viols = [i for i in sorted(source.inspections.values(),
                                    key=lambda i: date_key(i.date), reverse=True)
                  if source.violations.get(i.inspection_id)][:k]
    forged_total = caught = legit_total = preserved = 0
    misses = []
    for insp in with_viols:
        viols = source.violations[insp.inspection_id]
        own = {v.item for v in viols}
        foreign = next(it for it in all_items if it not in own)
        forged = [f"99-9Z - fabricated {insp.inspection_id} vermin-proofing violation", foreign]
        legit = [v.item for v in viols]
        kept, dropped = validate_citations(legit + forged, viols)
        forged_total += len(forged)
        caught += dropped
        legit_total += len(legit)
        preserved += len(kept)
        if dropped != len(forged) or len(kept) != len(legit):
            misses.append(insp.inspection_id)
    return {
        "mode": "sabotage (deterministic fault injection, no model calls)",
        "n_inspections": len(with_viols),
        "forged_citations_injected": forged_total,
        "forged_citations_caught": caught,
        "legitimate_citations": legit_total,
        "legitimate_citations_preserved": preserved,
        "forgery_classes": ["invented item code+text", "real item text from a different inspection"],
        "misses": misses,
        "pass": not misses,
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=25, help="recency sample size")
    ap.add_argument("--dangerous", type=int, default=0,
                    help="additionally include this many dangerous inspections "
                         "(uncorrected priority violation, score < 85)")
    ap.add_argument("--sabotage", type=int, default=0,
                    help="fault-inject K inspections' citations instead of running triage")
    ap.add_argument("--out", type=str, default="", help="write the report JSON here")
    args = ap.parse_args()

    source = SourceData()

    if args.sabotage:
        report = run_sabotage(source, args.sabotage)
        print(json.dumps(report, indent=2))
        if args.out:
            p = Path(args.out)
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(json.dumps(report, indent=2), encoding="utf-8")
        return 0 if report["pass"] else 1

    client = QwenClient()
    by_recency = sorted(source.inspections.values(),
                        key=lambda i: date_key(i.date), reverse=True)
    sample = by_recency[:args.n]
    if args.dangerous:
        seen = {i.inspection_id for i in sample}
        extra = [i for i in by_recency
                 if i.inspection_id not in seen and is_dangerous(source, i)][:args.dangerous]
        sample = sample + extra

    n = len(sample)
    citation_drops = 0
    citation_total = 0
    n_dangerous_checked = 0
    safety_misses = []      # dangerous inspections triaged ROUTINE
    consistency_misses = [] # action set does not match tier rules
    tiers = {"URGENT": 0, "ELEVATED": 0, "ROUTINE": 0}
    confusion: dict[str, dict[str, int]] = {}
    agree = 0

    for insp in sample:
        viols = source.violations.get(insp.inspection_id, [])
        triage, actions, dropped = run_inspection(insp, source, client)
        tiers[triage.risk_tier] += 1
        citation_drops += dropped
        citation_total += dropped + len(triage.citations)

        heur = _stub_triage(insp, viols)["risk_tier"]
        confusion.setdefault(triage.risk_tier, {}).setdefault(heur, 0)
        confusion[triage.risk_tier][heur] += 1
        agree += int(heur == triage.risk_tier)

        if is_dangerous(source, insp):
            n_dangerous_checked += 1
            if triage.risk_tier == "ROUTINE":
                safety_misses.append(insp.inspection_id)

        types = {a.action_type for a in actions}
        if triage.risk_tier == "URGENT" and "schedule_reinspection" not in types:
            consistency_misses.append(insp.inspection_id)
        if triage.risk_tier == "ELEVATED" and types == {"acknowledge"}:
            consistency_misses.append(insp.inspection_id)
        if triage.risk_tier == "ROUTINE" and types != {"acknowledge"}:
            consistency_misses.append(insp.inspection_id)

    report = {
        "mode": client.mode,
        "model": client.model if client.mode == "live" else None,
        "n_inspections": n,
        "n_dangerous_checked": n_dangerous_checked,
        "tier_distribution": tiers,
        "citation_hallucination_rate": round(citation_drops / citation_total, 4) if citation_total else 0.0,
        "citations_checked": citation_total,
        "citations_dropped": citation_drops,
        "safety_floor_misses": safety_misses,
        "tier_action_consistency_misses": consistency_misses,
        "pass": not safety_misses and not consistency_misses,
    }
    if client.mode == "live":
        report["heuristic_baseline_agreement"] = round(agree / n, 3) if n else None
        report["tier_confusion_live_x_heuristic"] = confusion
    else:
        report["note"] = ("stub mode: invariants hold by construction; "
                          "see the committed live-mode reports in evals/results/")
    print(json.dumps(report, indent=2))
    if args.out:
        p = Path(args.out)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps(report, indent=2), encoding="utf-8")
    return 0 if report["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
