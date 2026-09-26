"""
Safety Verification Module.
Screens requests and code against security policies, prompt injections, and dangerous operations.
"""

import re
import logging
from typing import List, Tuple
from backend.models.schemas import SafetyOutput

logger = logging.getLogger("verification_safety")

DANGEROUS_PATTERNS = [
    (r"rm\s+-rf", "Destructive file removal command detected"),
    (r"os\.system", "Arbitrary system execution call"),
    (r"subprocess\.", "Subprocess execution invocation"),
    (r"shutil\.rmtree", "Recursive filesystem removal attempt"),
    (r"format\s+[c-z]:", "Drive format command"),
    (r":\(\)\s*\{\s*:\s*\|\s*:\s*&\s*\}\s*;", "Fork bomb pattern"),
    (r"curl\s+.*\|\s*sh", "Piping remote script to shell"),
    (r"wget\s+.*\|\s*sh", "Piping remote script to shell"),
    (r"drop\s+database", "Database drop command"),
    (r"cat\s+/etc/shadow", "Sensitive password file access"),
    (r"dump\s+system\s+passwords", "Credential dump instruction"),
    (r"\beval\s*\(", "Forbidden arbitrary eval execution"),
    (r"\bexec\s*\(", "Forbidden arbitrary exec execution"),
]

PROMPT_INJECTION_PATTERNS = [
    (r"ignore\s+(all\s+)?previous\s+instructions", "Prompt injection: override instructions"),
    (r"bypass\s+all\s+rules", "Prompt injection: rule bypass"),
    (r"you\s+are\s+now\s+in\s+DAN\s+mode", "Jailbreak attempt: DAN mode"),
]


def check_action_safety(action_or_code: str) -> SafetyOutput:
    """
    Evaluates proposed actions or generated code against safety policies.
    """
    flagged: List[str] = []
    highest_risk = "SAFE"

    # Screen dangerous patterns
    for pattern, reason in DANGEROUS_PATTERNS:
        if re.search(pattern, action_or_code, re.IGNORECASE):
            flagged.append(reason)
            highest_risk = "CRITICAL"

    # Screen prompt injection patterns
    for pattern, reason in PROMPT_INJECTION_PATTERNS:
        if re.search(pattern, action_or_code, re.IGNORECASE):
            flagged.append(reason)
            if highest_risk != "CRITICAL":
                highest_risk = "HIGH"

    if flagged:
        logger.warning(f"Safety check violation: {flagged}")
        return SafetyOutput(
            is_safe=False,
            risk_level=highest_risk,
            reason=f"Security violation detected: {'; '.join(flagged)}",
            flagged_elements=flagged,
        )

    return SafetyOutput(
        is_safe=True,
        risk_level="SAFE",
        reason="Action validated: No security or policy violations detected.",
        flagged_elements=[],
    )
