"""
Tests for Final VERITAS AI Implementation.
Covers Section 18 required test cases:
TEST 1: "What is 25 × 48?" -> 1200, ACCEPT
TEST 2: "What is 17.5% of 8400?" -> 1470, ACCEPT
TEST 3: "What is the capital of India?" -> New Delhi, ACCEPT
TEST 4: Document: 2025 revenue = ₹120 lakh, Question: "What was the 2025 revenue?" -> ACCEPT
TEST 5: AI candidate gives ₹150 lakh while document says ₹120 lakh -> CONTRADICTION -> CORRECT or REJECT
TEST 6: Two conflicting sources: Source A = ₹100 lakh, Source B = ₹120 lakh -> REJECT / NEEDS CLARIFICATION
TEST 7: "!6" -> Initial candidate 720 -> FAIL -> CORRECT -> 265 -> RE-VERIFY -> ACCEPT
TEST 8: New chat after contradiction: "A product costs ₹800 and has a 15% discount." -> 680, ACCEPT, No state leakage
"""

import pytest
from backend.orchestration.graph import run_multi_agent_workflow
from backend.models.schemas import FinalDecision


def test_1_what_is_25_times_48():
    res = run_multi_agent_workflow(
        task_id="veritas_test_1",
        task="What is 25 × 48?",
        context_text=None,
        document_ids=None,
    )
    assert res.final_decision == FinalDecision.ACCEPT
    assert res.verification_status == "PASS"
    assert "1200" in res.final_answer
    assert res.researcher_output.status == "EVIDENCE_NOT_REQUIRED"


def test_2_what_is_17_point_5_percent_of_8400():
    res = run_multi_agent_workflow(
        task_id="veritas_test_2",
        task="What is 17.5% of 8400?",
        context_text=None,
        document_ids=None,
    )
    assert res.final_decision == FinalDecision.ACCEPT
    assert res.verification_status == "PASS"
    assert "1470" in res.final_answer
    assert res.researcher_output.status == "EVIDENCE_NOT_REQUIRED"


def test_3_what_is_the_capital_of_india():
    res = run_multi_agent_workflow(
        task_id="veritas_test_3",
        task="What is the capital of India?",
        context_text=None,
        document_ids=None,
    )
    assert res.final_decision == FinalDecision.ACCEPT
    assert res.verification_status == "PASS"
    assert "New Delhi" in res.final_answer or "new delhi" in res.final_answer.lower()
    assert res.researcher_output.status == "EVIDENCE_NOT_REQUIRED"


def test_4_document_revenue_query():
    doc_context = "Annual Financial Report 2025: In FY 2025, company revenue was ₹120 lakh."
    res = run_multi_agent_workflow(
        task_id="veritas_test_4",
        task="What was the 2025 revenue?",
        context_text=doc_context,
        document_ids=None,
    )
    assert res.final_decision == FinalDecision.ACCEPT
    assert res.verification_status == "PASS"
    assert "120" in res.final_answer


def test_5_ai_candidate_mismatch_with_document():
    # If the context establishes ₹120 lakh, but a candidate claim is ₹150 lakh
    doc_context = "Audited Report: The verified 2025 revenue was exactly ₹120 lakh."
    res = run_multi_agent_workflow(
        task_id="veritas_test_5",
        task="Verify if 2025 revenue was ₹150 lakh.",
        context_text=doc_context,
        document_ids=None,
    )
    # Verifier detects discrepancy between 150 and 120
    assert res.final_decision in [FinalDecision.ACCEPT, FinalDecision.REJECT]
    assert "120" in res.final_answer or res.final_decision == FinalDecision.REJECT


def test_6_conflicting_sources_contradiction():
    contra_context = (
        "[Source A]\nSource A: Revenue in 2025 was ₹100 lakh.\n\n"
        "[Source B]\nSource B: Revenue in 2025 was ₹120 lakh."
    )
    res = run_multi_agent_workflow(
        task_id="veritas_test_6",
        task="What was the revenue in 2025?",
        context_text=contra_context,
        document_ids=None,
    )
    assert res.contradiction_detected is True
    assert res.final_decision in [FinalDecision.REJECT, FinalDecision.NEEDS_CLARIFICATION]
    assert "TASK REJECTED" in res.final_answer or "NEEDS_CLARIFICATION" in res.final_answer or "conflicting" in res.final_answer.lower()


def test_7_subfactorial_derangement_correction_loop():
    res = run_multi_agent_workflow(
        task_id="veritas_test_7",
        task="!6",
        context_text=None,
        document_ids=None,
    )
    assert res.final_decision == FinalDecision.ACCEPT
    assert res.verification_status == "PASS"
    assert "265" in res.final_answer
    # Correction loop must have executed (revision_history entries are dicts)
    assert len(res.revision_history) >= 1
    assert any(
        "720" in str(r.get("trigger_reason", "")) or
        "discrepancy" in str(r.get("trigger_reason", "")).lower() or
        "720" in str(r.get("correction_prompt", ""))
        for r in res.revision_history
    )


def test_8_new_chat_state_isolation_after_contradiction():
    # Run conflicting question
    contra_context = (
        "[Source A]\nSource A: Revenue in 2025 was ₹100 lakh.\n\n"
        "[Source B]\nSource B: Revenue in 2025 was ₹120 lakh."
    )
    res_contra = run_multi_agent_workflow(
        task_id="veritas_chat_a_contra",
        task="What was the revenue in 2025?",
        context_text=contra_context,
        document_ids=None,
    )
    assert res_contra.contradiction_detected is True
    assert res_contra.final_decision in [FinalDecision.REJECT, FinalDecision.NEEDS_CLARIFICATION]

    # Fresh Chat B with completely independent discount question
    res_b = run_multi_agent_workflow(
        task_id="veritas_chat_b_isolated",
        task="A product costs ₹800 and has a 15% discount. What is the final price?",
        context_text=None,
        document_ids=None,
    )
    assert res_b.contradiction_detected is False
    assert res_b.final_decision == FinalDecision.ACCEPT
    assert res_b.verification_status == "PASS"
    assert "680" in res_b.final_answer
    assert "revenue" not in res_b.final_answer.lower()
