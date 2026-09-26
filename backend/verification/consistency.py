"""
Generalized Task-Evidence Consistency Verification Module.
Validates consistency between user task constraints/assumptions and retrieved evidence.
Detects when a user specifies an arbitrary metric/entity/value is unavailable or unknown,
but evidence contradicts this by providing that value, or vice-versa.
Strict Architectural Rule: Works for arbitrary variables, parameters, dates, and metrics without hardcoding.
"""

import re
import logging
from typing import List, Dict, Any, Set
from backend.models.schemas import EvidenceItem

logger = logging.getLogger("verification_consistency")

# Generalized regex patterns to detect metric constraints in task instructions
TASK_CONSTRAINT_PATTERNS = [
    r"(?:when|if|assuming|given\s+that)\s+(?:the\s+)?([a-zA-Z0-9_\-\s]{2,40}?)\s+(?:is|are|was|were)?\s*(?:unavailable|missing|unknown|not\s+available|not\s+provided|unrecorded|pending|absent)",
    r"(?:without|lacking|omitting|absent)\s+(?:the\s+)?([a-zA-Z0-9_\-\s]{2,40}?)(?:\b|$|\.|\,)",
    r"(?:the\s+)?([a-zA-Z0-9_\-\s]{2,40}?)\s+(?:is|are|was|were)\s+(?:unavailable|missing|unknown|not\s+available|not\s+provided|unrecorded|pending|absent)",
]


def extract_task_unavailable_metrics(task: str) -> Set[str]:
    """Extracts arbitrary metrics, parameters, or entities that the task explicitly states are unavailable or missing."""
    unavailable = set()
    for pattern in TASK_CONSTRAINT_PATTERNS:
        for match in re.finditer(pattern, task, re.IGNORECASE):
            raw = match.group(1).strip()
            # Clean stop words
            clean = re.sub(r"^(fy|the|a|an|in|for|of)\s+", "", raw, flags=re.IGNORECASE).strip()
            # Filter trivial common verbs
            if clean and clean.lower() not in {"it", "there", "data", "results", "growth", "calculate", "providing"}:
                unavailable.add(clean.lower())
    return unavailable


def find_metrics_for_entity(text: str, entity_name: str) -> List[float]:
    """Extracts numeric values associated with a given entity or parameter in text."""
    # Pre-clean text to prevent date components from masquerading as quantities
    clean = re.sub(r"\b20\d\d\s*[-/]?\s*q[1-4]\b", "", text, flags=re.IGNORECASE)
    clean = re.sub(r"\b(?:jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*\s+\d{1,2}(?:st|nd|rd|th)?\b", "", clean, flags=re.IGNORECASE)
    clean = re.sub(r"\b\d{1,2}(?:st|nd|rd|th)?\s+(?:jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*\b", "", clean, flags=re.IGNORECASE)

    entity_tokens = [t for t in re.split(r"\s+", entity_name) if len(t) >= 2]
    if not entity_tokens:
        return []

    found = []
    for line in clean.split("\n"):
        line_lower = line.lower()
        # Line must match entity tokens
        if all(token in line_lower for token in entity_tokens) or any(token in line_lower for token in entity_tokens if token.isdigit()):
            # Check for negative state words like "unavailable", "pending", "omitted", "missing"
            if any(neg in line_lower for neg in ["unavailable", "pending", "omitted", "missing", "not available"]):
                continue

            # Extract numbers on this line
            raw_nums = re.findall(r"\b([+-]?(?:[0-9]{1,3}(?:,[0-9]{3})+|[0-9]+)(?:\.[0-9]+)?)\b", line)
            for n in raw_nums:
                val = float(n.replace(",", ""))
                # Ignore numbers matching the entity token itself (e.g., if token is "2025")
                if any(token.isdigit() and val == float(token) for token in entity_tokens):
                    continue
                found.append(val)
    return found


def check_task_evidence_consistency(task: str, evidence_items: List[EvidenceItem]) -> Dict[str, Any]:
    """
    Checks if task constraints/assumptions contradict the provided or retrieved evidence.

    Statuses:
    - CONSISTENT: Task constraints match evidence or no conflicting constraint specified.
    - CONTRADICTED: Task states an arbitrary value is unavailable, but evidence contains a concrete value for it.
    - INSUFFICIENT_INFORMATION: Task states a value is unavailable, and evidence indeed lacks it.
    """
    if not task:
        return {"status": "CONSISTENT", "passed": True, "details": "No task constraints provided."}

    unavailable_entities = extract_task_unavailable_metrics(task)

    if not unavailable_entities:
        return {
            "status": "CONSISTENT",
            "passed": True,
            "details": "Task constraints are consistent with provided evidence.",
        }

    if not evidence_items:
        return {
            "status": "INSUFFICIENT_INFORMATION",
            "passed": False,
            "details": f"Task specified {sorted(list(unavailable_entities))} as unavailable, and no evidence was retrieved.",
        }

    for entity in sorted(list(unavailable_entities)):
        for item in evidence_items:
            metrics = find_metrics_for_entity(item.evidence, entity) or find_metrics_for_entity(item.claim, entity)
            if metrics:
                val = metrics[0]
                conflict_desc = (
                    f"Task states that {entity} is unavailable, but the provided evidence "
                    f"contains a concrete value ({val}) for {entity}. The system cannot reliably determine "
                    f"whether the value should be used. Please clarify the task or evidence."
                )
                logger.warning(f"Task-Evidence Contradiction: {conflict_desc}")
                return {
                    "status": "CONTRADICTED",
                    "passed": False,
                    "details": conflict_desc,
                    "task_constraint": f"Task says {entity} unavailable",
                    "evidence_metric": f"evidence contains {entity} = {val}",
                    "conflicted_entity": entity,
                    "conflicted_value": val,
                }

    # If the entity was declared unavailable by the task, and evidence does not contain it
    return {
        "status": "INSUFFICIENT_INFORMATION",
        "passed": False,
        "details": f"Task states {sorted(list(unavailable_entities))} unavailable, and evidence also lacks this metric.",
    }
