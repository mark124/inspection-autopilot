"""Deterministic automation rules: the only path that skips human approval.

Rules are explicit, listed in the UI, and deliberately narrow. Everything
consequential stays in the human approval queue.
"""
from __future__ import annotations

from .schemas import ActionDraft, Inspection, TriageResult, Violation

RULES = [
    {
        "name": "auto_ack_clean_routine",
        "description": "Auto-approve 'acknowledge' when tier is ROUTINE, score >= 90, "
                       "and the inspection has no priority violations.",
    },
]


def auto_approve(triage: TriageResult, action: ActionDraft, insp: Inspection,
                 viols: list[Violation]) -> str | None:
    """Return the rule name if this action may bypass the queue, else None."""
    if (action.action_type == "acknowledge"
            and triage.risk_tier == "ROUTINE"
            and (insp.score or 0) >= 90
            and not any(v.is_priority for v in viols)):
        return "auto_ack_clean_routine"
    return None
