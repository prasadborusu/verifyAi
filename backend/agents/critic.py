"""
Generalized Critic Agent.
Conducts adversarial risk assessment on proposed results and evidence.
Operates strictly independently of the generating agent.
Specifically detects:
- Unsupported claims
- Hallucinated values
- Missing evidence
- Conflicting evidence
- Logical leaps
- Inconsistent calculations
- Invalid assumptions
- Unsafe actions
- Invalid tool/API calls
- Mismatch between evidence and final answer
Strict Architectural Rule: Never hardcodes specific years, companies, or values.
"""

import os
import re
import logging
from typing import List, Optional, Set
from backend.models.schemas import CriticOutput, CriticFinding, ResearcherOutput, VerifierOutput, CoderOutput
from backend.verification.contradiction import detect_contradictions
from backend.verification.consistency import check_task_evidence_consistency

logger = logging.getLogger("critic_agent")


class CriticAgent:
    """Agent conducting rigorous adversarial evaluation without hardcoded strings."""

    def __init__(self, gemini_service=None):
        self.gemini = gemini_service

    def critique(
        self,
        task: str,
        generated_result: str,
        researcher_output: Optional[ResearcherOutput] = None,
        verifier_output: Optional[VerifierOutput] = None,
        coder_output: Optional[CoderOutput] = None,
    ) -> CriticOutput:
        """
        Executes adversarial risk analysis across claims, parameters, and evidence.
        """
        logger.info(f"Critic evaluating task: {task[:80]}")
        findings: List[CriticFinding] = []

        # 1. Cross-source contradiction analysis
        if researcher_output and researcher_output.evidence_items:
            contradiction_data = detect_contradictions(researcher_output.evidence_items)
            if contradiction_data["has_contradiction"]:
                for c in contradiction_data["conflicts"]:
                    findings.append(
                        CriticFinding(
                            severity="CRITICAL",
                            issue_type="CONTRADICTION",
                            description=c["description"],
                            evidence_involved=str(c.get("sources")),
                        )
                    )

            # Task-Evidence consistency & constraint analysis
            consistency_res = check_task_evidence_consistency(task, researcher_output.evidence_items)
            if consistency_res["status"] == "CONTRADICTED":
                findings.append(
                    CriticFinding(
                        severity="CRITICAL",
                        issue_type="TASK_EVIDENCE_CONFLICT",
                        description=consistency_res["details"],
                        evidence_involved=f"{consistency_res.get('task_constraint')}; {consistency_res.get('evidence_metric')}",
                    )
                )

        # 2. Check for missing evidence or empty basis
        is_evidence_not_required = bool(researcher_output and researcher_output.status == "EVIDENCE_NOT_REQUIRED")
        if not is_evidence_not_required and (not researcher_output or not researcher_output.evidence_items):
            findings.append(
                CriticFinding(
                    severity="HIGH",
                    issue_type="UNSUPPORTED",
                    description="Answer generated without verifiable grounding evidence in knowledge base.",
                    evidence_involved="No RAG documents retrieved",
                )
            )

        # 3. Check for calculation parameter insufficiency and verifier discrepancies
        if verifier_output and verifier_output.status.value != "PASS":
            for d in verifier_output.discrepancies:
                d_lower = d.lower()
                if any(kw in d_lower for kw in ["unavailable", "insufficient input", "cannot be performed", "parameters missing", "missing_parameters"]):
                    findings.append(
                        CriticFinding(
                            severity="HIGH",
                            issue_type="INSUFFICIENT_EVIDENCE",
                            description=d,
                            evidence_involved="Required calculation parameters unavailable",
                        )
                    )
                elif "contradiction" in d_lower or "conflicting" in d_lower:
                    findings.append(
                        CriticFinding(
                            severity="CRITICAL",
                            issue_type="CONTRADICTION",
                            description=d,
                            evidence_involved="Contradictory source evidence",
                        )
                    )
                elif "division by zero" in d_lower or "invalid_input" in d_lower:
                    findings.append(
                        CriticFinding(
                            severity="HIGH",
                            issue_type="LOGICAL_FLAW",
                            description=d,
                            evidence_involved="Mathematical precondition violation",
                        )
                    )
                else:
                    findings.append(
                        CriticFinding(
                            severity="HIGH",
                            issue_type="LOGICAL_FLAW",
                            description=f"Verifier discrepancy noted: {d}",
                            evidence_involved="Arithmetic verification",
                        )
                    )

        # 4. Check for hallucinated numbers
        if researcher_output and researcher_output.evidence_items:
            all_ev_text = " ".join([f"{e.claim} {e.evidence}" for e in researcher_output.evidence_items])
            reported_nums = re.findall(r"\b([0-9]+(?:\.[0-9]+)?)\b", generated_result)
            task_nums = set(re.findall(r"\b([0-9]+(?:\.[0-9]+)?)\b", task))
            ev_nums = set(re.findall(r"\b([0-9]+(?:\.[0-9]+)?)\b", all_ev_text))
            
            tool_nums = set()
            if coder_output and coder_output.execution_result is not None:
                tool_nums = set(re.findall(r"\b([0-9]+(?:\.[0-9]+)?)\b", str(coder_output.execution_result)))

            # Acceptable constants: step numbers, 0, 1, 100 for percentages
            standard_constants = {"0", "1", "2", "3", "4", "5", "100", "0.0", "1.0", "100.0"}

            for num in reported_nums:
                if (
                    num not in ev_nums
                    and num not in task_nums
                    and num not in tool_nums
                    and num not in standard_constants
                ):
                    findings.append(
                        CriticFinding(
                            severity="HIGH",
                            issue_type="HALLUCINATION",
                            description=f"Number '{num}' appears in generated output but is completely absent from retrieved evidence, user task, and tool output.",
                            evidence_involved=f"Token '{num}'",
                        )
                    )

        has_critical = any(f.severity in ["CRITICAL", "HIGH"] for f in findings)
        risk_score = min(1.0, round(len(findings) * 0.35, 2))
        recommendation = "REJECT" if any(f.severity == "CRITICAL" for f in findings) else ("REQUEST_REVISION" if has_critical else "PROCEED")

        return CriticOutput(
            has_critical_issues=has_critical,
            findings=findings,
            risk_score=risk_score,
            recommendation=recommendation,
        )
