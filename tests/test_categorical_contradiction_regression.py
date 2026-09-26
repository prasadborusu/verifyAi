"""
Regression Tests for Categorical and State Contradiction Detection.
Enforces the fundamental architectural invariants:
1. ENTITY != VALUE
2. GENERATION != VERIFICATION
3. CONFLICTING EVIDENCE -> NO VERIFIED FACT -> NO VERIFIED ANSWER -> NO ACCEPT
Domain-agnostic verification across arbitrary entities and categorical states.
"""

import pytest
from backend.models.schemas import FinalDecision, EvidenceItem, VerificationStatus
from backend.verification.contradiction import (
    extract_claims_from_item,
    build_evidence_graph,
    evaluate_contradictions,
    detect_contradictions,
    OPPOSING_STATES,
    are_opposing_states,
)
from backend.orchestration.graph import run_multi_agent_workflow


def test_categorical_contradiction_active_inactive():
    """
    1. test_categorical_contradiction_active_inactive
    Input:
    Source A -> Server status = ACTIVE
    Source B -> Server status = INACTIVE

    Expected:
    contradiction_detected = True
    contradiction_count = 1
    verification_status = BLOCKED
    final_decision = NEEDS_CLARIFICATION
    """
    items = [
        EvidenceItem(
            claim="Server status = ACTIVE",
            evidence="Server status = ACTIVE",
            source="Source A",
            source_id="source_a",
            page=1,
            confidence=0.95,
        ),
        EvidenceItem(
            claim="Server status = INACTIVE",
            evidence="Server status = INACTIVE",
            source="Source B",
            source_id="source_b",
            page=1,
            confidence=0.95,
        ),
    ]

    graph, claims = build_evidence_graph(items)
    # Must group under "server status", NOT two different groups!
    assert "server status" in graph, f"Expected 'server status' in graph, got keys: {list(graph.keys())}"
    group = graph["server status"]

    assert set(group.distinct_values) == {"ACTIVE", "INACTIVE"}
    assert set(group.supporting_sources) == {"Source A", "Source B"}

    report = evaluate_contradictions(graph, claims)
    assert report.contradiction_detected is True
    assert report.contradiction_count == 1
    assert report.verification_status == "BLOCKED"
    assert report.final_decision == FinalDecision.NEEDS_CLARIFICATION
    assert len(report.unresolved_contradictions) == 1

    # End-to-end multi-agent workflow verification
    context_text = (
        "Source A:\n"
        "Server status = ACTIVE\n\n"
        "Source B:\n"
        "Server status = INACTIVE"
    )
    res = run_multi_agent_workflow(
        "cat_test_1",
        task="What is the current server status?",
        context_text=context_text,
    )
    assert res.final_decision == FinalDecision.NEEDS_CLARIFICATION
    assert res.verification_status == "BLOCKED"
    assert res.confidence == 0.0
    assert "Source A" in res.final_answer
    assert "Source B" in res.final_answer
    assert "ACTIVE" in res.final_answer
    assert "INACTIVE" in res.final_answer


def test_categorical_agreement():
    """
    2. test_categorical_agreement
    Source A -> Server status = ACTIVE
    Source B -> Server status = ACTIVE

    Expected:
    no contradiction
    verification can PASS
    factual answer may be ACCEPTED
    """
    items = [
        EvidenceItem(
            claim="Server status = ACTIVE",
            evidence="Server status = ACTIVE",
            source="Source A",
            source_id="source_a",
            page=1,
            confidence=0.95,
        ),
        EvidenceItem(
            claim="Server status = ACTIVE",
            evidence="Server status = ACTIVE",
            source="Source B",
            source_id="source_b",
            page=1,
            confidence=0.95,
        ),
    ]

    graph, claims = build_evidence_graph(items)
    assert "server status" in graph
    group = graph["server status"]
    assert group.distinct_values == ["ACTIVE"]
    assert len(group.supporting_sources) == 2

    report = evaluate_contradictions(graph, claims)
    assert report.contradiction_detected is False
    assert report.contradiction_count == 0
    assert report.verification_status == "PASS"
    assert report.final_decision == FinalDecision.ACCEPT

    # End-to-end workflow verification
    context_text = (
        "Source A:\n"
        "Server status = ACTIVE\n\n"
        "Source B:\n"
        "Server status = ACTIVE"
    )
    res = run_multi_agent_workflow(
        "cat_test_2",
        task="What is the current server status?",
        context_text=context_text,
    )
    assert res.final_decision == FinalDecision.ACCEPT
    assert res.verification_status == "PASS"
    assert "ACTIVE" in res.final_answer


def test_categorical_objective_resolution():
    """
    3. test_categorical_objective_resolution
    Source A -> Server status = ACTIVE
    Source B -> Revised official correction: Server status = INACTIVE

    Expected:
    conflict resolved
    resolved_value = superseding value (INACTIVE)
    verification_status = PASS
    final_decision = ACCEPT
    """
    context_text = (
        "Source A:\n"
        "Server status = ACTIVE\n\n"
        "Source B — Official Correction:\n"
        "Server status = INACTIVE (official correction supersedes preliminary status)"
    )
    res = run_multi_agent_workflow(
        "cat_test_3",
        task="What is the current server status?",
        context_text=context_text,
    )
    assert res.final_decision == FinalDecision.ACCEPT
    assert res.verification_status == "PASS"
    assert "INACTIVE" in res.final_answer


def test_arbitrary_categorical_entities():
    """
    4. test_arbitrary_categorical_entities
    Test several generic entities without adding entity-specific code:
    Account state: ENABLED vs DISABLED
    Service availability: AVAILABLE vs UNAVAILABLE
    Deployment state: SUCCESS vs FAILED
    The contradiction detector must identify these generically.
    """
    pairs = [
        ("Account state", "ENABLED", "DISABLED"),
        ("Service availability", "AVAILABLE", "UNAVAILABLE"),
        ("Deployment state", "SUCCESS", "FAILED"),
        ("Network tunnel", "ONLINE", "OFFLINE"),
        ("Registration gate", "OPEN", "CLOSED"),
        ("Security token", "VALID", "INVALID"),
    ]

    for entity_name, val_a, val_b in pairs:
        items = [
            EvidenceItem(
                claim=f"{entity_name} = {val_a}",
                evidence=f"{entity_name} = {val_a}",
                source="Source A",
                source_id="src_a",
                page=1,
                confidence=0.95,
            ),
            EvidenceItem(
                claim=f"{entity_name} = {val_b}",
                evidence=f"{entity_name} = {val_b}",
                source="Source B",
                source_id="src_b",
                page=1,
                confidence=0.95,
            ),
        ]
        graph, claims = build_evidence_graph(items)
        report = evaluate_contradictions(graph, claims)
        assert report.contradiction_detected is True, f"Failed to detect contradiction for {entity_name}: {val_a} vs {val_b}"
        assert report.contradiction_count == 1
        assert report.verification_status == "BLOCKED"
        assert report.final_decision == FinalDecision.NEEDS_CLARIFICATION


def test_categorical_contradiction_does_not_depend_on_calculation():
    """
    5. test_categorical_contradiction_does_not_depend_on_calculation
    A factual question with no numerical calculation must still be blocked when evidence conflicts.
    The previous failure:
    "No candidate calculation formulated" -> verifier PASS -> contradiction not detected -> ACCEPT
    must become impossible.
    """
    task = "What is the current server status?"
    context = (
        "Source A:\n"
        "Server status = ACTIVE\n\n"
        "Source B:\n"
        "Server status = INACTIVE"
    )

    res = run_multi_agent_workflow("cat_test_5", task=task, context_text=context)

    # Invariant checks:
    # 1. Must NOT accept
    assert res.final_decision != FinalDecision.ACCEPT
    assert res.final_decision == FinalDecision.NEEDS_CLARIFICATION

    # 2. Must be BLOCKED
    assert res.verification_status == "BLOCKED"

    # 3. Confidence must not be 98%
    assert res.confidence == 0.0

    # 4. Candidate calculation/answer must be blocked
    if res.coder_output:
        assert res.coder_output.execution_result is None
        assert res.coder_output.inputs.get("status") == "CONFLICTING_INPUT"
