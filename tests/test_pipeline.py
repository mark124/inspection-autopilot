"""Tests for the pipeline, validation layers, rules, and append-only store."""
import pytest

from app.qwen import QwenClient
from app.rules import auto_approve
from app.schemas import ActionDraft, DecideBody, TriageResult
from app.store import ProposalStore, SourceData
from app.triage import _clean_params, lint_letter, run_inspection, validate_citations


class FakeClient:
    """Feeds a queue of canned payloads through the QwenClient interface."""
    mode = "live"
    model = "fake"

    def __init__(self, payloads):
        self.payloads = list(payloads)

    def complete_json(self, system, user, stub_payload=None):
        return self.payloads.pop(0)


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


def test_citation_validation_rejects_empty_and_generic(source):
    insp_id = next(i for i, v in source.violations.items() if v)
    viols = source.violations[insp_id]
    kept, dropped = validate_citations(["", "  ", "food", "e", "not"], viols)
    assert kept == []
    assert dropped == 5


def test_citation_validation_keeps_fragments_and_context(source):
    insp_id = next(i for i, v in source.violations.items() if v)
    viols = source.violations[insp_id]
    full = viols[0].item
    fragment = full[:22]  # substantial verbatim fragment
    with_context = full + " [PRIORITY, NOT corrected on site]"
    kept, dropped = validate_citations([full, fragment, with_context], viols)
    assert kept == [full, fragment, with_context]
    assert dropped == 0


def test_citation_validation_handles_weird_types(source):
    insp_id = next(i for i, v in source.violations.items() if v)
    viols = source.violations[insp_id]
    kept, dropped = validate_citations([{"item": "x"}, 42, None], viols)
    assert kept == [] and dropped == 3
    # a bare string is one citation, not char-split
    kept, dropped = validate_citations(viols[0].item, viols)
    assert kept == [viols[0].item] and dropped == 0
    # non-list garbage is treated as no citations
    kept, dropped = validate_citations({"citations": []}, viols)
    assert kept == [] and dropped == 0


def test_null_model_output_does_not_crash(source):
    insp = next(iter(source.inspections.values()))
    client = FakeClient([
        {"risk_tier": "ROUTINE", "rationale": "ok", "citations": None},
        {"actions": None},
    ])
    triage, actions, dropped = run_inspection(insp, source, client)
    assert triage.citations == []
    assert actions[0].action_type == "acknowledge"  # fallback


def test_clean_params_enforces_window():
    assert _clean_params("schedule_reinspection", {"window_days": 365})["window_days"] == 30
    assert _clean_params("schedule_reinspection", {"window_days": 0})["window_days"] == 3
    assert _clean_params("schedule_reinspection", {"window_days": "14"})["window_days"] == 14
    assert _clean_params("schedule_reinspection", {"window_days": "ASAP"})["window_days"] == 14
    assert _clean_params("schedule_reinspection",
                         {"window_days": "<img src=x onerror=alert(1)>"})["window_days"] == 14
    assert "window_days" not in _clean_params("follow_up_letter", {"window_days": 7})


def test_lint_letter_flags_unknown_codes(source):
    insp_id = next(i for i, v in source.violations.items() if v)
    viols = source.violations[insp_id]
    clean = f"Your inspection recorded: {viols[0].item}. Please correct."
    ok = lint_letter(clean, viols)
    assert ok["unmatched_codes"] == []
    poisoned = clean + " Also violation 88-9X must be corrected."
    bad = lint_letter(poisoned, viols)
    assert "88-9x" in bad["unmatched_codes"]
    assert lint_letter("", viols) is None


def test_auto_approve_only_clean_routine(source):
    insp = next(i for i in source.inspections.values()
                if (i.score or 0) >= 90 and not source.violations.get(i.inspection_id))
    triage = TriageResult(risk_tier="ROUTINE", rationale="clean", citations=[])
    act = ActionDraft(action_type="acknowledge")
    assert auto_approve(triage, act, insp, []) == "auto_ack_clean_routine"
    triage2 = TriageResult(risk_tier="URGENT", rationale="bad", citations=[])
    act2 = ActionDraft(action_type="follow_up_letter", draft_text="x")
    assert auto_approve(triage2, act2, insp, []) is None


def test_decisions_are_final(store):
    pid = store.add_proposal(1, "f1", "Test Cafe", "ELEVATED", "follow_up_letter",
                             {}, "letter", "why", ["cite"], "agent:stub")
    assert store.decide(pid, "approved", "supervisor") is True
    assert store.decide(pid, "rejected", "supervisor") is False
    assert store.list_proposals()[0].status == "approved"


def test_auto_approved_rows_refuse_decisions(store):
    pid = store.add_proposal(2, "f2", "Rule Cafe", "ROUTINE", "acknowledge",
                             {}, "", "clean", [], "rule:auto_ack_clean_routine",
                             auto_approved=True)
    assert store.decide(pid, "approved", "supervisor") is False
    s = store.stats()
    assert s["pending"] == 0
    assert s["pending"] >= 0


def test_unknown_proposal_rejected(store):
    assert store.decide(999, "approved", "supervisor") is False


def test_decide_body_constraints():
    assert DecideBody(decision="approved").decided_by == "supervisor"
    with pytest.raises(Exception):
        DecideBody(decision="approved", decided_by="x" * 41)
    with pytest.raises(Exception):
        DecideBody(decision="approved", decided_by="<script>")
    with pytest.raises(Exception):
        DecideBody(decision="maybe")
