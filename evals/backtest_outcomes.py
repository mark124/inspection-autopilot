"""Outcome backtest: does the agent's triage predict what actually happened next?

For every (inspection T, next inspection T+1) pair of the same facility, run the
triage pass on T using only information available at time T, then check the real
outcome at T+1 (score under 85 or any priority violation = bad). If the tiers
mean anything operationally, URGENT should precede bad outcomes far more often
than ROUTINE. This is a validity check of the tiers, not a forecasting benchmark.

Run:  python -m evals.backtest_outcomes --sample 350 --workers 4
Requires DASHSCOPE_API_KEY (this eval is only meaningful in live mode).
Writes evals/backtest_results.json (served by /api/outcomes).
"""
from __future__ import annotations

import argparse
import json
import os
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

from app.qwen import DEFAULT_BASE_URL, DEFAULT_MODEL, _extract_json
from app.store import SourceData
from app.triage import TRIAGE_SYSTEM, build_fact_sheet

OUT_PATH = Path(__file__).resolve().parent / "backtest_results.json"


def date_key(d: str) -> str:
    try:
        m, day, y = d.split("-")
        return f"{y}-{m}-{day}"
    except ValueError:
        return d


def build_pairs(source: SourceData) -> list:
    by_fac: dict = {}
    for i in source.inspections.values():
        by_fac.setdefault(i.facility_id, []).append(i)
    pairs = []
    for insps in by_fac.values():
        insps.sort(key=lambda i: date_key(i.date))
        pairs.extend(zip(insps, insps[1:]))
    pairs.sort(key=lambda p: p[0].inspection_id)
    return pairs


def bad_outcome(source: SourceData, nxt) -> bool:
    viols = source.violations.get(nxt.inspection_id, [])
    return (nxt.score or 100) < 85 or any(v.is_priority for v in viols)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--sample", type=int, default=350,
                    help="pairs to triage (deterministic systematic sample); 0 = all")
    ap.add_argument("--workers", type=int, default=4)
    args = ap.parse_args()

    api_key = os.environ.get("DASHSCOPE_API_KEY", "")
    if not api_key:
        print("ERROR: backtest requires DASHSCOPE_API_KEY (live mode only).")
        return 1

    from openai import OpenAI
    client = OpenAI(api_key=api_key,
                    base_url=os.environ.get("QWEN_BASE_URL", DEFAULT_BASE_URL))
    model = os.environ.get("QWEN_MODEL", DEFAULT_MODEL)

    source = SourceData()
    pairs = build_pairs(source)
    if args.sample and args.sample < len(pairs):
        step = len(pairs) / args.sample
        pairs = [pairs[int(i * step)] for i in range(args.sample)]

    print(f"triaging {len(pairs)} of 1024 pairs with {model} ...", flush=True)

    tokens_in = tokens_out = 0
    failures = 0

    def triage_tier(insp) -> str:
        nonlocal tokens_in, tokens_out, failures
        sheet = build_fact_sheet(insp, source)
        for attempt in range(3):
            try:
                resp = client.chat.completions.create(
                    model=model,
                    messages=[{"role": "system", "content": TRIAGE_SYSTEM},
                              {"role": "user", "content": sheet}],
                    temperature=0.2,
                    response_format={"type": "json_object"})
                if resp.usage:
                    tokens_in += resp.usage.prompt_tokens
                    tokens_out += resp.usage.completion_tokens
                tier = _extract_json(resp.choices[0].message.content or "").get("risk_tier")
                if tier in ("URGENT", "ELEVATED", "ROUTINE"):
                    return tier
            except Exception:
                time.sleep(2 * (attempt + 1))
        failures += 1
        return "ELEVATED"  # neutral fallback, counted separately

    results = {}
    t0 = time.time()
    with ThreadPoolExecutor(max_workers=args.workers) as ex:
        futs = {ex.submit(triage_tier, a): (a, b) for a, b in pairs}
        done = 0
        for fut in as_completed(futs):
            a, b = futs[fut]
            results[a.inspection_id] = (fut.result(), bad_outcome(source, b))
            done += 1
            if done % 25 == 0:
                print(f"  {done}/{len(pairs)} ({time.time()-t0:.0f}s)", flush=True)

    tiers: dict = {}
    for tier, bad in results.values():
        t = tiers.setdefault(tier, [0, 0])
        t[0] += 1
        t[1] += int(bad)

    n_total = sum(t[0] for t in tiers.values())
    n_bad = sum(t[1] for t in tiers.values())
    report = {
        "model": model,
        "n_pairs_triaged": n_total,
        "n_pairs_available": 1024,
        "sampling": "deterministic systematic by inspection_id" if args.sample else "all",
        "outcome_definition": "next inspection of same facility has score < 85 or any priority violation",
        "base_bad_rate": round(n_bad / n_total, 3),
        "tiers": {
            tier: {"n": t[0], "next_inspection_bad_rate": round(t[1] / t[0], 3)}
            for tier, t in sorted(tiers.items())
        },
        "triage_failures_fallback_elevated": failures,
        "tokens": {"input": tokens_in, "output": tokens_out},
        "runtime_seconds": round(time.time() - t0),
    }
    OUT_PATH.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))
    print(f"\nwrote {OUT_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
