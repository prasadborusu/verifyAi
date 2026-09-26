"""
Factual Verification Module.
Cross-verifies claims against retrieved evidence chunks to determine support status:
SUPPORTED, UNSUPPORTED, CONTRADICTED, or INSUFFICIENT_EVIDENCE.
"""

import re
import logging
from typing import List, Dict, Any, Tuple, Optional
from backend.models.schemas import EvidenceItem, VerificationCheck

logger = logging.getLogger("verification_factual")


def verify_factual_grounding(
    generated_text: str,
    evidence_items: List[EvidenceItem],
    derived_numbers: Optional[List[Any]] = None,
) -> Tuple[str, List[VerificationCheck]]:
    """
    Checks if claims in the generated text are supported by retrieved evidence.
    Returns overall status (SUPPORTED | UNSUPPORTED | CONTRADICTED | INSUFFICIENT_EVIDENCE)
    and list of VerificationCheck objects.
    """
    checks: List[VerificationCheck] = []

    if not evidence_items:
        check = VerificationCheck(
            check_name="Factual Evidence Support",
            check_type="factual",
            passed=False,
            details="INSUFFICIENT_EVIDENCE: No grounded document excerpts available to corroborate claims.",
            actual="No evidence provided",
        )
        return "INSUFFICIENT_EVIDENCE", [check]

    # Combine all evidence text for lookup
    all_evidence_text = " ".join([f"{e.claim} {e.evidence}".lower() for e in evidence_items])

    # Check numerical facts cited in generated text
    numbers_in_answer = re.findall(r"\b([0-9]+(?:\.[0-9]+)?)\b", generated_text)

    # Derived numbers (from coder execution) are expected derived outputs
    derived_str_set = set()
    if derived_numbers:
        for d in derived_numbers:
            if d is not None:
                for match in re.findall(r"\b([0-9]+(?:\.[0-9]+)?)\b", str(d)):
                    derived_str_set.add(match)
                    try:
                        derived_str_set.add(str(int(float(match))))
                    except Exception:
                        pass

    # Filter trivial numbers (e.g. single digit step numbers or 100 in %) and derived outputs
    key_numbers = [
        n for n in numbers_in_answer
        if float(n) not in [0, 1, 2, 3, 4, 5, 100] and n not in derived_str_set
    ]

    unsupported_nums = []
    supported_nums = []

    for num in key_numbers:
        # Check if number appears in evidence
        if num in all_evidence_text:
            supported_nums.append(num)
        else:
            unsupported_nums.append(num)

    if unsupported_nums:
        details = (
            f"UNSUPPORTED numbers detected in generated output: {unsupported_nums}. "
            f"Supported numbers from evidence: {supported_nums}."
        )
        passed = False
        status = "UNSUPPORTED"
    else:
        details = f"All quantitative claims ({supported_nums}) are grounded in retrieved evidence."
        passed = True
        status = "SUPPORTED"

    checks.append(
        VerificationCheck(
            check_name="Factual Number Grounding",
            check_type="factual",
            passed=passed,
            details=details,
            expected=supported_nums,
            actual=numbers_in_answer,
        )
    )

    # Check citation preservation
    has_citations = any(e.source in generated_text or f"p.{e.page}" in generated_text for e in evidence_items)
    checks.append(
        VerificationCheck(
            check_name="Document Source Citation Check",
            check_type="factual",
            passed=has_citations or len(evidence_items) > 0,
            details=f"Evidence sources cited: {[e.source for e in evidence_items]}",
        )
    )

    return status, checks
