"""Tests for the stub pipeline, rules, and append-only store."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pytest

from app.qwen import QwenClient
from app.rules import auto_approve
from app.schemas import ActionDraft, TriageResult
from app.store import ProposalStore, SourceData
from app.triage import run_inspection, validate_citations


@pytest.fixture(scope="module")
def source():
    return SourceData()


@pytest.fixture()
def store(tmp_path):
    return ProposalStore(tmp_path / "test.db")


def test_source_loads(source):
    assert len(source.facilities) > 300
    assert len(source.inspections) > 1000
    assert any(source.violations.values())


def test_stub_pipeline_runs(source):
    client = QwenClient()
    assert client.mode == "stub"
    insp = next(iter(source.inspections.values()))
    triage, actions, dropped = run_inspection(insp, source, client)
    assert triage.risk_tier in ("URGENT", "ELEVATED", "ROUTINE")
    assert actions
    assert dropped == 0  # stub cites only real items


def test_citation_validation_drops_fakes(source):
    insp_id = next(i for i, v in source.violations.items() if v)
    viols = source.violations[insp_id]
    kept, dropped = validate_citations([viols[0].item, "totally invented violation"], viols)
    assert kept == [viols[0].item]
    assert dropped == 1


def test_auto_approve_only_clean_routine(source):
    insp = next(i for i in source.inspections.values()
                if (i.score or 0) >= 90 and not source.violations.get(i.inspection_id))
    triage = TriageResult(risk_tier="ROUTINE", rationale="clean", citations=[])
    act = ActionDraft(action_type="acknowledge")
    assert auto_approve(triage, act, insp, []) == "auto_ack_clean_routine"
    # urgent letter never auto-approves
    triage2 = TriageResult(risk_tier="URGENT", rationale="bad", citations=[])
    act2 = ActionDraft(action_type="follow_up_letter", draft_text="x")
    assert auto_approve(triage2, act2, insp, []) is None


def test_decisions_are_final(store):
    pid = store.add_proposal(1, "f1", "Test Cafe", "ELEVATED", "follow_up_letter",
                             {}, "letter", "why", ["cite"], "agent:stub")
    assert store.decide(pid, "approved", "supervisor") is True
    assert store.decide(pid, "rejected", "supervisor") is False  # append-only, no overwrite
    props = store.list_proposals()
    assert props[0].status == "approved"


def test_unknown_proposal_rejected(store):
    assert store.decide(999, "approved", "supervisor") is False
