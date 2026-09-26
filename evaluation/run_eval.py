"""
Evaluation Suite Runner.
Executes test cases covering the 10 core verification scenarios (positive & negative).
Calculates real metrics for Generation Quality and Verification Quality without fabrication.
"""

import os
import sys
import json
import time
import logging
from typing import Dict, Any, List

# Ensure project root is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from backend.orchestration.graph import run_multi_agent_workflow
from backend.models.schemas import FinalDecision

logger = logging.getLogger("eval_runner")
logger.setLevel(logging.INFO)

TEST_CASES_PATH = os.path.join(os.path.dirname(__file__), "test_cases.json")
RESULTS_PATH = os.path.join(os.path.dirname(__file__), "eval_results.json")


def run_benchmark() -> Dict[str, Any]:
    """Runs all benchmark test cases and computes rigorous evaluation metrics."""
    with open(TEST_CASES_PATH, "r", encoding="utf-8") as f:
        cases: List[Dict[str, Any]] = json.load(f)

    results = []
    start_total_time = time.time()

    # Metric accumulators
    total_cases = len(cases)
    expected_accepts = 0
    expected_rejects = 0

    true_accepts = 0   # Ground truth ACCEPT, system ACCEPT
    false_accepts = 0  # Ground truth REJECT, system ACCEPT (Dangerous!)
    true_rejects = 0   # Ground truth REJECT, system REJECT
    false_rejects = 0  # Ground truth ACCEPT, system REJECT

    hallucination_detected = 0
    hallucination_total = 0

    contradiction_detected = 0
    contradiction_total = 0

    unsupported_detected = 0
    unsupported_total = 0

    calc_verified_correct = 0
    calc_total = 0

    for tc in cases:
        tc_id = tc["id"]
        tc_name = tc["name"]
        category = tc["category"]
        exp_dec = tc["expected_decision"]

        logger.info(f"Running benchmark case: {tc_id} ({tc_name})")
        case_start = time.time()

        res = run_multi_agent_workflow(
            task_id=f"eval_{tc_id}",
            task=tc["task"],
            context_text=tc.get("context"),
        )
        duration = round(time.time() - case_start, 2)

        actual_dec = res.final_decision.value
        passed_test = False

        if exp_dec == "ACCEPT":
            expected_accepts += 1
            if actual_dec == "ACCEPT":
                true_accepts += 1
                passed_test = True
                if tc.get("expected_calc_result"):
                    calc_total += 1
                    if tc["expected_calc_result"] in str(res.final_answer):
                        calc_verified_correct += 1
            else:
                false_rejects += 1
        elif exp_dec in ["REJECT", "NEEDS_CLARIFICATION"]:
            expected_rejects += 1
            if actual_dec in ["REJECT", "NEEDS_CLARIFICATION"]:
                true_rejects += 1
                passed_test = True
            else:
                false_accepts += 1

        # Specific category tracking
        if category == "HALLUCINATED_INFORMATION":
            hallucination_total += 1
            if actual_dec in ["REJECT", "NEEDS_CLARIFICATION"]:
                hallucination_detected += 1
        elif category == "CONFLICTING_DOCUMENTS":
            contradiction_total += 1
            if actual_dec in ["REJECT", "NEEDS_CLARIFICATION"]:
                contradiction_detected += 1
        elif category in ["UNSUPPORTED_CLAIM", "MISSING_INFORMATION"]:
            unsupported_total += 1
            if actual_dec in ["REJECT", "NEEDS_CLARIFICATION"]:
                unsupported_detected += 1

        results.append({
            "id": tc_id,
            "name": tc_name,
            "category": category,
            "expected_decision": exp_dec,
            "actual_decision": actual_dec,
            "passed": passed_test,
            "confidence": res.confidence,
            "duration_seconds": duration,
            "final_answer_snippet": res.final_answer[:160],
        })

    total_duration = round(time.time() - start_total_time, 2)

    # Compute Final Metric Rates
    far = round((false_accepts / expected_rejects) * 100.0, 2) if expected_rejects else 0.0
    frr = round((false_rejects / expected_accepts) * 100.0, 2) if expected_accepts else 0.0
    task_completion_rate = round(((true_accepts + true_rejects) / total_cases) * 100.0, 2)
    answer_accuracy = round((true_accepts / expected_accepts) * 100.0, 2) if expected_accepts else 100.0
    hallucination_det_rate = round((hallucination_detected / hallucination_total) * 100.0, 2) if hallucination_total else 100.0
    contradiction_det_rate = round((contradiction_detected / contradiction_total) * 100.0, 2) if contradiction_total else 100.0
    calc_accuracy = round((calc_verified_correct / calc_total) * 100.0, 2) if calc_total else 100.0

    eval_summary = {
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "total_test_cases": total_cases,
        "total_passed": true_accepts + true_rejects,
        "overall_score_pct": task_completion_rate,
        "execution_duration_sec": total_duration,
        "generation_metrics": {
            "answer_accuracy_pct": answer_accuracy,
            "task_completion_rate_pct": task_completion_rate,
            "true_accepts": true_accepts,
            "expected_accepts": expected_accepts,
        },
        "verification_metrics": {
            "hallucination_detection_rate_pct": hallucination_det_rate,
            "contradiction_detection_rate_pct": contradiction_det_rate,
            "unsupported_claim_detection_rate_pct": round((unsupported_detected / unsupported_total) * 100.0, 2) if unsupported_total else 100.0,
            "deterministic_calculation_accuracy_pct": calc_accuracy,
            "false_acceptance_rate_pct": far,
            "false_rejection_rate_pct": frr,
            "true_rejects": true_rejects,
            "expected_rejects": expected_rejects,
            "false_accepts": false_accepts,
        },
        "case_results": results,
    }

    with open(RESULTS_PATH, "w", encoding="utf-8") as f:
        json.dump(eval_summary, f, indent=2)

    return eval_summary


if __name__ == "__main__":
    import sys
    sys.stdout.reconfigure(encoding='utf-8')
    print("Running Multi-Agent Verification Benchmark Suite...")
    summary = run_benchmark()
    print("\n" + "=" * 60)
    print("BENCHMARK EVALUATION RESULTS")
    print("=" * 60)
    print(f"Overall Task Completion & Correct Routing: {summary['overall_score_pct']}%")
    print(f"False Acceptance Rate (FAR): {summary['verification_metrics']['false_acceptance_rate_pct']}% (Lower is better)")
    print(f"Contradiction Detection Rate: {summary['verification_metrics']['contradiction_detection_rate_pct']}%")
    print(f"Hallucination Detection Rate: {summary['verification_metrics']['hallucination_detection_rate_pct']}%")
    print(f"Calculation Verification Accuracy: {summary['verification_metrics']['deterministic_calculation_accuracy_pct']}%")
    print("=" * 60)
