"""Pydantic models shared across the pipeline."""
from __future__ import annotations

from typing import Literal, Optional

from pydantic import BaseModel, Field

RiskTier = Literal["URGENT", "ELEVATED", "ROUTINE"]
ActionType = Literal["schedule_reinspection", "follow_up_letter", "acknowledge"]
Decision = Literal["approved", "rejected"]


class Violation(BaseModel):
    inspection_id: int
    item: str
    designation: str = ""
    is_priority: int = 0
    is_priority_foundation: int = 0
    is_core: int = 0
    points: int = 0
    repeat: int = 0
    corrected: int = 0


class Inspection(BaseModel):
    inspection_id: int
    facility_id: str
    name: str
    permit_number: str = ""
    date: str
    purpose: str = ""
    score: Optional[int] = None
    inspector: str = ""
    n_violations: int = 0


class Facility(BaseModel):
    facility_id: str
    name: str
    address: str = ""
    permit_type: str = ""
    permit_number: str = ""


class TriageResult(BaseModel):
    risk_tier: RiskTier
    rationale: str
    citations: list[str] = Field(default_factory=list)


class ActionDraft(BaseModel):
    action_type: ActionType
    params: dict = Field(default_factory=dict)
    draft_text: str = ""
    rationale: str = ""


class Proposal(BaseModel):
    proposal_id: int
    inspection_id: int
    facility_id: str
    facility_name: str
    risk_tier: RiskTier
    action_type: ActionType
    params: dict
    draft_text: str
    rationale: str
    citations: list[str]
    source: str  # "agent" or "rule:<name>"
    status: str  # proposed | approved | rejected | auto_approved
    created_at: str
    decided_at: Optional[str] = None
    decided_by: Optional[str] = None
