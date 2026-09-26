"""
Comprehensive tests for Source Provenance and Verification Evidence.
Tests all 5 specified source types plus internal and contradiction handling:
1. DOCUMENT / RAG (PDFs, Datasets, CSVs, direct context)
2. WEB / EXTERNAL SOURCE (Authoritative external sources, URLs)
3. DETERMINISTIC VERIFICATION (Python Sandbox calculations, percentages, arithmetic)
4. CODE VERIFICATION (Sandboxed execution, test input/output)
5. LOGICAL VERIFICATION (Independent Logic Verifier, deductive syllogisms)
6. NO EXTERNAL SOURCE RETRIEVED (Factual cross-check without attached documents)
7. CONTRADICTION HANDLING (Cross-source conflicting evidence presentation)
"""

import pytest
from backend.models.schemas import FinalDecision, VerificationStatus, EvidenceItem
from backend.orchestration.graph import run_multi_agent_workflow
from backend.verification.provenance import resolve_source_provenance


def test_provenance_deterministic_percentage_calculation():
    """
    Test Case: "Calculate 17.5% of 8400."
    Expected Source: Deterministic Python Sandbox
    Evidence: 17.5 / 100 × 8400 = 1470
    Verification: Independent calculation matches AI answer.
    """
    res = run_multi_agent_workflow(
        task_id="test_prov_pct_calc",
        task="Calculate 17.5% of 8400.",
        context_text=None,
        document_ids=None,
    )
    assert res.final_decision == FinalDecision.ACCEPT
    assert res.source_provenance is not None
    prov = res.source_provenance
    assert prov.source_type == "DETERMINISTIC"
    assert "Deterministic Python Sandbox" in prov.source_name
    assert "17.5" in prov.evidence and "8400" in prov.evidence and "1470" in prov.evidence
    assert "Independent calculation matches AI answer" in prov.verification
    assert prov.status == "PASS"
    assert prov.confidence >= 0.95


def test_provenance_deterministic_arithmetic_multiplication():
    """
    Test Case: "25 × 48"
    Expected Source: Deterministic Python Sandbox
    Evidence: 25 × 48 = 1200
    Verification: Independent calculation matches AI answer.
    """
    res = run_multi_agent_workflow(
        task_id="test_prov_mult",
        task="25 × 48",
        context_text=None,
        document_ids=None,
    )
    assert res.final_decision == FinalDecision.ACCEPT
    prov = res.source_provenance
    assert prov is not None
    assert prov.source_type == "DETERMINISTIC"
    assert "Deterministic Python Sandbox" in prov.source_name
    assert "1200" in prov.evidence
    assert "Independent calculation matches AI answer" in prov.verification
    assert prov.status == "PASS"


def test_provenance_subfactorial_derangement():
    """
    Test Case: "Calculate !6."
    Expected Source: Deterministic Python Sandbox
    Evidence: contains !6 = 265
    Verification: Independent calculation matches AI answer.
    """
    res = run_multi_agent_workflow(
        task_id="test_prov_subfact",
        task="Calculate !6.",
        context_text=None,
        document_ids=None,
    )
    assert res.final_decision == FinalDecision.ACCEPT
    prov = res.source_provenance
    assert prov is not None
    assert prov.source_type == "DETERMINISTIC"
    assert "!6" in prov.evidence
    assert "265" in prov.evidence
    assert prov.status == "PASS"


def test_provenance_document_rag_dataset():
    """
    Test Case: Dataset CSV query with specific filters.
    Expected Source: Mobile-Price-Prediction-cleaned_data.csv
    Location: Rows / Page
    Evidence: actual aggregation value
    Verification: AI claim matches document evidence.
    """
    res = run_multi_agent_workflow(
        task_id="test_prov_dataset",
        task="What is the average price of mobile phones with 8 GB RAM?",
        context_text=None,
        document_ids=["Mobile-Price-Prediction-cleaned_data.csv"],
    )
    assert res.final_decision == FinalDecision.ACCEPT
    prov = res.source_provenance
    assert prov is not None
    assert prov.source_type == "DOCUMENT"
    assert "Mobile-Price-Prediction-cleaned_data.csv" in prov.source_name
    assert "AI claim matches document evidence" in prov.verification or "verified" in prov.verification.lower()
    assert prov.status == "PASS"


def test_provenance_document_direct_context():
    """
    Test Case: Direct context provided by user.
    Expected Source: company_report.pdf or provided_context
    Location: Page 1
    Evidence: "Revenue for 2025 was ₹120 lakh."
    """
    ctx = "[company_report.pdf]\ncompany_report.pdf (Page 12): Revenue for 2025 was ₹120 lakh."
    res = run_multi_agent_workflow(
        task_id="test_prov_doc_ctx",
        task="What was the revenue for 2025 in company_report.pdf?",
        context_text=ctx,
        document_ids=None,
    )
    assert res.final_decision == FinalDecision.ACCEPT
    prov = res.source_provenance
    assert prov is not None
    assert prov.source_type == "DOCUMENT"
    assert "company_report.pdf" in prov.source_name
    assert "120" in prov.evidence
    assert prov.status == "PASS"


def test_provenance_logical_verification_syllogism():
    """
    Test Case: "If all A are B and X is A, is X B?"
    Expected Source: Independent Logic Verifier
    Evidence: Premises / logical check
    Verification: Conclusion logically follows from verified premises.
    """
    res = run_multi_agent_workflow(
        task_id="test_prov_logic",
        task="If all A are B and X is A, is X B?",
        context_text=None,
        document_ids=None,
    )
    assert res.final_decision == FinalDecision.ACCEPT
    prov = res.source_provenance
    assert prov is not None
    assert prov.source_type == "LOGIC"
    assert "Independent Logic Verifier" in prov.source_name
    assert "Premises" in prov.evidence or "Modus Ponens" in prov.evidence
    assert "logically follows" in prov.verification
    assert prov.status == "PASS"


def test_provenance_factual_without_external_source():
    """
    Test Case: Factual query without external documents.
    Expected Source: No external source retrieved
    Verification: Internal/independent verification
    Rule: Must NEVER use placeholder text "General reasoning / world knowledge"
    """
    res = run_multi_agent_workflow(
        task_id="test_prov_fact_internal",
        task="What is the capital of France?",
        context_text=None,
        document_ids=None,
    )
    assert res.final_decision == FinalDecision.ACCEPT
    prov = res.source_provenance
    assert prov is not None
    assert prov.source_name == "No external source retrieved"
    assert "Internal/independent verification" in prov.verification
    assert "General reasoning / world knowledge" not in res.final_answer
    assert "General reasoning / world knowledge" not in prov.evidence


def test_provenance_contradiction_detected_shows_both_sources():
    """
    Test Case: Contradictory evidence across Report Alpha and Report Beta.
    Expected: CONTRADICTION DETECTED, showing both Source A and Source B.
    """
    contra_ctx = (
        "[Report Alpha]\nReport Alpha (Page 1): 2024 revenue was 100M.\n\n"
        "[Report Beta]\nReport Beta (Page 1): 2024 revenue was 120M due to audit restatement."
    )
    res = run_multi_agent_workflow(
        task_id="test_prov_contra",
        task="Calculate revenue growth from 2024 to 2025 and provide evidence.",
        context_text=contra_ctx,
        document_ids=None,
    )
    assert res.contradiction_detected is True
    prov = res.source_provenance
    assert prov is not None
    assert prov.source_type == "CONTRADICTION"
    assert len(prov.conflicts) >= 2
    src_names = [c.source_name for c in prov.conflicts]
    assert any("Report Alpha" in s for s in src_names)
    assert any("Report Beta" in s for s in src_names)
    assert "CONTRADICTION" in prov.status.upper()
