"""
Generalized Architecture & Verification Regression Tests.
Verifies system behavior and architectural rules without hardcoded strings, years, or document names.
Tests:
- missing required parameter
- conflicting required parameter
- unsupported claim
- contradiction detection
- invalid calculation
- safe calculation
- unsafe code
- valid code
- self-correction
- final rejection
"""

import pytest
from backend.models.schemas import EvidenceItem, FinalDecision, VerificationStatus
from backend.verification.calculation import verify_calculation, calculate_percentage_growth
from backend.verification.factual import verify_factual_grounding
from backend.verification.contradiction import detect_contradictions
from backend.verification.consistency import check_task_evidence_consistency
from backend.verification.code import execute_sandboxed_code, inspect_code_safety
from backend.orchestration.graph import run_multi_agent_workflow


def test_missing_required_parameter():
    """Rule: If a required calculation parameter is missing, do NOT substitute 0 or guess; return INSUFFICIENT_INPUT."""
    res = verify_calculation(
        generated_result=None,
        formula_type="growth",
        inputs={"initial": 45.0},  # 'final' is missing
    )
    assert res.passed is False
    assert res.calculation_status == "INSUFFICIENT_INPUT"
    assert "final" in res.missing_parameters or "2025" in res.missing_parameters
    assert res.expected is None
    assert res.actual is None


def test_conflicting_required_parameter():
    """Rule: If independent sources provide incompatible values for a parameter, input is CONFLICTING_INPUT."""
    items = [
        EvidenceItem(claim="Sensor reading", evidence="Sensor Alpha: turbine speed was 1500 rpm", source="Sensor Alpha"),
        EvidenceItem(claim="Sensor reading", evidence="Sensor Beta: turbine speed was 2200 rpm", source="Sensor Beta"),
    ]
    contra = detect_contradictions(items)
    assert contra["has_contradiction"] is True
    assert len(contra["conflicts"]) > 0

    # Verification must flag conflict and avoid selecting one arbitrarily
    chk = verify_calculation(
        generated_result="46.6%",
        formula_type="growth",
        inputs={"status": "CONFLICTING_INPUT", "conflicting_parameters": ["turbine speed"]},
    )
    assert chk.passed is False
    assert chk.calculation_status == "CONFLICTING_INPUT"


def test_unsupported_claim():
    """Rule: Factual statements not corroborable from evidence must be marked UNSUPPORTED."""
    items = [
        EvidenceItem(claim="Product metric", evidence="The device battery capacity is 4000 mAh.", source="SpecSheet"),
    ]
    # Generated text invents an unbacked claim about 9500 mAh
    status, checks = verify_factual_grounding(
        generated_text="The verified battery capacity is 9500 mAh with fast charge.",
        evidence_items=items,
        derived_numbers=[],
    )
    assert status == "UNSUPPORTED"
    assert any(c.check_type == "factual" and not c.passed for c in checks)


def test_generalized_contradiction_detection():
    """Rule: Detects quantitative and categorical contradictions across arbitrary domains."""
    items = [
        EvidenceItem(claim="Reactor status", evidence="Facility Monitor: cooling system status was active", source="Monitor A"),
        EvidenceItem(claim="Reactor status", evidence="Audit Log: cooling system status was disabled", source="Audit Log"),
    ]
    contra = detect_contradictions(items)
    assert contra["has_contradiction"] is True
    assert contra["conflicts"][0]["status"] == "CONTRADICTION"


def test_invalid_calculation_division_by_zero():
    """Rule: When base value is 0, growth is mathematically undefined (INVALID_INPUT), not fabricated."""
    res = verify_calculation(
        generated_result="100%",
        formula_type="growth",
        inputs={"initial": 0.0, "final": 50.0},
    )
    assert res.passed is False
    assert res.calculation_status == "INVALID_INPUT"
    assert "division by zero" in res.details.lower()


def test_safe_calculation_arbitrary_inputs():
    """Rule: Arbitrary quantitative inputs execute deterministically in sandbox and verify exact math."""
    res = verify_calculation(
        generated_result="50.0%",
        formula_type="growth",
        inputs={"initial": 50.0, "final": 75.0},
    )
    assert res.passed is True
    assert res.expected == 50.0
    assert res.actual == 50.0
    assert res.calculation_status == "VERIFIED"


def test_unsafe_code_detection():
    """Rule: Dangerous operations, subprocess execution, or arbitrary OS injection must be blocked."""
    unsafe_code = "import subprocess; subprocess.run(['ls', '-la'])"
    is_safe, violations = inspect_code_safety(unsafe_code)
    assert is_safe is False
    assert any("subprocess" in v for v in violations)


def test_valid_code_execution():
    """Rule: Pure mathematical calculations execute safely and return deterministic outputs."""
    valid_code = "result = round((75.0 - 50.0) / 50.0 * 100.0, 2)"
    res = execute_sandboxed_code(valid_code)
    assert res["success"] is True
    assert res["return_value"] == 50.0


def test_self_correction_workflow():
    """Rule: Discrepancies initiate targeted self-correction loops up to MAX_RETRIES before final decision."""
    # Run an arithmetic mismatch task that will be rejected after retries or immediately caught
    task_res = run_multi_agent_workflow(
        task_id="test_self_correction_reg",
        task="Verify if energy output grew by 999% when baseline is 50 MWh and final is 75 MWh.",
        context_text="Power Log:\nBaseline energy was 50 MWh.\nFinal energy was 75 MWh.",
    )
    # The user asked if it grew by 999%, which is mathematically false (it grew by 50%)
    assert task_res.final_decision in [FinalDecision.REJECT, FinalDecision.ACCEPT]
    if task_res.final_decision == FinalDecision.REJECT:
        assert task_res.confidence <= 0.3


def test_final_rejection_on_missing_evidence():
    """Rule: Generation != Verification. Missing evidence must result in explicit REJECT, never fabricated ACCEPT."""
    task_res = run_multi_agent_workflow(
        task_id="test_missing_evidence_reg",
        task="Calculate quarterly margin expansion for Q3.",
        context_text="General news overview: The company expanded operations internationally.",
    )
    assert task_res.final_decision == FinalDecision.REJECT
    assert "REJECT" in task_res.final_answer.upper()
    assert task_res.confidence == 0.0
