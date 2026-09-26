"""
Single reusable Gemini Service.
Isolated LLM service layer wrapping Google Gemini API.
Ensures zero hardcoded secrets and graceful error handling.
"""

import os
import json
import re
import logging
from typing import Optional, Type, Union, Any
from pydantic import BaseModel
from dotenv import load_dotenv

# Load environment variables from .env
load_dotenv()

logger = logging.getLogger("gemini_service")
logger.setLevel(logging.INFO)


class GeminiService:
    """Isolated service for all Gemini LLM interactions."""

    def __init__(self, api_key: Optional[str] = None, model: Optional[str] = None):
        self.api_key = api_key or os.getenv("GEMINI_API_KEY", "").strip()
        self.model_name = model or os.getenv("GEMINI_MODEL", "gemini-flash-lite-latest").strip()
        self.client = None
        self._init_client()

    def _init_client(self):
        """Initializes the google-genai Client if an API key is available."""
        if not self.api_key or self.api_key == "your_api_key_here":
            logger.warning("GEMINI_API_KEY not configured or is placeholder. LLM calls will fail or use deterministic fallback.")
            self.client = None
            return

        try:
            from google import genai
            self.client = genai.Client(api_key=self.api_key)
            logger.info("Gemini client successfully initialized.")
        except Exception as e:
            logger.error(f"Failed to initialize google.genai Client: {e}")
            self.client = None

    def is_available(self) -> bool:
        """Checks if Gemini API client is configured."""
        return self.client is not None and bool(self.api_key) and self.api_key != "your_api_key_here"

    def generate(
        self,
        prompt: str,
        structured_schema: Optional[Type[BaseModel]] = None,
        system_instruction: Optional[str] = None,
        temperature: float = 0.2,
    ) -> Union[str, BaseModel, dict]:
        """
        Executes a prompt against Gemini.
        If structured_schema is provided, guarantees a validated Pydantic model response.
        If API key is missing or fails, raises or falls back cleanly.
        """
        if not self.is_available():
            raise RuntimeError(
                "Gemini API key is not configured. Please set GEMINI_API_KEY in your .env file or environment."
            )

        try:
            full_prompt = prompt
            if structured_schema is not None:
                schema_json = json.dumps(structured_schema.model_json_schema(), indent=2)
                full_prompt = (
                    f"{prompt}\n\n"
                    f"CRITICAL: Return ONLY valid JSON matching this JSON Schema. Do NOT add markdown blocks or commentary:\n"
                    f"{schema_json}"
                )

            contents = full_prompt
            if system_instruction:
                contents = f"System: {system_instruction}\n\nUser: {full_prompt}"

            # Try primary model, then fallbacks if 429/error
            models_to_try = [self.model_name]
            for fallback in ["gemini-flash-lite-latest", "gemini-3.1-flash-lite", "gemini-3.5-flash-lite", "gemini-flash-latest", "gemma-4-26b-a4b-it"]:
                if fallback not in models_to_try:
                    models_to_try.append(fallback)

            last_exc = None
            response = None
            for model_candidate in models_to_try:
                try:
                    response = self.client.models.generate_content(
                        model=model_candidate,
                        contents=contents,
                    )
                    if response and response.text:
                        break
                except Exception as exc:
                    logger.warning(f"Gemini call to {model_candidate} failed: {exc}. Trying fallback...")
                    last_exc = exc

            if not response or not response.text:
                raise last_exc or RuntimeError("All Gemini candidate models failed to return content.")

            text_output = response.text or ""

            if structured_schema is not None:
                return self._parse_structured_output(text_output, structured_schema)

            return text_output

        except Exception as exc:
            logger.error(f"Gemini API generation error: {exc}")
            raise RuntimeError(f"Gemini API error: {str(exc)}") from exc

    def _parse_structured_output(self, raw_text: str, schema: Type[BaseModel]) -> BaseModel:
        """Extracts JSON substring and validates with the requested Pydantic schema."""
        cleaned = raw_text.strip()
        # Remove markdown triple backtick fences if present
        if cleaned.startswith("```"):
            cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned)
            cleaned = re.sub(r"\s*```$", "", cleaned)
            cleaned = cleaned.strip()

        # If still not bare JSON, find first { and last }
        if not (cleaned.startswith("{") and cleaned.endswith("}")):
            match = re.search(r"(\{.*\})", cleaned, re.DOTALL)
            if match:
                cleaned = match.group(1)

        try:
            data = json.loads(cleaned)
            return schema.model_validate(data)
        except Exception as e:
            logger.warning(f"Direct JSON parsing failed ({e}). Raw text: {raw_text[:200]}")
            # Try lenient parsing
            raise ValueError(f"Failed to parse structured output from LLM: {e}. Output was: {raw_text[:300]}")


# Global singleton instance
_gemini_service_instance: Optional[GeminiService] = None


def get_gemini_service() -> GeminiService:
    global _gemini_service_instance
    if _gemini_service_instance is None:
        _gemini_service_instance = GeminiService()
    return _gemini_service_instance


def reload_gemini_service(api_key: Optional[str] = None) -> GeminiService:
    """Reloads or overrides the Gemini service (e.g., when key is updated in UI)."""
    global _gemini_service_instance
    _gemini_service_instance = GeminiService(api_key=api_key)
    return _gemini_service_instance
