"""
Planner Agent.
Decomposes complex user inquiries into structured, verifiable subtasks.
Identifies required tools, needed evidence, and explicit verification requirements.
STRICT RULE: The planner agent must NEVER directly produce the final answer.
"""

import os
import logging
from typing import Optional
from backend.models.schemas import PlannerOutput
from backend.services.gemini import get_gemini_service

logger = logging.getLogger("planner_agent")

PROMPT_TEMPLATE_PATH = os.path.join(os.path.dirname(__file__), "..", "..", "prompts", "planner.txt")


def load_prompt_template() -> str:
    try:
        with open(PROMPT_TEMPLATE_PATH, "r", encoding="utf-8") as f:
            return f.read()
    except Exception as e:
        logger.warning(f"Failed to read prompt file {PROMPT_TEMPLATE_PATH}: {e}")
        return "Decompose the user task into task_type, subtasks, required_tools, required_evidence, verification_requirements."


class PlannerAgent:
    """Agent responsible for planning and decomposition."""

    def __init__(self, gemini_service=None):
        self.gemini = gemini_service or get_gemini_service()
        self.prompt_template = load_prompt_template()

    def plan(
        self,
        task: str,
        context_text: Optional[str] = None,
        document_ids: Optional[List[str]] = None,
    ) -> PlannerOutput:
        """
        Creates a structured plan for the given task.
        Uses Gemini with PlannerOutput schema or deterministic analysis fallback.
        Dynamically extracts structured dataset task specifications when operating on tabular data.
        """
        logger.info(f"Planning task: {task[:80]}...")

        # Dynamically check for tabular dataset analysis
        from backend.analytics.dataset_engine import resolve_dataset_task
        dataset_spec = resolve_dataset_task(
            task=task,
            document_ids=document_ids,
            gemini_service=self.gemini,
        )

        # Check for self-contained task classification
        from backend.verification.general_reasoning import is_self_contained_task
        is_self = is_self_contained_task(task, context_text, document_ids)

        if self.gemini.is_available():
            prompt = (
                f"{self.prompt_template}\n\n"
                f"TASK TO PLAN:\n{task}\n\n"
                f"AVAILABLE CONTEXT PREVIEW:\n{context_text[:500] if context_text else 'None'}\n\n"
                f"REMINDER: Do NOT solve the problem or calculate the answer. Only produce the plan."
            )
            try:
                result = self.gemini.generate(
                    prompt=prompt,
                    structured_schema=PlannerOutput,
                    temperature=0.1,
                )
                if isinstance(result, PlannerOutput):
                    if dataset_spec and not result.dataset_task:
                        result.dataset_task = dataset_spec
                    if is_self:
                        result.is_self_contained = True
                        result.requires_external_evidence = False
                        result.task_type = "Self-Contained Deterministic Calculation"
                    return result
            except Exception as e:
                logger.warning(f"LLM planning failed ({e}). Proceeding to rule-based fallback planner.")

        # Fallback / deterministic decomposition
        return self._deterministic_plan(task, context_text, dataset_spec=dataset_spec)

    def _deterministic_plan(
        self,
        task: str,
        context_text: Optional[str] = None,
        dataset_spec: Optional[Any] = None,
    ) -> PlannerOutput:
        """Rule-based planner to ensure 100% reliability even if LLM is unavailable."""
        task_lower = task.lower()
        from backend.verification.general_reasoning import is_self_contained_task
        is_self = is_self_contained_task(task, context_text, [dataset_spec.target_dataset] if dataset_spec else None)

        if is_self:
            task_type = "Self-Contained Deterministic Calculation"
            subtasks = [
                "Extract mathematical operands and operation directly from user question",
                "Execute deterministic calculation in isolated Python sandbox",
                "Independently cross-verify arithmetic calculations and logic",
                "Validate factual claim boundaries (zero external claims)",
                "Synthesize verified analytical conclusion",
            ]
            required_tools = ["Python Sandbox / Coder", "Independent Calculator", "Boundary Verifier"]
            required_evidence = ["User-provided numerical operands in question"]
            verification_requirements = [
                "Information sufficiency check",
                "Planner operation match check",
                "Deterministic arithmetic verification",
                "Sandbox and recomputation consistency check",
                "Factual claim boundary check",
            ]
            return PlannerOutput(
                task_type=task_type,
                subtasks=subtasks,
                required_tools=required_tools,
                required_evidence=required_evidence,
                verification_requirements=verification_requirements,
                is_self_contained=True,
                requires_external_evidence=False,
            )

        if dataset_spec:
            task_type = "DATASET ANALYSIS / AGGREGATION"
            filter_str = "; ".join(f"{f.column} {f.operator} {f.value}" for f in dataset_spec.filters) if dataset_spec.filters else "unfiltered"
            subtasks = [
                f"Identify target dataset '{dataset_spec.target_dataset}' and target column '{dataset_spec.target_column}'",
                f"Apply dataset filters and constraints ({filter_str})",
                f"Execute deterministic {dataset_spec.operation} operation ({dataset_spec.aggregation}) in Python sandbox",
                f"Independently cross-verify arithmetic calculations and row counts",
                f"Synthesize verified dataset findings with provenance metadata",
            ]
            required_tools = ["RAG Retrieval / Dataset Loader", "Python REPL / Coder", "Independent Calculator"]
            required_evidence = [f"Filtered {dataset_spec.target_dataset} records", f"Target column '{dataset_spec.target_column}'"]
            verification_requirements = [
                "Dataset isolation verification",
                "Column schema existence verification",
                "Filter operator and value validity check",
                "Structured task operation match",
                "Arithmetic calculation verification",
                "Dataset factual grounding check",
            ]
            return PlannerOutput(
                task_type=task_type,
                subtasks=subtasks,
                required_tools=required_tools,
                required_evidence=required_evidence,
                verification_requirements=verification_requirements,
                dataset_task=dataset_spec,
            )

        if any(w in task_lower for w in ["dataset", "dataset analysis", "aggregation", "dataframe"]):
            task_type = "DATASET ANALYSIS / AGGREGATION"
            subtasks = [
                "Identify target dataset file and column constraints",
                "Filter dataset rows according to specified condition",
                "Extract numerical target column values",
                "Compute aggregated statistical metrics in Python sandbox",
                "Independently cross-verify arithmetic calculations and row counts",
                "Synthesize verified dataset findings and report provenance",
            ]
            required_tools = ["RAG Retrieval / Dataset Loader", "Python REPL / Coder", "Independent Calculator"]
            required_evidence = ["Filtered dataset column values", "Dataset source filename"]
            verification_requirements = [
                "Row filtering and condition verification",
                "Arithmetic calculation verification",
                "Dataset citation verification",
            ]
        elif any(w in task_lower for w in ["growth", "calculate", "percentage", "%", "revenue", "sum", "average", "ratio"]) or any(sym in task for sym in ["+", "-", "*", "/", "×", "÷", "^"]):
            task_type = "Financial & Quantitative Analysis"
            subtasks = [
                "Extract baseline and target metrics from retrieved source evidence",
                "Formulate exact mathematical formula for calculation",
                "Execute Python calculation sandboxed to ensure numerical precision",
                "Verify calculations independently using deterministic arithmetic checks",
                "Verify all quantitative inputs against cited document pages",
                "Synthesize verified findings and document limitations",
            ]
            required_tools = ["RAG Retrieval", "Python REPL / Coder", "Independent Calculator", "Contradiction Detector"]
            required_evidence = ["Baseline financial metrics", "Target period financial metrics", "Reporting document citations"]
            verification_requirements = [
                "Deterministic arithmetic verification of formula",
                "Source citation verification for all numerical values",
                "Contradiction check across reporting documents",
            ]
        elif any(w in task_lower for w in ["code", "run", "execute", "python", "script"]):
            task_type = "Code Generation & Execution"
            subtasks = [
                "Analyze code specifications and requirements",
                "Inspect code for safety and sandbox compliance",
                "Execute code within restricted environment",
                "Verify output against expected behavior",
                "Summarize verified output",
            ]
            required_tools = ["Python Sandbox", "Safety Inspector", "Output Verifier"]
            required_evidence = ["Target function specifications"]
            verification_requirements = ["Zero dangerous syscalls", "Syntax validity", "Expected output match"]
        else:
            task_type = "Fact-Checking & Evidence Retrieval"
            subtasks = [
                "Retrieve grounded excerpts from knowledge base",
                "Check for factual support and source consistency",
                "Detect potential contradictions or unsupported claims",
                "Synthesize verified factual summary",
            ]
            required_tools = ["RAG Retrieval", "Factual Verifier", "Critic Agent"]
            required_evidence = ["Grounded source citations"]
            verification_requirements = ["Evidence confidence > 0.8", "Source page citation", "Absence of contradictions"]

        return PlannerOutput(
            task_type=task_type,
            subtasks=subtasks,
            required_tools=required_tools,
            required_evidence=required_evidence,
            verification_requirements=verification_requirements,
        )
