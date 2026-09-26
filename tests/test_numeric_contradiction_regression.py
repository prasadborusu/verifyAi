"""
Regression Tests for Generalized Numeric Contradiction Detection.
Enforces the fundamental architectural invariants:
1. ENTITY != VALUE
2. GENERATION != VERIFICATION
3. CONFLICTING EVIDENCE -> NO VERIFIED FACT -> NO VERIFIED ANSWER -> NO ACCEPT

Required test coverage:
1. Numeric contradiction -> BLOCKED
2. Numeric agreement -> ACCEPT
3. Different periods -> no contradiction
4. Equivalent units -> no contradiction
5. Percentage contradiction -> BLOCKED
6. Count contradiction -> BLOCKED
7. Factual question with conflicting evidence -> NEEDS_CLARIFICATION
8. Categorical ACTIVE/INACTIVE regression
9. Objective official correction -> RESOLVED/ACCEPT
"""

import pytest
from backend.models.schemas import FinalDecision, EvidenceItem, VerificationStatus
from backend.verification.contradiction import (
    extract_claims_from_item,
    build_evidence_graph,
    evaluate_contradictions,
    detect_contradictions,
    normalize_unit_and_scale,
    normalize_entity_key,
)
from backend.orchestration.graph import run_multi_agent_workflow


def test_1_numeric_contradiction_blocked():
    """
    1. Numeric contradiction -> BLOCKED
    Source A: Revenue = ₹10 crore
    Source B: Revenue = ₹15 crore
    """
    items = [
        EvidenceItem(
            claim="Revenue = ₹10 crore",
            evidence="Revenue = ₹10 crore",
            source="Source A",
            source_id="source_a",
            page=1,
            confidence=0.95,
        ),
        EvidenceItem(
            claim="Revenue = ₹15 crore",
            evidence="Revenue = ₹15 crore",
            source="Source B",
            source_id="source_b",
            page=1,
            confidence=0.95,
        ),
    ]

    graph, claims = build_evidence_graph(items)
    assert "revenue" in graph, f"Expected canonical 'revenue' in graph, got: {list(graph.keys())}"
    group = graph["revenue"]

    # Verify ENTITY != VALUE invariant
    assert group.canonical_entity == "revenue"
    assert set(group.distinct_values) == {10, 15}
    assert set(group.supporting_sources) == {"Source A", "Source B"}

    report = evaluate_contradictions(graph, claims)
    assert report.contradiction_detected is True
    assert report.contradiction_count == 1
    assert report.verification_status == "BLOCKED"
    assert report.final_decision == FinalDecision.NEEDS_CLARIFICATION


def test_2_numeric_agreement_accept():
    """
    2. Numeric agreement -> ACCEPT
    Source A: Revenue = ₹10 crore
    Source B: Revenue = ₹10 crore
    """
    items = [
        EvidenceItem(
            claim="Revenue = ₹10 crore",
            evidence="Revenue = ₹10 crore",
            source="Source A",
            source_id="source_a",
            page=1,
            confidence=0.95,
        ),
        EvidenceItem(
            claim="Revenue = ₹10 crore",
            evidence="Revenue = ₹10 crore",
            source="Source B",
            source_id="source_b",
            page=1,
            confidence=0.95,
        ),
    ]

    graph, claims = build_evidence_graph(items)
    assert "revenue" in graph
    group = graph["revenue"]
    assert len(group.distinct_values) == 1
    assert group.distinct_values == [10]

    report = evaluate_contradictions(graph, claims)
    assert report.contradiction_detected is False
    assert report.verification_status == "PASS"
    assert report.final_decision == FinalDecision.ACCEPT


def test_3_different_periods_no_contradiction():
    """
    3. Different periods -> no contradiction
    Revenue January = 10 crore
    Revenue February = 15 crore
    """
    items = [
        EvidenceItem(
            claim="Revenue January = 10 crore",
            evidence="Revenue January = 10 crore",
            source="Source A",
            source_id="source_a",
            page=1,
            confidence=0.95,
        ),
        EvidenceItem(
            claim="Revenue February = 15 crore",
            evidence="Revenue February = 15 crore",
            source="Source B",
            source_id="source_b",
            page=1,
            confidence=0.95,
        ),
    ]

    graph, claims = build_evidence_graph(items)
    # Different periods must be in separate EvidenceGroups
    assert "revenue_january" in graph
    assert "revenue_february" in graph

    report = evaluate_contradictions(graph, claims)
    assert report.contradiction_detected is False
    assert report.verification_status == "PASS"
    assert report.final_decision == FinalDecision.ACCEPT


def test_4_equivalent_units_no_contradiction():
    """
    4. Equivalent units -> no contradiction
    Source A: Revenue = ₹10 crore
    Source B: Revenue = ₹100,000,000
    Both represent 100,000,000 INR.
    """
    items = [
        EvidenceItem(
            claim="Revenue = ₹10 crore",
            evidence="Revenue = ₹10 crore",
            source="Source A",
            source_id="source_a",
            page=1,
            confidence=0.95,
        ),
        EvidenceItem(
            claim="Revenue = ₹100,000,000",
            evidence="Revenue = ₹100,000,000",
            source="Source B",
            source_id="source_b",
            page=1,
            confidence=0.95,
        ),
    ]

    graph, claims = build_evidence_graph(items)
    assert "revenue" in graph
    group = graph["revenue"]

    # Equivalent after unit normalization -> only 1 distinct base value
    assert len(group.distinct_values) == 1

    report = evaluate_contradictions(graph, claims)
    assert report.contradiction_detected is False
    assert report.verification_status == "PASS"
    assert report.final_decision == FinalDecision.ACCEPT


def test_5_percentage_contradiction_blocked():
    """
    5. Percentage contradiction -> BLOCKED
    Source A: Growth = 20%
    Source B: Growth = 35%
    """
    items = [
        EvidenceItem(
            claim="Growth = 20%",
            evidence="Growth = 20%",
            source="Source A",
            source_id="source_a",
            page=1,
            confidence=0.95,
        ),
        EvidenceItem(
            claim="Growth = 35%",
            evidence="Growth = 35%",
            source="Source B",
            source_id="source_b",
            page=1,
            confidence=0.95,
        ),
    ]

    graph, claims = build_evidence_graph(items)
    assert "growth" in graph
    group = graph["growth"]
    assert set(group.distinct_values) == {20, 35}

    report = evaluate_contradictions(graph, claims)
    assert report.contradiction_detected is True
    assert report.verification_status == "BLOCKED"
    assert report.final_decision == FinalDecision.NEEDS_CLARIFICATION


def test_6_count_contradiction_blocked():
    """
    6. Count contradiction -> BLOCKED
    Source A: Employees = 500
    Source B: Employees = 700
    """
    items = [
        EvidenceItem(
            claim="Employees = 500",
            evidence="Employees = 500",
            source="Source A",
            source_id="source_a",
            page=1,
            confidence=0.95,
        ),
        EvidenceItem(
            claim="Employees = 700",
            evidence="Employees = 700",
            source="Source B",
            source_id="source_b",
            page=1,
            confidence=0.95,
        ),
    ]

    graph, claims = build_evidence_graph(items)
    assert "employees" in graph
    group = graph["employees"]
    assert set(group.distinct_values) == {500, 700}

    report = evaluate_contradictions(graph, claims)
    assert report.contradiction_detected is True
    assert report.verification_status == "BLOCKED"
    assert report.final_decision == FinalDecision.NEEDS_CLARIFICATION


def test_7_factual_question_conflicting_evidence_workflow():
    """
    7. Factual question with conflicting evidence -> NEEDS_CLARIFICATION
    Task: 'What is the revenue?'
    Context:
    Source A:
    Revenue = ₹10 crore

    Source B:
    Revenue = ₹15 crore
    """
    context = "Source A:\nRevenue = ₹10 crore\n\nSource B:\nRevenue = ₹15 crore"
    response = run_multi_agent_workflow(
        task_id="test_factual_conflict_001",
        task="What is the revenue?",
        context_text=context,
    )

    assert response.final_decision == FinalDecision.NEEDS_CLARIFICATION
    assert response.verification_status == "BLOCKED"
    assert response.confidence == 0.0
    assert response.contradiction_detected is True
    assert response.contradiction_count == 1

    # Check explicit statement in answer
    assert "Source A reports ₹10 crore" in response.final_answer
    assert "Source B reports ₹15 crore" in response.final_answer
    assert "The evidence is contradictory" in response.final_answer


def test_8_categorical_active_inactive_regression():
    """
    8. Categorical ACTIVE/INACTIVE regression
    Source A: Server status = ACTIVE
    Source B: Server status = INACTIVE
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
    assert "server status" in graph
    group = graph["server status"]
    assert set(group.distinct_values) == {"ACTIVE", "INACTIVE"}

    report = evaluate_contradictions(graph, claims)
    assert report.contradiction_detected is True
    assert report.verification_status == "BLOCKED"
    assert report.final_decision == FinalDecision.NEEDS_CLARIFICATION


def test_9_objective_official_correction_resolved_accept():
    """
    9. Objective official correction -> RESOLVED/ACCEPT
    Source A: Revenue = ₹10 crore
    Source B: Revenue = ₹15 crore (official correction)
    """
    items = [
        EvidenceItem(
            claim="Revenue = ₹10 crore",
            evidence="Revenue = ₹10 crore",
            source="Source A",
            source_id="source_a",
            page=1,
            confidence=0.95,
        ),
        EvidenceItem(
            claim="Revenue = ₹15 crore (official correction)",
            evidence="Revenue = ₹15 crore (official correction)",
            source="Source B (official correction)",
            source_id="source_b_corrected",
            page=1,
            confidence=0.95,
            metadata={"is_superseding": True, "resolution_reason": "official correction"},
        ),
    ]

    graph, claims = build_evidence_graph(items)
    assert "revenue" in graph
    report = evaluate_contradictions(graph, claims)

    assert report.contradiction_detected is True
    assert len(report.resolved_contradictions) == 1
    assert len(report.unresolved_contradictions) == 0
    assert report.verification_status == "PASS"
    assert report.final_decision == FinalDecision.ACCEPT


def test_10_equivalent_units_workflow_accept():
    """
    ₹10 crore == ₹100,000,000 -> no contradiction.
    'What is the revenue?' must NOT become a growth calculation (no 999999900%).
    Returns common verified revenue value.
    """
    context = "Source A:\nRevenue = ₹10 crore\n\nSource B:\nRevenue = ₹100,000,000"
    response = run_multi_agent_workflow(
        task_id="test_equiv_units_workflow",
        task="What is the revenue?",
        context_text=context,
    )

    assert response.final_decision == FinalDecision.ACCEPT
    assert response.verification_status == "PASS"
    assert response.contradiction_detected is False
    assert "999999900%" not in response.final_answer
    assert "growth" not in response.final_answer.lower()
    assert "100,000,000" in response.final_answer


def test_11_numeric_contradiction_10_vs_20_crore():
    """
    ₹10 crore vs ₹20 crore -> contradiction.
    """
    items = [
        EvidenceItem(
            claim="Revenue = ₹10 crore",
            evidence="Revenue = ₹10 crore",
            source="Source A",
            source_id="source_a",
            page=1,
            confidence=0.95,
        ),
        EvidenceItem(
            claim="Revenue = ₹20 crore",
            evidence="Revenue = ₹20 crore",
            source="Source B",
            source_id="source_b",
            page=1,
            confidence=0.95,
        ),
    ]

    graph, claims = build_evidence_graph(items)
    report = evaluate_contradictions(graph, claims)
    assert report.contradiction_detected is True
    assert report.verification_status == "BLOCKED"
    assert report.final_decision == FinalDecision.NEEDS_CLARIFICATION


def test_12_factual_question_does_not_become_growth():
    """
    January ₹10 crore + February ₹15 crore should not automatically produce 50% growth unless the task asks for growth.
    Task: 'What is the revenue?'
    """
    context = "Source A:\nRevenue January = 10 crore\n\nSource B:\nRevenue February = 15 crore"
    response = run_multi_agent_workflow(
        task_id="test_factual_no_growth",
        task="What is the revenue?",
        context_text=context,
    )

    assert response.final_decision == FinalDecision.ACCEPT
    assert response.verification_status == "PASS"
    # Must NOT invent unrequested 50% growth
    assert "50%" not in response.final_answer
    assert "50.0%" not in response.final_answer
    assert "January" in response.final_answer
    assert "February" in response.final_answer


def test_13_growth_task_produces_growth():
    """
    When the task explicitly asks for growth, it should calculate 50% growth.
    Task: 'Calculate revenue growth from January to February'
    """
    context = "Source A:\nRevenue January = 10 crore\n\nSource B:\nRevenue February = 15 crore"
    response = run_multi_agent_workflow(
        task_id="test_growth_calc",
        task="Calculate revenue growth from January to February",
        context_text=context,
    )

    assert response.final_decision == FinalDecision.ACCEPT
    assert response.verification_status == "PASS"
    assert "50.0%" in response.final_answer

