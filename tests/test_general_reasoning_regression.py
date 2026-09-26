"""
Regression tests for General Reasoning Mode (Mode 3).
Verifies:
1. Self-contained calculation "Calculate 17.5% of 8400." -> PASS, 1470
2. Self-contained calculation "What is 25% of 400?" -> PASS, 100
3. General reasoning question requiring external factual information without evidence -> REJECT / NEEDS_EVIDENCE
4. Existing Dataset Mode tests and Direct Context contradiction tests remain strictly unchanged.
"""

import pytest
from backend.models.schemas import FinalDecision, VerificationStatus
from backend.orchestration.graph import run_multi_agent_workflow
from backend.verification.general_reasoning import (
    is_self_contained_task,
    solve_self_contained_task,
    verify_self_contained_task,
)


def test_is_self_contained_classification():
    """Validates self-contained vs external fact classification."""
    # Self-contained
    assert is_self_contained_task("Calculate 17.5% of 8400.") is True
    assert is_self_contained_task("What is 25% of 400?") is True
    assert is_self_contained_task("What is 2 + 2?") is True
    assert is_self_contained_task("If revenue was 100 in 2024 and 120 in 2025, calculate the percentage growth.") is True
    assert is_self_contained_task("Calculate compound interest for principal $10,000 at 5% annual rate over 3 years.") is True

    # Requires external evidence
    assert is_self_contained_task("What is the current population of India?") is False
    assert is_self_contained_task("Who is the CEO of Apple?") is False
    assert is_self_contained_task("What was the revenue recorded in the 2025 financial report?") is False

    # Not self-contained if dataset or context is provided
    assert is_self_contained_task("What is 2 + 2?", document_ids=["data.csv"]) is False
    assert is_self_contained_task("What is 2 + 2?", context_text="Context...") is False


def test_general_reasoning_calculate_17_5_pct_of_8400():
    """
    User Query: "Calculate 17.5% of 8400."
    Expected: 17.5% * 8400 = 1470
    Result: ACCEPT, VerificationStatus.PASS, 0 external sources.
    """
    res = run_multi_agent_workflow(
        task_id="test_gen_17_5_pct",
        task="Calculate 17.5% of 8400.",
        context_text=None,
        document_ids=None,
    )

    assert res.final_decision == FinalDecision.ACCEPT
    assert res.verification_status == "PASS"
    assert "1470" in res.final_answer
    assert res.researcher_output is not None
    assert res.researcher_output.status == "EVIDENCE_NOT_REQUIRED"
    assert len(res.researcher_output.evidence_items) == 0
    assert res.contradiction_detected is False


def test_general_reasoning_what_is_25_pct_of_400():
    """
    User Query: "What is 25% of 400?"
    Expected: 25% * 400 = 100
    Result: ACCEPT, VerificationStatus.PASS.
    """
    res = run_multi_agent_workflow(
        task_id="test_gen_25_pct",
        task="What is 25% of 400?",
        context_text=None,
        document_ids=None,
    )

    assert res.final_decision == FinalDecision.ACCEPT
    assert res.verification_status == "PASS"
    assert "100" in res.final_answer
    assert res.researcher_output is not None
    assert res.researcher_output.status == "EVIDENCE_NOT_REQUIRED"


def test_general_reasoning_external_factual_query_rejected():
    """
    User Query: "What is the current population of India?"
    Without context or dataset evidence, this cannot be self-contained and must be REJECTED.
    """
    res = run_multi_agent_workflow(
        task_id="test_gen_population",
        task="What is the current population of India?",
        context_text=None,
        document_ids=None,
    )

    assert res.final_decision == FinalDecision.REJECT
    assert res.verification_status in ["NEEDS_EVIDENCE", "BLOCKED", "FAIL"]
    assert "TASK REJECTED" in res.final_answer


def test_general_reasoning_simple_arithmetic():
    """
    User Query: "What is 2 + 2?"
    Expected: 4
    Result: ACCEPT.
    """
    res = run_multi_agent_workflow(
        task_id="test_gen_2_plus_2",
        task="What is 2 + 2?",
        context_text=None,
        document_ids=None,
    )

    assert res.final_decision == FinalDecision.ACCEPT
    assert res.verification_status == "PASS"
    assert "4" in res.final_answer
    assert res.researcher_output.status == "EVIDENCE_NOT_REQUIRED"


def test_dataset_mode_still_requires_dataset_grounding():
    """
    Verifies that Dataset Mode still enforces dataset grounding and does not bypass verification.
    """
    res = run_multi_agent_workflow(
        task_id="test_dataset_grounding_check",
        task="What is the average price of mobile phones with 8 GB RAM?",
        context_text=None,
        document_ids=["Mobile-Price-Prediction-cleaned_data.csv"],
    )

    assert res.final_decision == FinalDecision.ACCEPT
    assert res.verification_status == "PASS"
    assert res.researcher_output.status == "EVIDENCE_FOUND"
    assert len(res.researcher_output.evidence_items) > 0
    assert "37,358" in res.final_answer or "37358" in res.final_answer


def test_direct_context_contradiction_still_blocked():
    """
    Verifies that Direct Context Mode still detects contradictions and blocks execution.
    """
    contra_context = (
        "[Report Alpha]\nReport Alpha: 2024 revenue was 100M.\n\n"
        "[Report Beta]\nReport Beta: 2024 revenue was 120M due to audit restatement."
    )
    res = run_multi_agent_workflow(
        task_id="test_direct_context_contra",
        task="Calculate revenue growth from 2024 to 2025 and provide evidence.",
        context_text=contra_context,
        document_ids=None,
    )

    assert res.final_decision == FinalDecision.REJECT
    assert res.contradiction_detected is True
    assert "TASK REJECTED" in res.final_answer or "NEEDS_CLARIFICATION" in res.final_answer


def test_general_reasoning_25_times_48():
    """
    User Query: "25 × 48"
    Expected: 25 * 48 = 1200
    Result: ACCEPT, VerificationStatus.PASS, 0 external sources.
    """
    res = run_multi_agent_workflow(
        task_id="test_gen_25_times_48",
        task="25 × 48",
        context_text=None,
        document_ids=None,
    )

    assert res.final_decision == FinalDecision.ACCEPT
    assert res.verification_status == "PASS"
    assert "1200" in res.final_answer
    assert res.researcher_output is not None
    assert res.researcher_output.status == "EVIDENCE_NOT_REQUIRED"
    assert len(res.researcher_output.evidence_items) == 0


def test_general_reasoning_what_is_25_times_48():
    """
    User Query: "What is 25 × 48?"
    Expected: 1200
    Result: ACCEPT.
    """
    res = run_multi_agent_workflow(
        task_id="test_gen_what_is_25_times_48",
        task="What is 25 × 48?",
        context_text=None,
        document_ids=None,
    )

    assert res.final_decision == FinalDecision.ACCEPT
    assert res.verification_status == "PASS"
    assert "1200" in res.final_answer
    assert res.researcher_output.status == "EVIDENCE_NOT_REQUIRED"


def test_general_reasoning_average_calculation():
    """
    User Query: "What is the average of 10, 20, 30?"
    Expected: 20
    Result: ACCEPT.
    """
    res = run_multi_agent_workflow(
        task_id="test_gen_average",
        task="What is the average of 10, 20, 30?",
        context_text=None,
        document_ids=None,
    )

    assert res.final_decision == FinalDecision.ACCEPT
    assert res.verification_status == "PASS"
    assert "20" in res.final_answer
    assert res.researcher_output.status == "EVIDENCE_NOT_REQUIRED"


def test_general_reasoning_discount_price():
    """
    User Query: "If a product costs ₹800 and has a 15% discount, what is the final price?"
    Expected: 800 - 15% = 680
    Result: ACCEPT.
    """
    res = run_multi_agent_workflow(
        task_id="test_gen_discount",
        task="If a product costs ₹800 and has a 15% discount, what is the final price?",
        context_text=None,
        document_ids=None,
    )

    assert res.final_decision == FinalDecision.ACCEPT
    assert res.verification_status == "PASS"
    assert "680" in res.final_answer
    assert res.researcher_output.status == "EVIDENCE_NOT_REQUIRED"

