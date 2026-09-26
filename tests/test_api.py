"""
Integration tests for FastAPI endpoints.
"""

from fastapi.testclient import TestClient
from backend.main import app

client = TestClient(app)


def test_health_endpoint():
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert "gemini_configured" in data


def test_analyze_endpoint_financial_demo():
    payload = {
        "task": "Calculate revenue growth from 2024 to 2025 and provide evidence.",
        "context_text": "Annual Financial Filing 2025:\nIn FY 2024, revenue was 100 lakh.\nIn FY 2025, revenue was 120 lakh.",
    }
    response = client.post("/analyze", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["final_decision"] == "ACCEPT"
    assert "20.0%" in data["final_answer"]
    assert data["confidence"] > 0.9


def test_analyze_endpoint_contradiction_reject():
    payload = {
        "task": "Calculate 2024 revenue.",
        "context_text": "Report Alpha: 2024 revenue was 100M.\nReport Beta: 2024 revenue was 120M.",
    }
    response = client.post("/analyze", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["final_decision"] in ["REJECT", "NEEDS_CLARIFICATION"]


def test_tasks_list_and_audit():
    list_resp = client.get("/tasks")
    assert list_resp.status_code == 200
    tasks = list_resp.json()
    assert isinstance(tasks, list)
    if tasks:
        task_id = tasks[0]["task_id"]
        audit_resp = client.get(f"/tasks/{task_id}/audit")
        assert audit_resp.status_code == 200
        assert "audit_trail" in audit_resp.json()


# USER REQUIRED TESTS (1-4)
def test_user_test_1_task_unavailable_evidence_contains_value():
    """
    TEST 1:
    Task says 2025 unavailable
    Evidence contains 2025 = 120
    Expected: REJECT or REVISE, NOT ACCEPT
    """
    payload = {
        "task": "Calculate revenue growth when the 2025 revenue is unavailable.",
        "context_text": "Annual Financial Filing 2025:\nIn FY 2024, revenue was 100 lakh.\nIn FY 2025, revenue was 120 lakh.",
    }
    response = client.post("/analyze", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["final_decision"] in ["REJECT", "REVISE"]
    assert data["final_decision"] != "ACCEPT"
    # Ensure contradiction details are reported
    assert "Task states that 2025 revenue is unavailable" in data["final_answer"] or any(
        "CONTRADICTION" in str(log) for log in data.get("audit_trail", [])
    )


def test_user_test_2_normal_revenue_growth_accept():
    """
    TEST 2:
    Task asks normal revenue growth
    Evidence contains 2024 = 100 and 2025 = 120
    Expected: ACCEPT, 20%
    """
    payload = {
        "task": "Calculate revenue growth from 2024 to 2025 and provide evidence.",
        "context_text": "Annual Financial Filing 2025:\nIn FY 2024, revenue was 100 lakh.\nIn FY 2025, revenue was 120 lakh.",
    }
    response = client.post("/analyze", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["final_decision"] == "ACCEPT"
    assert "20.0%" in data["final_answer"]
    assert data["confidence"] >= 0.9


def test_user_test_3_task_and_evidence_both_unavailable():
    """
    TEST 3:
    Task says 2025 unavailable
    Evidence also says 2025 unavailable
    Expected: REJECT / INSUFFICIENT_EVIDENCE
    """
    payload = {
        "task": "Calculate revenue growth when the 2025 revenue is unavailable.",
        "context_text": "Fiscal Report: In FY 2024, revenue was recorded at 100M. 2025 results are currently pending final audit certification and are unavailable.",
    }
    response = client.post("/analyze", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["final_decision"] == "REJECT"
    assert "20.0%" not in data["final_answer"]


def test_user_test_4_custom_context_isolation():
    """
    TEST 4:
    Custom Context must not contain the previous preset scenario.
    When custom context is passed as empty, it does not silently inject ChromaDB preset documents.
    """
    from backend.agents.researcher import ResearcherAgent
    researcher = ResearcherAgent()
    # Explicit empty custom context provided by user
    out = researcher.research(
        task="Calculate revenue growth between 2024 and 2025",
        context_text="",
    )
    assert out.status == "INSUFFICIENT_EVIDENCE"
    assert len(out.evidence_items) == 0


def test_missing_2025_revenue_no_fabricated_expected_calculation():
    """
    Regression test:
    Task: Calculate revenue growth when 2025 revenue is unavailable.
    Context: FY 2024 revenue = 100 lakh. FY 2025 revenue is not available.
    Must NOT contain 'Expected -100.0%, Generated 2025.0%' or any fabricated calculation.
    Must report 'Calculation cannot be performed because FY 2025 revenue is unavailable.'
    Must route to REJECT.
    """
    payload = {
        "task": "Calculate revenue growth when the 2025 revenue is unavailable.",
        "context_text": "FY 2024 revenue = 100 lakh.\nFY 2025 revenue is not available.",
    }
    response = client.post("/analyze", json=payload)
    assert response.status_code == 200
    data = response.json()

    assert data["final_decision"] == "REJECT"

    # Verifier report checks
    v_out = data.get("verifier_output") or {}
    checks = v_out.get("checks", [])
    calc_checks = [c for c in checks if c.get("check_type") == "calculation"]

    # Verify no fabricated values
    for c in calc_checks:
        assert c.get("expected") is None or c.get("expected") != -100.0
        assert "2125" not in c.get("details", "")
        assert "-100" not in c.get("details", "")

    # Ensure message is reported
    v_reason = v_out.get("reason", "")
    assert "Calculation cannot be performed because FY 2025 revenue is unavailable." in str(data) or "unavailable" in v_reason
