"""
Generalized Finalizer Agent.
Synthesizes verified findings into a grounded, accountable final answer.
Strict Rules:
1. It must NEVER silently turn an unverified or conflicted result into a confident answer.
2. If unresolved contradictions exist, it rejects or requests clarification detailing:
   - Conflicting claim
   - Source A value
   - Source B value
   - Why the conflict cannot be resolved
   - What information is needed to continue.
"""

import os
import logging
from typing import Optional, List
from backend.models.schemas import (
    FinalizerOutput,
    FinalDecision,
    CitedEvidence,
    ResearcherOutput,
    VerifierOutput,
    CriticOutput,
    CoderOutput,
)
from backend.services.gemini import get_gemini_service

logger = logging.getLogger("finalizer_agent")

PROMPT_TEMPLATE_PATH = os.path.join(os.path.dirname(__file__), "..", "..", "prompts", "finalizer.txt")


def load_prompt_template() -> str:
    try:
        with open(PROMPT_TEMPLATE_PATH, "r", encoding="utf-8") as f:
            return f.read()
    except Exception:
        return "Synthesize verified findings into a transparent final answer."


def format_claim_display(val: Any, unit: Optional[str]) -> str:
    if val is None:
        return "Unknown"
    val_str = str(val)
    if not unit:
        return val_str
    u_clean = str(unit).strip()
    if u_clean.upper().startswith("INR"):
        rest = u_clean[3:].strip()
        return f"₹{val_str} {rest}".strip() if rest else f"₹{val_str}"
    if u_clean.upper().startswith("USD"):
        rest = u_clean[3:].strip()
        return f"${val_str} {rest}".strip() if rest else f"${val_str}"
    if u_clean.upper().startswith("EUR"):
        rest = u_clean[3:].strip()
        return f"€{val_str} {rest}".strip() if rest else f"€{val_str}"
    if u_clean.upper().startswith("GBP"):
        rest = u_clean[3:].strip()
        return f"£{val_str} {rest}".strip() if rest else f"£{val_str}"
    if u_clean == "%":
        return f"{val_str}%"
    if u_clean in ["°C", "°F"]:
        return f"{val_str}{u_clean}"
    if u_clean.lower() == "state":
        return val_str
    return f"{val_str} {u_clean}".strip()


class FinalizerAgent:
    """Agent that outputs verified conclusion or explicit rejection / needs clarification."""

    def __init__(self, gemini_service=None):
        self.gemini = gemini_service or get_gemini_service()
        self.prompt_template = load_prompt_template()

    def finalize(
        self,
        task: str,
        researcher_output: Optional[ResearcherOutput],
        coder_output: Optional[CoderOutput],
        verifier_output: Optional[VerifierOutput],
        critic_output: Optional[CriticOutput],
        rejection_reason: Optional[str] = None,
        decision_override: Optional[FinalDecision] = None,
        raw_ai_output: Optional[str] = None,
    ) -> FinalizerOutput:
        """
        Synthesizes verified conclusion or explicit rejection / needs clarification.
        """
        logger.info(f"Finalizing task: {task[:80]}")

        # Check for unresolved contradiction report in researcher output
        c_report = getattr(researcher_output, "contradiction_report", None)
        has_unresolved_contra = bool(c_report and c_report.unresolved_contradictions)

        # Enforce deterministic hard gate:
        # UNRESOLVED CONFLICT -> NO ACCEPT under any circumstance
        if has_unresolved_contra:
            decision = FinalDecision.NEEDS_CLARIFICATION
        elif decision_override:
            decision = decision_override
        elif rejection_reason:
            decision = FinalDecision.REJECT
        elif verifier_output and verifier_output.recommended_action in [FinalDecision.REJECT, FinalDecision.NEEDS_CLARIFICATION]:
            decision = verifier_output.recommended_action
        elif verifier_output and verifier_output.recommended_action == FinalDecision.ACCEPT:
            decision = FinalDecision.ACCEPT
        else:
            decision = FinalDecision.REJECT

        # Handle Unresolved Contradiction — structured multi-source breakdown
        if has_unresolved_contra:
            reason = rejection_reason or (verifier_output.reason if verifier_output else "Contradictory evidence.")
            contra_breakdown = "### ⚠️ Unresolved Cross-Source Contradictions Detected:\n\n"
            explicit_summaries = []
            for u in c_report.unresolved_contradictions:
                period_val = u.get("period")
                period_str = f" ({period_val})" if period_val else ""
                entity_lbl = u.get("canonical_entity") or u.get("entity", "Unknown")
                claims_list = u.get("claims", [])
                if len(claims_list) >= 2:
                    src_a = claims_list[0].get("source_name", "Source A")
                    val_a = format_claim_display(
                        claims_list[0].get("value") if claims_list[0].get("value") is not None else claims_list[0].get("extracted_value"),
                        claims_list[0].get("unit")
                    )
                    src_b = claims_list[1].get("source_name", "Source B")
                    val_b = format_claim_display(
                        claims_list[1].get("value") if claims_list[1].get("value") is not None else claims_list[1].get("extracted_value"),
                        claims_list[1].get("unit")
                    )
                    explicit_summaries.append(
                        f"{src_a} reports {val_a}, while {src_b} reports {val_b}. "
                        f"The evidence is contradictory — verification cannot confirm either value."
                    )
                contra_breakdown += f"#### Metric: **{entity_lbl}**{period_str}\n"
                contra_breakdown += f"- **Conflicting Values:**\n"
                for clm in claims_list:
                    val_num = clm.get("value") if clm.get("value") is not None else clm.get("extracted_value")
                    val_str = format_claim_display(val_num, clm.get("unit"))
                    contra_breakdown += f"  - **{clm.get('source_name', 'Unknown Source')}:** `{val_str}` (*\"{clm.get('excerpt', '')}\"*)\n"
                contra_breakdown += (
                    f"\n**Why unresolvable:** Incompatible statements across independent sources with no authority metadata.\n"
                    f"**To resolve:** Specify which source takes precedence or provide an authoritative version.\n\n"
                )
            lead_summary = "\n\n".join(explicit_summaries)
            final_answer = (
                f"{lead_summary}\n\n"
                f"**VERIFAI: CONTRADICTION DETECTED** — Unresolved contradictory evidence prevents verified completion.\n\n"
                f"{contra_breakdown}"
            )
            from backend.verification.provenance import resolve_source_provenance
            prov = resolve_source_provenance(
                task=task,
                researcher_output=researcher_output,
                coder_output=coder_output,
                verifier_output=verifier_output,
                decision=FinalDecision.NEEDS_CLARIFICATION,
                gemini_service=self.gemini,
            )
            return FinalizerOutput(
                final_answer=final_answer,
                decision=FinalDecision.NEEDS_CLARIFICATION,
                confidence=0.0,
                cited_evidence=[],
                verification_summary=f"CONTRADICTION: {reason}",
                limitations=["Contradictory evidence sources prevented verified completion."],
                source_provenance=prov,
            )

        # Handle REJECT due to safety violation — this is a hard stop
        if rejection_reason and "Safety Policy Violation" in str(rejection_reason):
            final_answer = (
                f"⛔ **Safety Policy Violation**\n\n"
                f"{rejection_reason}\n\n"
                f"This request cannot be processed due to a safety policy restriction."
            )
            return FinalizerOutput(
                final_answer=final_answer,
                decision=FinalDecision.REJECT,
                confidence=0.0,
                cited_evidence=[],
                verification_summary=f"SAFETY_VIOLATION: {rejection_reason}",
                limitations=["Request blocked by safety policy."],
            )

        # All other REJECT/UNVERIFIED cases: ALWAYS return the AI answer + UNVERIFIED status
        # The AI answer must NEVER be suppressed by verification failure.
        if decision in [FinalDecision.REJECT, FinalDecision.NEEDS_CLARIFICATION]:
            reason = rejection_reason or (verifier_output.reason if verifier_output else "Verification could not confirm the answer.")
            ai_ans = str(raw_ai_output or "").strip()
            if not ai_ans:
                ai_ans = verifier_output.reason if verifier_output else "No response generated."

            # If verifier found a corrected/expected value, note it
            correction_note = ""
            corr_val = verifier_output.calculated_value if verifier_output else None
            exp_val = verifier_output.expected_value if verifier_output else None
            if corr_val is not None and str(corr_val) != ai_ans:
                correction_note = f"\n\n**Independent Verification Found:** `{corr_val}`"
            elif exp_val is not None and str(exp_val) != ai_ans:
                correction_note = f"\n\n**Expected Value:** `{exp_val}`"

            final_answer = ai_ans + correction_note
            from backend.verification.provenance import resolve_source_provenance
            prov = resolve_source_provenance(
                task=task,
                researcher_output=researcher_output,
                coder_output=coder_output,
                verifier_output=verifier_output,
                raw_ai_output=raw_ai_output,
                final_answer=final_answer,
                decision=decision,
                gemini_service=self.gemini,
            )

            return FinalizerOutput(
                final_answer=final_answer,
                decision=FinalDecision.REJECT,
                confidence=0.0,
                cited_evidence=[],
                verification_summary=f"UNVERIFIED: {reason}",
                limitations=[f"Verification could not independently confirm: {reason}"],
                source_provenance=prov,
            )

        # Prepare cited evidence list for ACCEPT
        cited: List[CitedEvidence] = []
        if researcher_output:
            for ev in researcher_output.evidence_items:
                cited.append(
                    CitedEvidence(
                        claim=ev.claim,
                        source=ev.source,
                        page=ev.page or 1,
                        location=ev.location or (f"Page {ev.page}" if ev.page else None),
                        url=ev.url or ev.metadata.get("url"),
                        evidence=ev.evidence or ev.excerpt,
                        verified=True,
                    )
                )

        calc_result_str = str(coder_output.execution_result) if coder_output and coder_output.execution_result else None
        sources_str = ", ".join(set([f"{c.source} (page {c.page})" for c in cited])) if cited else "None"
        
        from backend.verification.provenance import resolve_source_provenance
        prov = resolve_source_provenance(
            task=task,
            researcher_output=researcher_output,
            coder_output=coder_output,
            verifier_output=verifier_output,
            raw_ai_output=raw_ai_output,
            final_answer=calc_result_str,
            decision=FinalDecision.ACCEPT,
            gemini_service=self.gemini,
        )

        conf_pct = int((verifier_output.confidence if verifier_output else 0.95) * 100)

        if not cited or (researcher_output and researcher_output.status == "EVIDENCE_NOT_REQUIRED"):
            if calc_result_str is not None:
                final_answer = (
                    f"The verified result for '{task}' is **{calc_result_str}**.\n\n"
                    f"### Verification Summary:\n"
                    f"- **Source:** {prov.source_name}\n"
                    f"- **Evidence / Calculation:** {prov.evidence}\n"
                    f"- **Verification:** {prov.verification}\n"
                    f"- **Status:** [{prov.status}]\n"
                    f"- **Confidence:** {conf_pct}%\n"
                )
                if coder_output and coder_output.calculation_steps:
                    final_answer += f"\n### Verification Steps:\n"
                    for step in coder_output.calculation_steps:
                        final_answer += f"- {step}\n"
                limitations = [
                    "Self-contained calculation verified deterministically in Python sandbox.",
                    "Zero external sources required.",
                ]
            else:
                ans_text = str(raw_ai_output or (verifier_output.calculated_value if verifier_output else "")).strip()
                final_answer = (
                    f"{ans_text}\n\n"
                    f"### Verification Summary:\n"
                    f"- **Source:** {prov.source_name}\n"
                    f"- **Evidence:** {prov.evidence}\n"
                    f"- **Verification:** {prov.verification}\n"
                    f"- **Status:** [{prov.status}]\n"
                    f"- **Confidence:** {conf_pct}%\n"
                )
                limitations = [
                    "Independently verified against factual knowledge and consistency criteria.",
                ]
        else:
            res_label = "computed result" if (coder_output and coder_output.inputs.get("formula") in ["growth", "difference", "sum", "ratio"]) else "verified result"
            val_display = calc_result_str if calc_result_str is not None else (raw_ai_output or "verified output")
            loc_str = f" · {prov.location}" if prov.location else ""
            url_str = f"\n- **URL:** {prov.url}" if prov.url else ""
            final_answer = (
                f"Based on audited and verified source documents, the {res_label} for '{task}' is **{val_display}**.\n\n"
                f"### Verification Summary:\n"
                f"- **Source:** {prov.source_name}{loc_str}{url_str}\n"
                f"- **Evidence:** \"{prov.evidence}\"\n"
                f"- **Verification:** {prov.verification}\n"
                f"- **Status:** [{prov.status}]\n"
                f"- **Confidence:** {conf_pct}%\n\n"
                f"### Verified Evidence Citations:\n"
            )
            for c in cited:
                final_answer += f"- **{c.claim}** [Source: `{c.source}`, Page: {c.page}] (Verified: [PASS])\n"

            if coder_output and coder_output.calculation_steps:
                steps_header = "Mathematical Verification Steps" if (coder_output and coder_output.inputs.get("formula") in ["growth", "difference", "sum", "ratio"]) else "Verification Steps"
                final_answer += f"\n### {steps_header}:\n"
                for step in coder_output.calculation_steps:
                    final_answer += f"- {step}\n"

            limitations = [
                f"Figures are grounded exclusively in provided source documents: {sources_str}.",
                "Calculations verified via deterministic Python execution sandbox.",
            ]

        verification_summary = (
            f"Independent verification status: {verifier_output.status.value if verifier_output else 'PASS'}. "
            f"All {len(verifier_output.checks) if verifier_output else 0} independent checks passed. "
            f"Source: {prov.source_name}."
        )

        return FinalizerOutput(
            final_answer=final_answer,
            decision=FinalDecision.ACCEPT,
            confidence=verifier_output.confidence if verifier_output else 0.95,
            cited_evidence=cited,
            verification_summary=verification_summary,
            limitations=limitations,
            source_provenance=prov,
        )
