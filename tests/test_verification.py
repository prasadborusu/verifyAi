"""
Unit tests for deterministic verification modules.
Tests calculation, factual grounding, contradiction detection, and safety screening.
"""

import pytest
from backend.models.schemas import EvidenceItem
from backend.verification.calculation import verify_calculation, calculate_percentage_growth
from backend.verification.factual import verify_factual_grounding
from backend.verification.contradiction import detect_contradictions
from backend.verification.safety import check_action_safety
from backend.verification.code import execute_sandboxed_code, inspect_code_safety


def test_calculate_percentage_growth():
    assert calculate_percentage_growth(100.0, 120.0) == 20.0
    assert calculate_percentage_growth(50.0, 75.0) == 50.0
    with pytest.raises(ZeroDivisionError):
        calculate_percentage_growth(0.0, 100.0)


def test_verify_calculation_pass():
    chk = verify_calculation(
        generated_result="20.0%",
        formula_type="growth",
        inputs={"initial": 100.0, "final": 120.0},
    )
    assert chk.passed is True
    assert chk.expected == 20.0


def test_verify_calculation_fail():
    chk = verify_calculation(
        generated_result="30.0%",  # Wrong generated value
        formula_type="growth",
        inputs={"initial": 100.0, "final": 120.0},
    )
    assert chk.passed is False
    assert chk.expected == 20.0
    assert chk.actual == 30.0


def test_detect_contradictions():
    items = [
        EvidenceItem(claim="2024 revenue", evidence="2024 revenue was 100M", source="DocA", page=1),
        EvidenceItem(claim="2024 revenue", evidence="2024 revenue was 120M", source="DocB", page=2),
    ]
    res = detect_contradictions(items)
    assert res["has_contradiction"] is True
    assert len(res["conflicts"]) > 0


def test_check_action_safety_dangerous():
    safe_out = check_action_safety("os.system('rm -rf /')")
    assert safe_out.is_safe is False
    assert safe_out.risk_level == "CRITICAL"


def test_check_action_safety_safe():
    safe_out = check_action_safety("Calculate the compound annual growth rate for 2024-2025")
    assert safe_out.is_safe is True
    assert safe_out.risk_level == "SAFE"


def test_sandboxed_code_execution():
    res = execute_sandboxed_code("result = (120 - 100) / 100 * 100")
    assert res["success"] is True
    assert res["return_value"] == 20.0


def test_sandboxed_code_execution_block_import():
    is_safe, violations = inspect_code_safety("import os; os.system('echo hi')")
    assert is_safe is False
    assert any("os" in v for v in violations)


def test_task_evidence_consistency_contradiction():
    from backend.verification.consistency import check_task_evidence_consistency
    items = [
        EvidenceItem(claim="2024 revenue", evidence="FY 2024 revenue was 100 lakh", source="DocA"),
        EvidenceItem(claim="2025 revenue", evidence="FY 2025 revenue was 120 lakh", source="DocA"),
    ]
    res = check_task_evidence_consistency("Calculate revenue growth when 2025 revenue is unavailable.", items)
    assert res["status"] == "CONTRADICTED"
    assert res["passed"] is False
    assert "Task states that 2025 revenue is unavailable" in res["details"]


def test_task_evidence_consistency_consistent():
    from backend.verification.consistency import check_task_evidence_consistency
    items = [
        EvidenceItem(claim="2024 revenue", evidence="FY 2024 revenue was 100 lakh", source="DocA"),
        EvidenceItem(claim="2025 revenue", evidence="FY 2025 revenue was 120 lakh", source="DocA"),
    ]
    res = check_task_evidence_consistency("Calculate revenue growth between 2024 and 2025.", items)
    assert res["status"] == "CONSISTENT"
    assert res["passed"] is True


def test_task_evidence_consistency_missing_in_both():
    from backend.verification.consistency import check_task_evidence_consistency
    items = [
        EvidenceItem(claim="2024 revenue", evidence="FY 2024 revenue was 100 lakh", source="DocA"),
        EvidenceItem(claim="2025 revenue", evidence="2025 revenue is unavailable and pending audit.", source="DocA"),
    ]
    res = check_task_evidence_consistency("Calculate revenue growth when 2025 revenue is unavailable.", items)
    assert res["status"] == "INSUFFICIENT_INFORMATION"
    assert res["passed"] is False


def test_verify_calculation_missing_parameter_insufficient_input():
    # Only 2024 is available, 2025 is missing
    chk = verify_calculation(
        generated_result=None,
        formula_type="growth",
        inputs={"initial": 100.0, "2024": 100.0},
    )
    assert chk.passed is False
    assert chk.expected is None  # Must NOT fabricate -100.0%
    assert chk.actual is None    # Must NOT fabricate 2025.0%
    assert chk.calculation_status == "INSUFFICIENT_INPUT"
    assert chk.missing_parameters == ["2025"]
    assert chk.details == "Calculation cannot be performed because FY 2025 revenue is unavailable."
