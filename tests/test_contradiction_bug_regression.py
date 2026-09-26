"""
Regression Tests for Multi-Source Identity Preservation, Evidence Graph Contradiction Detection,
and Hard Deterministic Gating.
Enforces the fundamental architectural invariant:
UNRESOLVED CONFLICT -> NO VERIFIED INPUT -> NO VERIFIED CALCULATION -> NO ACCEPT
GENERATION != VERIFICATION
"""

import pytest
from backend.orchestration.graph import run_multi_agent_workflow
from backend.rag.ingestion import parse_sources_from_text, ingest_raw_text
from backend.models.schemas import FinalDecision, EvidenceItem
from backend.verification.contradiction import extract_claims_from_item, build_evidence_graph, evaluate_contradictions, detect_contradictions


def test_source_identity_preservation():
    """
    TEST 4: Prove that distinct sources do not collapse into source_id = 'provided_context'.
    Assert that source_A != source_B and both survive into EvidenceClaim, EvidenceGroup,
    and ContradictionReport.
    """
    raw_text = (
        "Source A — Monthly Analytics\n"
        "January visitors = 24,000\n"
        "February visitors = 30,000\n\n"
        "Source B — Management Summary\n"
        "January visitors = 24,000\n"
        "February visitors = 36,000"
    )

    parsed = parse_sources_from_text(raw_text)
    assert len(parsed) == 2, f"Expected 2 parsed sources, got {len(parsed)}"
    src_names = [p["source"] for p in parsed]
    assert any("Monthly Analytics" in s for s in src_names)
    assert any("Management Summary" in s for s in src_names)

    chunks = ingest_raw_text(raw_text)
    assert len(chunks) >= 2
    sources_in_chunks = set(c["source"] for c in chunks)
    assert len(sources_in_chunks) >= 2
    assert "provided_context" not in sources_in_chunks

    # Convert chunks to EvidenceItems and test claim extraction
    ev_items = [
        EvidenceItem(
            claim=c["text"],
            evidence=c["text"],
            source=c["source"],
            source_id=c["source_id"],
            page=1,
            confidence=0.95,
        )
        for c in chunks
    ]
    graph, claims = build_evidence_graph(ev_items)
    assert len(claims) >= 4

    claim_sources = set(c.source_name for c in claims)
    assert len(claim_sources) >= 2
    assert "provided_context" not in claim_sources

    report = evaluate_contradictions(graph, claims)
    assert report.contradiction_detected is True
    assert len(report.unresolved_contradictions) == 1
    unres = report.unresolved_contradictions[0]
    assert len(unres["supporting_sources"]) == 2
    assert unres["supporting_sources"][0] != unres["supporting_sources"][1]


def test_sources_agree_scenario():
    """
    TEST 1: Sources agree on both periods.
    Source A: Jan=24,000, Feb=30,000
    Source B: Jan=24,000, Feb=30,000
    Expected:
    contradiction_detected = false
    verification_status = PASS
    final_decision = ACCEPT
    Calculation = 25.0%
    """
    context = (
        "Source A — Monthly Analytics\n"
        "January visitors = 24,000\n"
        "February visitors = 30,000\n\n"
        "Source B — Management Summary\n"
        "January visitors = 24,000\n"
        "February visitors = 30,000"
    )
    task = "Calculate the percentage increase in website visitors from January to February using the provided evidence."

    res = run_multi_agent_workflow("reg_test_1", task, context_text=context)

    c_rep = res.contradiction_report or (res.researcher_output.contradiction_report if res.researcher_output else None)
    if c_rep:
        assert c_rep.contradiction_detected is False or len(c_rep.unresolved_contradictions) == 0

    assert res.verification_status == "PASS"
    assert res.final_decision == FinalDecision.ACCEPT
    assert res.coder_output is not None
    assert res.coder_output.execution_result is not None
    assert "25" in str(res.coder_output.execution_result)


def test_sources_disagree_contradiction_blocked():
    """
    TEST 2: Cross-source contradiction on February visitors.
    Source A: Jan=24,000, Feb=30,000
    Source B: Jan=24,000, Feb=36,000
    Expected:
    contradiction_detected = true
    contradiction_count >= 1
    unresolved_contradictions >= 1
    verification_status = BLOCKED
    final_decision = NEEDS_CLARIFICATION or REJECT
    CRITICAL:
    Assert that final_decision is NOT ACCEPT.
    Assert engine does NOT calculate 0%, 25%, 50% or arbitrarily pick a value.
    """
    context = (
        "Source A — Monthly Analytics\n"
        "January visitors = 24,000\n"
        "February visitors = 30,000\n\n"
        "Source B — Management Summary\n"
        "January visitors = 24,000\n"
        "February visitors = 36,000"
    )
    task = "Calculate the percentage increase in website visitors from January to February using the provided evidence."

    res = run_multi_agent_workflow("reg_test_2", task, context_text=context)

    # 1. Contradiction detected
    c_rep = res.contradiction_report or (res.researcher_output.contradiction_report if res.researcher_output else None)
    assert c_rep is not None
    assert c_rep.contradiction_detected is True
    assert c_rep.contradiction_count >= 1
    assert len(c_rep.unresolved_contradictions) >= 1

    # 2. Status and Decision Gates
    assert res.final_decision in [FinalDecision.NEEDS_CLARIFICATION, FinalDecision.REJECT]
    assert res.final_decision != FinalDecision.ACCEPT
    assert res.verification_status in ["BLOCKED", "FAIL"]

    # 3. Candidate calculation halted/blocked
    assert res.coder_output is not None
    assert res.coder_output.execution_result is None or res.coder_output.inputs.get("status") == "CONFLICTING_INPUT"
    assert res.coder_output.execution_result != "0.0%"
    assert res.coder_output.execution_result != "25.0%"
    assert res.coder_output.execution_result != "50.0%"

    # 4. Input references must flag conflict
    conflicted_refs = [ref for ref in res.coder_output.input_references if ref.is_conflicted]
    assert len(conflicted_refs) >= 1
    for cr in conflicted_refs:
        assert cr.selected_value is None
        assert cr.has_alternative_evidence is True

    # 5. Finalizer answer explains contradiction clearly
    assert "contradiction" in res.final_answer.lower() or "conflicting" in res.final_answer.lower()
    assert "30000" in res.final_answer or "30,000" in res.final_answer
    assert "36000" in res.final_answer or "36,000" in res.final_answer


def test_objective_resolution_scenario():
    """
    TEST 3: Sources disagree, but Source B contains an objective correction/revision.
    Source A: Feb=30,000 (preliminary)
    Source B: Feb=36,000 (revised/corrected)
    Expected:
    Conflict detected and objectively resolved
    Source B selected with basis
    Calculation proceeds with 36,000
    final_decision = ACCEPT
    Calculation = 50.0%
    """
    context = (
        "Source A — Preliminary Monthly Analytics\n"
        "January visitors = 24,000\n"
        "February visitors = 30,000\n\n"
        "Source B — Revised Management Summary (Official Correction)\n"
        "January visitors = 24,000\n"
        "February visitors = 36,000"
    )
    task = "Calculate the percentage increase in website visitors from January to February using the provided evidence."

    res = run_multi_agent_workflow("reg_test_3", task, context_text=context)

    c_rep = res.contradiction_report or (res.researcher_output.contradiction_report if res.researcher_output else None)
    assert c_rep is not None
    assert c_rep.contradiction_detected is True
    assert len(c_rep.resolved_contradictions) >= 1
    assert len(c_rep.unresolved_contradictions) == 0

    assert res.verification_status == "PASS"
    assert res.final_decision == FinalDecision.ACCEPT
    assert res.coder_output is not None
    assert res.coder_output.execution_result is not None
    assert "50" in str(res.coder_output.execution_result)
