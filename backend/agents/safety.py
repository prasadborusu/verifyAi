"""
Safety Agent.
Inspects tool operations, generated code, and proposed user commands before execution.
Rejects any execution violating sandbox security or privacy policies.
"""

import os
import logging
from typing import Optional
from backend.models.schemas import SafetyOutput
from backend.verification.safety import check_action_safety
from backend.services.gemini import get_gemini_service

logger = logging.getLogger("safety_agent")

PROMPT_TEMPLATE_PATH = os.path.join(os.path.dirname(__file__), "..", "..", "prompts", "safety.txt")


def load_prompt_template() -> str:
    try:
        with open(PROMPT_TEMPLATE_PATH, "r", encoding="utf-8") as f:
            return f.read()
    except Exception:
        return "Inspect proposed actions and code for safety and security."


class SafetyAgent:
    """Agent that guards against unsafe actions or code execution."""

    def __init__(self, gemini_service=None):
        self.gemini = gemini_service or get_gemini_service()
        self.prompt_template = load_prompt_template()

    def inspect(self, action_description: str, code_to_execute: Optional[str] = None) -> SafetyOutput:
        """
        Inspects text and code for dangerous operations.
        Combines deterministic regex/AST inspection with semantic policy check.
        """
        target_content = f"{action_description}\n{code_to_execute or ''}"

        # First, deterministic rule-based safety screening
        det_result = check_action_safety(target_content)
        if not det_result.is_safe:
            return det_result

        # If LLM available, perform secondary semantic check
        if self.gemini.is_available():
            prompt = (
                f"{self.prompt_template}\n\n"
                f"ACTION / CODE TO INSPECT:\n{target_content}\n\n"
                f"Return SafetyOutput schema."
            )
            try:
                llm_res = self.gemini.generate(prompt=prompt, structured_schema=SafetyOutput)
                if isinstance(llm_res, SafetyOutput) and not llm_res.is_safe:
                    return llm_res
            except Exception as e:
                logger.warning(f"LLM safety inspection skipped ({e}). Relying on deterministic check.")

        return det_result
