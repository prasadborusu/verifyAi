"""
Unseen Verification Test Cases (Cases A, B, and C).
Tests the generalized verification architecture against completely new unseen inputs.
Verifies system behavior dynamically without pre-programmed expected strings.
"""

import pytest
from backend.models.schemas import FinalDecision
from backend.orchestration.graph import run_multi_agent_workflow


def test_case_a_all_sources_agree_accept():
    """
    CASE A: All sources agree on required input values.
    Expected: ACCEPT after independent deterministic verification.
    """
    task = "Verify server request throughput between baseline and peak."
    context = (
        "Telemetry Report A:\nBaseline throughput was 400 req/s.\n\n"
        "Telemetry Report B:\nPeak throughput was 600 req/s."
    )
    res = run_multi_agent_workflow(
        task_id="unseen_case_a",
        task=task,
        context_text=context,
    )
    assert res.final_decision == FinalDecision.ACCEPT
    assert res.confidence >= 0.9
    c_rep = res.contradiction_report
    if c_rep:
        assert c_rep.contradiction_detected is False
        assert len(c_rep.unresolved_contradictions) == 0


def test_case_b_sources_disagree_unresolved_blocks_and_rejects():
    """
    CASE B: Sources disagree on a required input and no objective resolution is possible.
    Expected:
    - CONTRADICTION_DETECTED = true
    - VERIFICATION_STATUS = BLOCKED / FAIL
    - FINAL_DECISION = REJECT or NEEDS_CLARIFICATION
    - Must NOT arbitrarily select one value or report a verified calculation.
    """
    task = "Determine February website visitor count."
    context = (
        "Monthly Analytics:\nFebruary visitors was 30000 visitors.\n\n"
        "Management Summary:\nFebruary visitors was 36000 visitors."
    )
    res = run_multi_agent_workflow(
        task_id="unseen_case_b",
        task=task,
        context_text=context,
    )
    assert res.final_decision in [FinalDecision.REJECT, FinalDecision.NEEDS_CLARIFICATION]
    assert res.confidence == 0.0

    # Verify structured machine-readable fields
    c_rep = res.contradiction_report
    assert c_rep is not None
    assert c_rep.contradiction_detected is True
    assert c_rep.verification_status in ["BLOCKED", "FAIL"]
    assert len(c_rep.unresolved_contradictions) >= 1
    assert "30000" in str(c_rep.unresolved_contradictions)
    assert "36000" in str(c_rep.unresolved_contradictions)


def test_case_c_sources_disagree_objectively_resolved_accept():
    """
    CASE C: Sources initially disagree, but an objective document revision / restatement
    resolves the conflict.
    Expected:
    - Conflict detected first.
    - Resolution recorded with objective basis.
    - Verified answer supports the resolved value.
    - FINAL_DECISION = ACCEPT.
    """
    task = "Determine final operational expenditure."
    context = (
        "Draft Report:\nOperational expenditure was 500k.\n\n"
        "Audited Statement:\nOperational expenditure was 520k due to audit restatement."
    )
    res = run_multi_agent_workflow(
        task_id="unseen_case_c",
        task=task,
        context_text=context,
    )
    # The conflict must be detected and resolved objectively
    c_rep = res.contradiction_report
    assert c_rep is not None
    assert c_rep.contradiction_detected is True
    assert len(c_rep.resolved_contradictions) >= 1
    assert len(c_rep.resolution_basis) >= 1
    assert "audit restatement" in str(c_rep.resolution_basis).lower()

    # Once resolved, the system can accept the audited figure
    assert res.final_decision == FinalDecision.ACCEPT
    assert "520" in str(res.final_answer) or "520.0" in str(res.final_answer)
