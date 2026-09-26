"""
Generalized Independent Verifier Agent.
The core gatekeeper: enforces strict separation of generation and verification.
Never trusts generated text blindly; runs independent deterministic checks on calculations,
input provenance, factual grounding, cross-source contradictions, task-evidence consistency, citations, and sandboxed code.
"""

import os
import re
import logging
from typing import List, Dict, Any, Optional
from backend.models.schemas import (
    VerifierOutput,
    VerificationStatus,
    FinalDecision,
    VerificationCheck,
    ResearcherOutput,
    CoderOutput,
    PlannerOutput,
    ContradictionReport,
)
from backend.verification.calculation import verify_calculation, extract_numerical_value_from_generated
from backend.verification.factual import verify_factual_grounding
from backend.verification.code import verify_code_execution
from backend.verification.consistency import check_task_evidence_consistency
from backend.verification.contradiction import detect_contradictions
from backend.services.gemini import get_gemini_service

logger = logging.getLogger("verifier_agent")


class VerifierAgent:
    """Agent that independently verifies all intermediate and final outputs without hardcoding."""

    def __init__(self, gemini_service=None):
        self.gemini = gemini_service or get_gemini_service()

    def verify(
        self,
        task: str,
        generated_result: str,
        researcher_output: Optional[ResearcherOutput] = None,
        coder_output: Optional[CoderOutput] = None,
        planner_output: Optional[PlannerOutput] = None,
    ) -> VerifierOutput:
        """
        Executes comprehensive independent verification suite.
        Verifies both arithmetic and input justification independently.
        """
        logger.info(f"Independent verifier checking task: {task[:80]}")
        checks: List[VerificationCheck] = []
        discrepancies: List[str] = []

        # 0. Check for task in General Reasoning mode (no external documents attached)
        has_docs = bool(researcher_output and researcher_output.evidence_items and researcher_output.status not in ("EVIDENCE_NOT_REQUIRED", "INSUFFICIENT_EVIDENCE"))
        if (researcher_output and researcher_output.status == "EVIDENCE_NOT_REQUIRED") or not has_docs:
            from backend.verification.router import determine_verification_route, verify_factual_claim, verify_logic_claim
            from backend.verification.general_reasoning import verify_self_contained_task, is_self_contained_task

            v_route = determine_verification_route(task)

            # Route A: NUMERIC / COMPUTATIONAL
            if v_route == "NUMERIC" or is_self_contained_task(task):
                passed, self_checks, reason = verify_self_contained_task(
                    task=task,
                    generated_result=generated_result,
                    coder_output=coder_output,
                    planner_output=planner_output,
                )
                discrepancies = [] if passed else [reason]
                status = VerificationStatus.PASS if passed else VerificationStatus.FAIL
                action = FinalDecision.ACCEPT if passed else FinalDecision.REJECT
                calc_val = coder_output.execution_result if coder_output and coder_output.execution_result else None
                return VerifierOutput(
                    status=status,
                    reason=reason,
                    confidence=0.99 if passed else 0.0,
                    checks=self_checks,
                    discrepancies=discrepancies,
                    recommended_action=action,
                    calculated_value=calc_val,
                )

            # Route B: LOGIC / SYLLOGISMS
            elif v_route == "LOGIC":
                passed, reason, conf, logic_checks = verify_logic_claim(task, generated_result)
                status = VerificationStatus.PASS if passed else VerificationStatus.FAIL
                action = FinalDecision.ACCEPT if passed else FinalDecision.REJECT
                return VerifierOutput(
                    status=status,
                    reason=reason,
                    confidence=conf,
                    checks=logic_checks,
                    discrepancies=[] if passed else [reason],
                    recommended_action=action,
                    calculated_value=None,
                )

            # Route C: GENERAL FACTUAL & CONCEPTUAL INQUIRIES
            else:
                passed, reason, conf, fact_checks, corr = verify_factual_claim(
                    task=task,
                    candidate_answer=generated_result,
                    claims=[generated_result],
                    gemini_service=self.gemini,
                )
                status = VerificationStatus.PASS if passed else VerificationStatus.FAIL
                action = FinalDecision.ACCEPT if passed else FinalDecision.REJECT
                return VerifierOutput(
                    status=status,
                    reason=reason,
                    confidence=conf,
                    checks=fact_checks,
                    discrepancies=[] if passed else [reason],
                    recommended_action=action,
                    calculated_value=None,
                    expected_value=corr if corr else None,
                )

        # 1. Evidence sufficiency precondition check
        if not researcher_output or researcher_output.status == "INSUFFICIENT_EVIDENCE":
            checks.append(
                VerificationCheck(
                    check_name="Evidence Grounding Precondition",
                    check_type="factual",
                    passed=False,
                    details="Verification halted: Required evidence was absent or insufficient in RAG repository.",
                )
            )
            return VerifierOutput(
                status=VerificationStatus.NEEDS_EVIDENCE,
                reason="Required source evidence was insufficient to verify claims.",
                confidence=0.0,
                checks=checks,
                discrepancies=["Insufficient evidence in uploaded documents."],
                recommended_action=FinalDecision.REJECT,
            )

        # 2. Cross-Source Contradiction Precondition & Resolution Check
        c_report = getattr(researcher_output, "contradiction_report", None)
        if not c_report and researcher_output.evidence_items:
            c_data = detect_contradictions(researcher_output.evidence_items)
            c_report = ContradictionReport(
                contradiction_detected=c_data.get("contradiction_detected", False),
                contradiction_count=c_data.get("contradiction_count", 0),
                unresolved_contradictions=c_data.get("unresolved_contradictions", []),
                resolved_contradictions=c_data.get("resolved_contradictions", []),
                resolution_basis=c_data.get("resolution_basis", []),
                verification_status=c_data.get("verification_status", "PASS"),
                final_decision=c_data.get("final_decision", FinalDecision.ACCEPT),
            )

        has_unresolved_contra = False
        if c_report:
            if c_report.resolved_contradictions:
                checks.append(
                    VerificationCheck(
                        check_name="Objective Contradiction Resolution",
                        check_type="contradiction",
                        passed=True,
                        details=f"Conflict objectively resolved via metadata: {'; '.join(c_report.resolution_basis)}",
                    )
                )

            if c_report.unresolved_contradictions:
                has_unresolved_contra = True
                for u in c_report.unresolved_contradictions:
                    checks.append(
                        VerificationCheck(
                            check_name=f"Contradiction Guard: {u.get('entity', 'metric')}",
                            check_type="contradiction",
                            passed=False,
                            details=u.get("description", "Conflicting sources detected"),
                        )
                    )
                    discrepancies.append(u.get("description", "Contradictory values detected across sources."))

        elif researcher_output.status == "CONFLICTING_EVIDENCE":
            has_unresolved_contra = True
            checks.append(
                VerificationCheck(
                    check_name="Cross-Source Contradiction Precondition",
                    check_type="contradiction",
                    passed=False,
                    details="Unreconciled contradiction detected across retrieved source documents.",
                )
            )
            discrepancies.append("Multiple independent sources report conflicting and incompatible values.")

        # 3. Input Provenance & Justification Check (Never verify only arithmetic!)
        if coder_output and coder_output.input_references:
            for ref in coder_output.input_references:
                if ref.is_conflicted:
                    has_unresolved_contra = True
                    checks.append(
                        VerificationCheck(
                            check_name=f"Input Provenance: {ref.parameter_name}",
                            check_type="contradiction",
                            passed=False,
                            details=(
                                f"Input '{ref.parameter_name}' was selected as {ref.selected_value} from '{ref.source_name}', "
                                f"but alternative conflicting evidence exists across sources without objective resolution."
                            ),
                        )
                    )
                    discrepancies.append(f"Unjustified input selection: '{ref.parameter_name}' has unresolved conflicting evidence.")

        # 4. Task-Evidence Consistency Check
        consistency_res = check_task_evidence_consistency(task, researcher_output.evidence_items)
        consistency_check = VerificationCheck(
            check_name="Task-Evidence Consistency Check",
            check_type="consistency",
            passed=consistency_res["passed"],
            details=consistency_res["details"],
            actual=consistency_res.get("evidence_metric", consistency_res["status"]),
            expected=consistency_res.get("task_constraint", "Consistent constraints"),
        )
        checks.append(consistency_check)
        if not consistency_res["passed"]:
            discrepancies.append(consistency_res["details"])

        # 5. Independent factual grounding check
        derived_vals = [coder_output.execution_result] if coder_output else []
        fact_status, fact_checks = verify_factual_grounding(
            generated_text=generated_result,
            evidence_items=researcher_output.evidence_items,
            derived_numbers=derived_vals,
        )
        checks.extend(fact_checks)
        if fact_status in ["UNSUPPORTED", "CONTRADICTED"]:
            discrepancies.append(f"Factual check failure: {fact_status}")

        # 6. Independent Parameter-Aware Calculation Verification (Deterministic Python arithmetic)
        calc_check = None
        needs_calculation = any(w in task.lower() for w in ["calculate", "growth", "percentage", "%", "ratio", "sum", "average", "difference", "cagr"])

        if coder_output and coder_output.inputs:
            inputs = coder_output.inputs
            if inputs.get("formula") == "factual_multi_period" or not needs_calculation:
                formula_type = inputs.get("formula", "single_value")
            elif "value" in inputs and not any(k in inputs for k in ["initial", "final"]):
                formula_type = "single_value"
            elif any(w in task.lower() for w in ["ratio", "division", "divide"]):
                formula_type = "ratio"
            elif any(w in task.lower() for w in ["sum", "total", "summation"]):
                formula_type = "sum"
            elif any(w in task.lower() for w in ["difference", "subtract", "minus", "gap"]) or inputs.get("formula") == "final - initial":
                formula_type = "difference"
            else:
                formula_type = "growth"

            calc_check = verify_calculation(
                generated_result=coder_output.execution_result,
                formula_type=formula_type,
                inputs=inputs,
            )
            checks.append(calc_check)
            if not calc_check.passed:
                if getattr(calc_check, "calculation_status", None) in ["INSUFFICIENT_INPUT", "CONFLICTING_INPUT", "INVALID_INPUT"]:
                    discrepancies.append(calc_check.details)
                else:
                    discrepancies.append(f"Calculation check failure: {calc_check.details}")

        elif needs_calculation:
            checks.append(
                VerificationCheck(
                    check_name="Quantitative Calculation Requirement",
                    check_type="calculation",
                    passed=False,
                    details="Task requested numerical calculation, but execution could not formulate or verify a valid quantitative result.",
                    calculation_status="INSUFFICIENT_INPUT",
                )
            )
            discrepancies.append("Calculation incomplete or parameters missing.")

        # 6b. Task Hypothesis Refutation / Confirmation Check
        hypo_match = re.search(
            r"(?:confirm|verify|check|validate|is\s+it\s+true)\s+(?:that|if|whether)?.*?\b(?:reached|equals?|was|were|is|are|at|of|grew\s+by|increased\s+by)\s*([0-9]+(?:\.[0-9]+)?)\s*(%|[a-zA-Z]+)?",
            task,
            re.IGNORECASE,
        )
        if hypo_match:
            try:
                claimed_val = float(hypo_match.group(1))
                is_pct = hypo_match.group(2) == "%" or "%" in task
                actual_res_num = None
                if coder_output and coder_output.execution_result is not None:
                    actual_res_num = extract_numerical_value_from_generated(coder_output.execution_result)

                if actual_res_num is not None and not (1900 <= claimed_val <= 2099 and not is_pct):
                    diff = abs(actual_res_num - claimed_val)
                    if diff > 0.05:
                        checks.append(
                            VerificationCheck(
                                check_name="Task Hypothesis Verification",
                                check_type="factual",
                                passed=False,
                                details=(
                                    f"Task hypothesis refutation: Task asked to verify if value is {claimed_val}"
                                    f"{'%' if is_pct else ''}, but verified evidence proves it is {actual_res_num}"
                                    f"{'%' if is_pct else ''} (Discrepancy: {diff:.2f})."
                                ),
                                expected=claimed_val,
                                actual=actual_res_num,
                            )
                        )
                        discrepancies.append(
                            f"Task hypothesis contradicted: Claimed {claimed_val} does not match verified {actual_res_num}."
                        )
            except (ValueError, TypeError):
                pass

        # 7. Sandboxed Code verification (if code was executed)
        if coder_output and coder_output.code and not coder_output.code.startswith("#"):
            code_chk = verify_code_execution(coder_output.code, coder_output.inputs)
            checks.append(code_chk)
            if not code_chk.passed:
                discrepancies.append(f"Code verification failure: {code_chk.details}")

        # 8. Independent Dataset Task Verification Suite
        ds_spec = None
        if planner_output and planner_output.dataset_task:
            ds_spec = planner_output.dataset_task
        elif researcher_output and researcher_output.evidence_items:
            for ev in researcher_output.evidence_items:
                if ev.metadata and "dataset_spec" in ev.metadata:
                    try:
                        from backend.models.schemas import DatasetTaskSpec
                        ds_spec = DatasetTaskSpec(**ev.metadata["dataset_spec"])
                        break
                    except Exception:
                        pass

        if ds_spec:
            from backend.analytics.dataset_engine import verify_dataset_execution
            ds_checks = verify_dataset_execution(
                spec=ds_spec,
                coder_output=coder_output,
                researcher_output=researcher_output,
                selected_document_ids=[ev.source for ev in researcher_output.evidence_items] if researcher_output else None,
            )
            for chk in ds_checks:
                checks.append(chk)
                if not chk.passed:
                    discrepancies.append(f"{chk.check_name}: {chk.details}")

        # Determine overall pass / fail status
        all_passed = all(c.passed for c in checks)
        expected_val = calc_check.expected if calc_check else None
        actual_val = calc_check.actual if calc_check else None

        if all_passed:
            status = VerificationStatus.PASS
            reason = "All independent checks passed: Factual grounding verified, arithmetic verified deterministically, sources cited."
            confidence = 0.98
            rec_action = FinalDecision.ACCEPT
        else:
            is_contradicted = has_unresolved_contra or consistency_res.get("status") == "CONTRADICTED"
            is_insufficient = any(getattr(c, "calculation_status", None) == "INSUFFICIENT_INPUT" for c in checks)
            status = VerificationStatus.BLOCKED if is_contradicted else VerificationStatus.FAIL
            reason = f"Verification failed on: {'; '.join(discrepancies)}"
            confidence = 0.0 if (is_contradicted or is_insufficient) else 0.25
            
            if is_contradicted:
                rec_action = FinalDecision.NEEDS_CLARIFICATION
            elif is_insufficient:
                rec_action = FinalDecision.REJECT
            else:
                rec_action = FinalDecision.REVISE

        return VerifierOutput(
            status=status,
            reason=reason,
            confidence=confidence,
            checks=checks,
            discrepancies=discrepancies,
            recommended_action=rec_action,
            calculated_value=actual_val,
            expected_value=expected_val,
        )
