"""Agent pipeline: fact sheet -> risk triage -> drafted actions -> letter lint.

Every agent judgment must cite violation items that actually appear in the
fact sheet; citations are validated in code and invalid ones are dropped
(and counted, so evals can report the hallucination rate honestly). Drafted
letters are additionally cross-checked by a deterministic linter that verifies
every violation code the letter names against the official record.
"""
from __future__ import annotations

import re
from typing import Optional

from .qwen import QwenClient
from .schemas import ActionDraft, Inspection, TriageResult, Violation
from .store import SourceData

TRIAGE_SYSTEM = """You are a food-safety triage assistant for a county environmental health office.
You read one inspection fact sheet and classify follow-up risk. You never invent facts:
every claim in your rationale must come from the fact sheet (its violations, score,
or prior-inspection history).
Reply with ONLY a JSON object: {"risk_tier": "URGENT"|"ELEVATED"|"ROUTINE",
"rationale": "<2-4 sentences grounded in the fact sheet>",
"citations": ["<exact violation item text copied from the fact sheet>", ...]}
The citations array must contain ONLY violation item texts copied exactly from the
VIOLATIONS section. If VIOLATIONS is (none), return "citations": [] and ground the
rationale in the score and prior-inspection history (prose only, never in citations).
Guidance: URGENT = imminent-health-hazard patterns (score below 70, or multiple uncorrected
priority violations, or repeat priority violations). ELEVATED = priority violations present,
declining scores, or repeat/uncorrected items that need a scheduled recheck.
ROUTINE = high score, no priority violations, nothing uncorrected."""

ACTION_SYSTEM = """You are drafting follow-up actions for a county food-safety supervisor.
Given one inspection fact sheet and its assigned risk tier, propose exactly the concrete
next steps a supervisor should approve. Allowed action types:
- "schedule_reinspection": params {"window_days": <int 3-30>}
- "follow_up_letter": params {}; draft_text = a short formal letter to the facility
  operator naming the specific violations and the correction expected
- "acknowledge": params {}; no follow-up needed beyond the routine cycle
Rules: URGENT gets schedule_reinspection (tight window) AND follow_up_letter.
ELEVATED gets schedule_reinspection or follow_up_letter as facts warrant.
ROUTINE gets acknowledge only. Never invent violations not on the fact sheet.
Reply with ONLY a JSON object: {"actions": [{"action_type": "...", "params": {...},
"draft_text": "...", "rationale": "<1-2 sentences>"}, ...]}"""

# every real violation item is 26+ chars; this blocks one-word "citations"
# while still accepting any substantial verbatim fragment
_MIN_FRAGMENT_CHARS = 20


def build_fact_sheet(insp: Inspection, source: SourceData) -> str:
    fac = source.facilities.get(insp.facility_id)
    viols = source.violations.get(insp.inspection_id, [])
    history = source.history_for_facility(insp.facility_id, insp.date)[:5]

    lines = [
        f"FACILITY: {insp.name}" + (f" | {fac.address}" if fac and fac.address else ""),
        f"INSPECTION: {insp.date} | purpose: {insp.purpose} | score: {insp.score}"
        f" | inspector: {insp.inspector}",
        f"VIOLATIONS ({len(viols)}):",
    ]
    if not viols:
        lines.append("  (none)")
    for v in viols:
        flags = []
        if v.is_priority:
            flags.append("PRIORITY")
        if v.is_priority_foundation:
            flags.append("priority-foundation")
        if v.is_core:
            flags.append("core")
        if v.repeat:
            flags.append("REPEAT")
        flags.append("corrected on site" if v.corrected else "NOT corrected on site")
        lines.append(f"  - {v.item} [{', '.join(flags)}; {v.points} pts]")
    lines.append(f"PRIOR INSPECTIONS ({len(history)} most recent first):")
    if not history:
        lines.append("  (none on file)")
    for h in history:
        lines.append(f"  - {h.date}: score {h.score}, {h.n_violations} violations ({h.purpose})")
    return "\n".join(lines)


def _norm(s: str) -> str:
    return " ".join(s.lower().split())


def validate_citations(citations, viols: list[Violation]) -> tuple[list[str], int]:
    """Keep only citations that verbatim-match a violation item.

    Accepted: the exact item, an item quoted inside a longer citation, or a
    verbatim fragment of at least _MIN_FRAGMENT_CHARS. Everything else
    (empty strings, generic words, non-strings, invented items) is dropped
    and counted toward the hallucination metric.
    """
    if isinstance(citations, str):
        citations = [citations]
    if not isinstance(citations, list):
        citations = []
    real = {_norm(v.item) for v in viols}
    kept, dropped = [], 0
    for c in citations:
        c_norm = _norm(c) if isinstance(c, str) else ""
        if c_norm and (
                c_norm in real
                or any(r in c_norm for r in real)
                or (len(c_norm) >= _MIN_FRAGMENT_CHARS and any(c_norm in r for r in real))):
            kept.append(c)
        else:
            dropped += 1
    return kept, dropped


_CODE_RE = re.compile(r"\b\d{1,2}-\d[a-z]?\b|\b\d{1,2}[a-z]\b", re.IGNORECASE)


def lint_letter(draft_text: str, viols: list[Violation]) -> Optional[dict]:
    """Deterministic cross-check: every violation code the letter names must
    exist in this inspection's official record. Returns None for empty drafts.
    """
    if not draft_text.strip():
        return None
    real_items = [_norm(v.item) for v in viols]
    real_codes = {m.group(0).lower() for item in real_items for m in _CODE_RE.finditer(item)}
    named = {m.group(0).lower() for m in _CODE_RE.finditer(_norm(draft_text))}
    unmatched = sorted(c for c in named if c not in real_codes)
    return {"codes_named": len(named), "codes_matched": len(named) - len(unmatched),
            "unmatched_codes": unmatched}


def _clean_params(action_type: str, params: dict) -> dict:
    """Enforce in code what the prompt promises (window_days is an int 3-30)."""
    if not isinstance(params, dict):
        return {}
    if action_type == "schedule_reinspection":
        try:
            w = int(params.get("window_days", 14))
        except (TypeError, ValueError):
            w = 14
        params["window_days"] = max(3, min(30, w))
    else:
        params.pop("window_days", None)
    return params


def _stub_triage(insp: Inspection, viols: list[Violation]) -> dict:
    score = insp.score if insp.score is not None else 100
    n_priority = sum(v.is_priority for v in viols)
    n_uncorrected_priority = sum(1 for v in viols if v.is_priority and not v.corrected)
    n_repeat_priority = sum(1 for v in viols if v.is_priority and v.repeat)
    if score < 70 or n_uncorrected_priority >= 2 or n_repeat_priority >= 1:
        tier = "URGENT"
    elif n_priority >= 1 or score < 85 or any(v.repeat for v in viols):
        tier = "ELEVATED"
    else:
        tier = "ROUTINE"
    cited = [v.item for v in viols if v.is_priority or v.repeat][:4]
    return {"risk_tier": tier,
            "rationale": f"[stub heuristic] score={score}, priority={n_priority}, "
                         f"uncorrected priority={n_uncorrected_priority}, repeat priority={n_repeat_priority}.",
            "citations": cited}


def _stub_actions(tier: str, insp: Inspection, viols: list[Violation]) -> dict:
    cited = ", ".join(v.item for v in viols if v.is_priority) or "the noted items"
    letter = (f"[stub draft] Dear operator of {insp.name}: your {insp.date} inspection "
              f"(score {insp.score}) recorded violations requiring correction: {cited}. "
              f"Please correct these items; a recheck will verify compliance.")
    if tier == "URGENT":
        acts = [{"action_type": "schedule_reinspection", "params": {"window_days": 5},
                 "draft_text": "", "rationale": "[stub] urgent tier gets a tight recheck."},
                {"action_type": "follow_up_letter", "params": {}, "draft_text": letter,
                 "rationale": "[stub] urgent tier gets a formal letter."}]
    elif tier == "ELEVATED":
        acts = [{"action_type": "schedule_reinspection", "params": {"window_days": 14},
                 "draft_text": "", "rationale": "[stub] elevated tier gets a recheck."}]
    else:
        acts = [{"action_type": "acknowledge", "params": {}, "draft_text": "",
                 "rationale": "[stub] routine tier, no follow-up."}]
    return {"actions": acts}


def run_inspection(insp: Inspection, source: SourceData, client: QwenClient
                   ) -> tuple[TriageResult, list[ActionDraft], int]:
    """Triage one inspection and draft actions. Returns (triage, actions, dropped_citations)."""
    viols = source.violations.get(insp.inspection_id, [])
    sheet = build_fact_sheet(insp, source)

    raw = client.complete_json(TRIAGE_SYSTEM, sheet, stub_payload=_stub_triage(insp, viols))
    tier = raw.get("risk_tier", "ELEVATED")
    if tier not in ("URGENT", "ELEVATED", "ROUTINE"):
        tier = "ELEVATED"
    kept, dropped = validate_citations(raw.get("citations") or [], viols)
    triage = TriageResult(risk_tier=tier, rationale=str(raw.get("rationale", "")), citations=kept)

    raw_actions = client.complete_json(
        ACTION_SYSTEM,
        f"{sheet}\n\nASSIGNED RISK TIER: {triage.risk_tier}",
        stub_payload=_stub_actions(triage.risk_tier, insp, viols))
    raw_list = raw_actions.get("actions") or []
    if not isinstance(raw_list, list):
        raw_list = []
    actions: list[ActionDraft] = []
    for a in raw_list:
        try:
            act = ActionDraft(**a)
        except Exception:
            continue  # malformed action dropped; the eval's tier-action consistency check surfaces the gap
        act.params = _clean_params(act.action_type, act.params)
        if act.action_type == "follow_up_letter":
            lint = lint_letter(act.draft_text, viols)
            if lint is not None:
                act.params["letter_lint"] = lint
        actions.append(act)
    if not actions:
        actions = [ActionDraft(action_type="acknowledge", rationale="fallback: no valid actions returned")]
    return triage, actions, dropped
