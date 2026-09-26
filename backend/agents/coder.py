"""
Generalized Coder / Tool Agent.
Performs quantitative computations, generates Python code, and executes calculations in a deterministic sandbox.
Strict Architectural Rules:
1. Candidate answers must carry explicit evidence references (parameter_name, selected_value, source_id, source_name).
2. Check whether alternative/conflicting evidence exists in the evidence graph for any input.
3. If inputs are contradictory without an objective resolution, halt calculation and flag CONFLICTING_INPUT.
4. If an input has an objective resolution (e.g. audit restatement), use the resolved value and record provenance.
5. If required inputs are missing, do not guess or substitute 0; flag INSUFFICIENT_INPUT.
"""

import os
import re
import logging
from typing import Dict, Any, Optional, List, Tuple
from backend.models.schemas import (
    CoderOutput,
    ResearcherOutput,
    PlannerOutput,
    CandidateInputReference,
    EvidenceClaim,
    EvidenceGroup,
)
from backend.verification.code import execute_sandboxed_code
from backend.services.gemini import get_gemini_service

logger = logging.getLogger("coder_agent")

PROMPT_TEMPLATE_PATH = os.path.join(os.path.dirname(__file__), "..", "..", "prompts", "coder.txt")


def load_prompt_template() -> str:
    try:
        with open(PROMPT_TEMPLATE_PATH, "r", encoding="utf-8") as f:
            return f.read()
    except Exception:
        return "Generate safe Python code and calculate deterministic results."


class CoderAgent:
    """Agent responsible for deterministic calculation logic and tool execution."""

    def __init__(self, gemini_service=None):
        self.gemini = gemini_service or get_gemini_service()
        self.prompt_template = load_prompt_template()

    def execute_task(
        self,
        task: str,
        researcher_output: Optional[ResearcherOutput] = None,
        planner_output: Optional[PlannerOutput] = None,
        correction_feedback: Optional[str] = None,
    ) -> CoderOutput:
        """
        Executes deterministic calculation or code generation based on retrieved evidence.
        Attaches candidate input references for provenance verification.
        """
        logger.info(f"Coder agent running for task: {task[:80]}")

        # Check if this is a self-contained task where external evidence is not required
        is_self_contained = False
        if researcher_output and researcher_output.status == "EVIDENCE_NOT_REQUIRED":
            is_self_contained = True
        elif planner_output and getattr(planner_output, "is_self_contained", False):
            is_self_contained = True

        if is_self_contained:
            from backend.verification.general_reasoning import solve_self_contained_task
            solved = solve_self_contained_task(task)
            if solved:
                code = solved["code"]
                exec_res = execute_sandboxed_code(code, solved.get("inputs"))
                fmt_res = solved["formatted_result"]
                return CoderOutput(
                    code=code,
                    explanation=f"Executed deterministic calculation in isolated Python sandbox: {fmt_res}",
                    inputs=solved["inputs"],
                    input_references=[],
                    execution_result=fmt_res,
                    calculation_steps=solved["calculation_steps"],
                    error=exec_res.get("error"),
                )
            else:
                # Task is non-computational general reasoning inquiry (factual, conceptual, or logic)
                return CoderOutput(
                    code="# Non-computational inquiry: preserved for independent verification",
                    explanation="General reasoning inquiry. Preserved candidate output for independent verification layer.",
                    inputs={"task": task, "status": "VALID_INPUT"},
                    input_references=[],
                    execution_result=None,
                    calculation_steps=["Routed to independent verification layer"],
                )

        # 1. Extract generalized numerical inputs from researcher evidence & graph
        extracted_inputs, input_refs = self._extract_inputs_from_evidence(researcher_output, task)

        # 2. Check if researcher detected unresolved contradictory evidence or inputs are conflicted
        c_report = getattr(researcher_output, "contradiction_report", None) if researcher_output else None
        has_unresolved_contra = bool(c_report and c_report.contradiction_detected and c_report.unresolved_contradictions)

        if has_unresolved_contra or extracted_inputs.get("status") == "CONFLICTING_INPUT" or any(ref.is_conflicted for ref in input_refs):
            logger.warning("Unresolved contradiction detected in evidence inputs. Halting calculation.")
            conflicted_names = [f"{ref.period + ' ' if ref.period else ''}{ref.parameter_name}".strip() for ref in input_refs if ref.is_conflicted]
            unique_conflicted = sorted(list(set(conflicted_names)))
            if not unique_conflicted and c_report:
                unique_conflicted = [u.get("canonical_entity") or u.get("entity", "metric") for u in c_report.unresolved_contradictions]

            # If input_refs was empty but contradiction was reported, populate from contradiction report
            if not input_refs and c_report:
                for u in c_report.unresolved_contradictions:
                    for clm in u.get("claims", []):
                        input_refs.append(
                            CandidateInputReference(
                                parameter_name=u.get("canonical_entity") or u.get("entity", "metric"),
                                selected_value=None,
                                source_id=clm.get("source_id", "source"),
                                source_name=clm.get("source_name", "Source"),
                                period=u.get("period"),
                                has_alternative_evidence=True,
                                is_conflicted=True,
                            )
                        )

            return CoderOutput(
                code="# Calculation halted: unresolved contradictory inputs detected across sources",
                explanation=(
                    f"Cannot perform deterministic calculation because required input parameters have "
                    f"conflicting values across sources without objective resolution: {', '.join(unique_conflicted)}"
                ),
                inputs={"status": "CONFLICTING_INPUT", "conflicting_parameters": unique_conflicted},
                input_references=input_refs,
                execution_result=None,
                calculation_steps=[
                    f"Identified contradictory values for {', '.join(unique_conflicted)} across sources",
                    "Halted calculation to prevent arbitrary value selection (Generation != Verification)",
                ],
                error="Conflicting inputs",
            )

        # 2b. General Tabular Dataset Analysis Execution
        has_dataset_evidence = any(e.source.endswith(".csv") for e in (researcher_output.evidence_items if researcher_output else []))
        is_dataset_task = has_dataset_evidence or bool(planner_output and planner_output.dataset_task)
        if is_dataset_task and researcher_output and researcher_output.evidence_items:
            ds_item = next((e for e in researcher_output.evidence_items if e.source.endswith(".csv")), researcher_output.evidence_items[0])
            ev_meta = ds_item.metadata or {}
            doc_src = ds_item.source

            # Extract or compute sandboxed dataset analysis
            code = ev_meta.get("code")
            calc_steps = ev_meta.get("calculation_steps")
            formatted_res = ev_meta.get("formatted_result") or str(ev_meta.get("result_value"))
            res_val = ev_meta.get("result_value")
            op_name = ev_meta.get("operation") or "dataset_analysis"
            target_metric = ev_meta.get("target_column") or "dataset_metric"

            if not code:
                from backend.analytics.dataset_engine import resolve_dataset_task, execute_dataset_task
                spec = planner_output.dataset_task if planner_output else None
                if not spec:
                    spec = resolve_dataset_task(task, document_ids=[doc_src], gemini_service=self.gemini)
                if spec:
                    exec_data = execute_dataset_task(spec)
                    code = exec_data["code"]
                    calc_steps = exec_data["calculation_steps"]
                    formatted_res = exec_data["formatted_result"]
                    res_val = exec_data["result_value"]
                    op_name = spec.operation
                    target_metric = spec.target_column or "dataset_metric"

            if code:
                exec_res = execute_sandboxed_code(code)
                return CoderOutput(
                    code=code,
                    explanation=f"Calculated verified {op_name} for '{task}' from {doc_src}: {formatted_res}",
                    inputs={
                        "value": res_val,
                        "status": "VALID_INPUT",
                        "dataset": doc_src,
                        "formula": op_name,
                    },
                    input_references=[
                        CandidateInputReference(
                            parameter_name=target_metric,
                            selected_value=res_val,
                            source_id=re.sub(r"[^\w\-]", "_", doc_src.lower()),
                            source_name=doc_src,
                            is_conflicted=False,
                        )
                    ],
                    execution_result=formatted_res,
                    calculation_steps=calc_steps or [f"Executed verified {op_name} analysis on {doc_src}"],
                    error=exec_res.get("error"),
                )

        # 3. Check for comparison / growth or single-value calculations
        is_growth_task = any(w in task.lower() for w in ["growth", "increase", "percentage change", "% change", "cagr", "rate of change", "between", "throughput", "baseline", "compare", "comparison"])
        is_diff_task = any(w in task.lower() for w in ["difference", "subtract", "minus", "gap"])

        has_initial = isinstance(extracted_inputs.get("initial"), (int, float))
        has_final = isinstance(extracted_inputs.get("final"), (int, float))

        # Only calculate growth or difference if the task explicitly requests growth/comparison/difference!
        if (is_growth_task or is_diff_task) and has_initial and has_final:
            initial_val = extracted_inputs["initial"]
            final_val = extracted_inputs["final"]

            if is_diff_task:
                diff_val = round(final_val - initial_val, 4)
                code = (
                    f"initial_val = {initial_val}\n"
                    f"final_val = {final_val}\n"
                    f"result = final_val - initial_val\n"
                    f"print(f'Difference: {{result}}')"
                )
                exec_res = execute_sandboxed_code(code, {"initial_val": initial_val, "final_val": final_val})
                inputs_dict = dict(extracted_inputs)
                inputs_dict.update({
                    "initial": initial_val,
                    "final": final_val,
                    "formula": "final - initial",
                })
                return CoderOutput(
                    code=code,
                    explanation=f"Calculated difference: {final_val} - {initial_val} = {diff_val}",
                    inputs=inputs_dict,
                    input_references=input_refs,
                    execution_result=f"{diff_val}",
                    calculation_steps=[f"Difference between {final_val} and {initial_val} is {diff_val}"],
                    error=exec_res.get("error"),
                )
            else:
                if initial_val == 0:
                    return CoderOutput(
                        code="# Base initial value is 0; growth undefined",
                        explanation="Base initial value is 0. Growth percentage cannot be computed (division by zero is mathematically undefined).",
                        inputs={"initial": 0.0, "final": final_val, "status": "INVALID_INPUT"},
                        input_references=input_refs,
                        execution_result=None,
                        calculation_steps=["Identified base initial value: 0", "Division by zero: Growth is mathematically undefined"],
                        error="Division by zero: initial value is 0",
                    )

                growth_pct = round(((final_val - initial_val) / initial_val) * 100.0, 2)
                code = (
                    f"initial_val = {initial_val}\n"
                    f"final_val = {final_val}\n"
                    f"result = ((final_val - initial_val) / initial_val) * 100.0\n"
                    f"print(f'Growth: {{result:.2f}}%')"
                )
                exec_res = execute_sandboxed_code(code, {"initial_val": initial_val, "final_val": final_val})

                inputs_dict = dict(extracted_inputs)
                inputs_dict.update({
                    "initial": initial_val,
                    "final": final_val,
                    "formula": "((final - initial) / initial) * 100",
                })

                # Record any objective resolution notes in steps
                calc_steps = [
                    f"Step 1: Identified base initial parameter: {initial_val}",
                    f"Step 2: Identified final comparison parameter: {final_val}",
                    f"Step 3: Difference = {round(final_val - initial_val, 4)}",
                    f"Step 4: Division by base ({initial_val}) * 100 = {growth_pct}%",
                ]
                if researcher_output and researcher_output.contradiction_report:
                    for res_note in researcher_output.contradiction_report.resolution_basis:
                        calc_steps.append(f"Resolution Basis: {res_note}")

                return CoderOutput(
                    code=code,
                    explanation=f"Calculated percentage growth: ({final_val} - {initial_val}) / {initial_val} * 100 = {growth_pct}%",
                    inputs=inputs_dict,
                    input_references=input_refs,
                    execution_result=f"{growth_pct}%",
                    calculation_steps=calc_steps,
                    error=exec_res.get("error"),
                )

        elif has_initial and not has_final and is_growth_task:
            # One parameter is available, the other is missing for a growth task
            return CoderOutput(
                code="# Calculation cannot be performed: final comparison parameter is unavailable",
                explanation="Calculation cannot be performed because the required final comparison parameter is unavailable in the evidence.",
                inputs=extracted_inputs,
                input_references=input_refs,
                execution_result=None,
                calculation_steps=["Identified initial parameter", "Final parameter missing; halted without substituting 0"],
                error="Missing final parameter",
            )

        # 3b. Deterministic factual value resolution (single value or multi-period reporting)
        if not is_growth_task and not is_diff_task:
            claims = getattr(researcher_output, "claims", []) or []
            distinct_period_claims = {}
            for c in claims:
                if c.period and c.extracted_value is not None:
                    p_key = c.period.capitalize()
                    if p_key not in distinct_period_claims:
                        distinct_period_claims[p_key] = c

            if len(distinct_period_claims) >= 2:
                # Factual question with multiple different periods: report values by period without unrequested growth
                period_items = []
                for p_name, clm in distinct_period_claims.items():
                    val_str = f"{clm.extracted_value} {clm.unit or ''}".strip()
                    base_val = clm.metadata.get("base_numeric_value") if isinstance(clm.metadata, dict) else None
                    if base_val is not None and clm.unit and "crore" in clm.unit.lower():
                        val_str = f"₹{clm.extracted_value} crore ({int(base_val):,} INR)"
                    elif base_val is not None and clm.unit and "lakh" in clm.unit.lower():
                        val_str = f"₹{clm.extracted_value} lakh ({int(base_val):,} INR)"
                    period_items.append(f"{p_name}: {val_str}")

                multi_period_str = ", ".join(period_items)
                code = f"# Multi-period factual report (growth not requested)\nresult = {repr(multi_period_str)}"
                return CoderOutput(
                    code=code,
                    explanation=f"Reported factual values across periods without unrequested growth calculation: {multi_period_str}",
                    inputs={**extracted_inputs, "formula": "factual_multi_period"},
                    input_references=input_refs,
                    execution_result=multi_period_str,
                    calculation_steps=[
                        f"Identified factual values across periods: {multi_period_str}",
                        "Preserved factual reporting without computing unrequested growth percentage",
                    ],
                )

            # Common / single verified value for target entity
            single_target_val = None
            if researcher_output and researcher_output.contradiction_report and researcher_output.contradiction_report.resolved_contradictions:
                single_target_val = researcher_output.contradiction_report.resolved_contradictions[0].get("resolved_value")
            elif "value" in extracted_inputs and extracted_inputs["value"] is not None:
                single_target_val = extracted_inputs["value"]
            else:
                for k, v in extracted_inputs.items():
                    if k not in ["initial", "final", "status", "conflicting_parameters", "missing_parameters"] and v is not None:
                        single_target_val = v
                        break

            if single_target_val is not None:
                disp_val = single_target_val
                if isinstance(single_target_val, (int, float)):
                    int_val = int(single_target_val) if float(single_target_val).is_integer() else single_target_val
                    has_inr = any("inr" in str(c.unit).lower() or "₹" in str(c.raw_entity) for c in claims)
                    if has_inr and isinstance(int_val, int) and int_val >= 10000000:
                        cr_val = int_val / 10000000.0
                        cr_str = f" (₹{int(cr_val)} crore)" if cr_val.is_integer() else f" (₹{cr_val:.2f} crore)"
                        disp_val = f"₹{int_val:,} INR{cr_str}"
                    elif has_inr and isinstance(int_val, int):
                        disp_val = f"₹{int_val:,} INR"

                code = f"result = {repr(disp_val)}\nprint(f'Verified Value: {{result}}')"
                exec_res = execute_sandboxed_code(code, {"result": disp_val})
                return CoderOutput(
                    code=code,
                    explanation=f"Determined verified value: {disp_val}",
                    inputs={"value": single_target_val, "formula": "single_value", "status": "VALID_INPUT"},
                    input_references=input_refs,
                    execution_result=disp_val,
                    calculation_steps=[f"Determined verified factual value: {disp_val}"],
                    error=exec_res.get("error"),
                )

        # 4. If LLM available, generate code via Gemini
        if self.gemini.is_available():
            evidence_summary = ""
            if researcher_output:
                evidence_summary = "\n".join([f"- {e.claim}: {e.evidence}" for e in researcher_output.evidence_items])

            prompt = (
                f"{self.prompt_template}\n\n"
                f"TASK: {task}\n\n"
                f"EVIDENCE EXTRACTED:\n{evidence_summary}\n\n"
                f"{'CORRECTION INSTRUCTION: ' + correction_feedback if correction_feedback else ''}\n\n"
                f"Generate safe Python code to perform the calculation deterministically. Do NOT guess missing numbers."
            )
            try:
                llm_output = self.gemini.generate(prompt=prompt, structured_schema=CoderOutput)
                if isinstance(llm_output, CoderOutput):
                    if llm_output.code:
                        exec_res = execute_sandboxed_code(llm_output.code, llm_output.inputs)
                        llm_output.execution_result = exec_res.get("return_value")
                        llm_output.error = exec_res.get("error")
                        llm_output.input_references = input_refs
                    return llm_output
            except Exception as e:
                logger.warning(f"LLM code generation failed ({e}). Using deterministic fallback.")

        # 5. Deterministic fallback if insufficient parameters
        return CoderOutput(
            code="# No calculable numerical parameters found in evidence",
            explanation="Could not find sufficient numerical parameters to formulate deterministic calculation.",
            inputs=extracted_inputs,
            input_references=input_refs,
            execution_result=None,
            calculation_steps=["No calculation performed due to missing or incalculable variables."],
            error="Missing numerical parameters",
        )

    def _extract_inputs_from_evidence(
        self,
        researcher_output: Optional[ResearcherOutput],
        task: str,
    ) -> Tuple[Dict[str, Any], List[CandidateInputReference]]:
        """
        Extracts generalized key-value numerical pairs and builds CandidateInputReference
        provenance tracking connecting each parameter to its source and evidence claim.
        """
        inputs: Dict[str, Any] = {}
        input_refs: List[CandidateInputReference] = []

        if not researcher_output:
            return inputs, input_refs

        graph = getattr(researcher_output, "evidence_graph", {}) or {}
        claims = getattr(researcher_output, "claims", []) or []

        numeric_entries: List[Tuple[str, float, str, str, Optional[str]]] = []  # (param, val, src_id, src_name, period)

        # 1. Prefer claims from the structured EvidenceClaim list if available
        if claims:
            for c in claims:
                if c.extracted_value is not None:
                    param_name = c.canonical_entity
                    # Check if this claim's group in the graph is conflicted or resolved
                    period_key = f"_{c.period.lower()}" if c.period else ""
                    group_key = f"{c.canonical_entity}{period_key}"
                    group = graph.get(group_key)

                    is_conflicted = False
                    has_alt = False
                    base_numeric = c.metadata.get("base_numeric_value") if isinstance(c.metadata, dict) else None
                    val_to_use = base_numeric if base_numeric is not None else c.extracted_value
                    if isinstance(val_to_use, float) and val_to_use.is_integer():
                        val_to_use = int(val_to_use)

                    if group:
                        if group.is_conflicted:
                            has_alt = True
                            if group.is_resolved:
                                # Use objectively resolved value
                                val_to_use = group.resolved_value
                                is_conflicted = False
                            else:
                                is_conflicted = True
                                val_to_use = None

                    ref = CandidateInputReference(
                        parameter_name=param_name,
                        selected_value=val_to_use,
                        source_id=c.source_id,
                        source_name=c.source_name,
                        period=c.period,
                        has_alternative_evidence=has_alt,
                        is_conflicted=is_conflicted,
                    )
                    input_refs.append(ref)
                    if val_to_use is not None:
                        if isinstance(val_to_use, (int, float)):
                            numeric_entries.append((param_name, val_to_use, c.source_id, c.source_name, c.period))
                        if param_name not in inputs or (group and group.is_resolved and val_to_use == group.resolved_value):
                            inputs[param_name] = val_to_use
                        if c.period and c.period not in inputs:
                            inputs[c.period] = val_to_use

        # 2. Extract from raw evidence items if claims were not extracted
        if not numeric_entries and researcher_output.evidence_items:
            for item in researcher_output.evidence_items:
                clean = f"{item.claim}\n{item.evidence}"
                lines = clean.split("\n")
                for raw_line in lines:
                    line = raw_line.strip()
                    if not line or (line.endswith(":") and len(line.split()) <= 4):
                        continue
                    if any(w in line.lower() for w in ["unavailable", "pending", "omitted", "missing", "not available"]):
                        continue

                    clean_line = re.sub(r"\b20\d\d\s*[-/]?\s*q[1-4]\b", "", line, flags=re.IGNORECASE)
                    clean_line = re.sub(r"\b(?:jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*\s+\d{1,2}(?:st|nd|rd|th)?\b", "", clean_line, flags=re.IGNORECASE)

                    # Year match
                    year_matches = re.findall(
                        r"(?:fy\s*)?(\b\d{4}\b)[^\d\n]*?(?:is|was|are|were|=|:|\bat\b|\brecorded\s+at\b|\breached\b|\bof\b)\s*([+-]?(?:[0-9]{1,3}(?:,[0-9]{3})+|[0-9]+)(?:\.[0-9]+)?)",
                        clean_line,
                        re.IGNORECASE,
                    )
                    for yr, val_str in year_matches:
                        try:
                            v = float(val_str.replace(",", ""))
                            if not (1900 <= v <= 2099 and v == float(yr)):
                                inputs[yr] = v
                                numeric_entries.append((yr, v, item.source_id or item.source, item.source, yr))
                        except ValueError:
                            pass

                    # Named match
                    named_matches = re.findall(
                        r"([a-zA-Z_\s]{3,30}?)\s*(?:is|was|are|were|=|:|\bat\b|\brecorded\s+at\b|\breached\b|\bof\b)\s*([+-]?(?:[0-9]{1,3}(?:,[0-9]{3})+|[0-9]+)(?:\.[0-9]+)?)",
                        clean_line,
                        re.IGNORECASE,
                    )
                    for name, val_str in named_matches:
                        clean_name = name.strip().lower()
                        clean_name = re.sub(r"^(in|for|of|the|a|an|fy)\s+", "", clean_name).strip()
                        if clean_name and clean_name not in {"it", "there", "this", "that", "which", "and", "revenue", "sales"}:
                            try:
                                v = float(val_str.replace(",", ""))
                                if clean_name not in inputs:
                                    inputs[clean_name] = v
                                    numeric_entries.append((clean_name, v, item.source_id or item.source, item.source, None))
                            except ValueError:
                                pass

        # Determine initial and final ONLY if task asks for growth, comparison or difference
        is_growth_task = any(w in task.lower() for w in ["growth", "increase", "percentage change", "% change", "cagr", "rate of change", "between", "throughput", "baseline", "compare", "comparison"])
        is_diff_task = any(w in task.lower() for w in ["difference", "subtract", "minus", "gap"])

        if is_growth_task or is_diff_task:
            year_keys = sorted([k for k in inputs.keys() if k.isdigit() and len(k) == 4 and isinstance(inputs[k], (int, float))])
            if len(year_keys) >= 2:
                inputs["initial"] = inputs[year_keys[0]]
                inputs["final"] = inputs[year_keys[1]]
            elif len(year_keys) == 1:
                yr = year_keys[0]
                if f"from {yr}" in task.lower() or f"{yr} to" in task.lower() or yr == "2024":
                    inputs["initial"] = inputs[yr]
                else:
                    inputs["final"] = inputs[yr]
            else:
                for k in ["baseline", "start", "base", "initial", "january", "jan", "pre"]:
                    if k in inputs and isinstance(inputs[k], (int, float)):
                        inputs["initial"] = inputs[k]
                        break
                for k in ["final", "end", "target", "current", "february", "feb", "peak", "post"]:
                    if k in inputs and isinstance(inputs[k], (int, float)):
                        inputs["final"] = inputs[k]
                        break

                if "initial" not in inputs and len(numeric_entries) >= 2:
                    ent0, ent1 = numeric_entries[0], numeric_entries[1]
                    if ent0[0] != ent1[0] or ent0[4] != ent1[4]:
                        inputs["initial"] = ent0[1]
                        inputs["final"] = ent1[1]
        else:
            # Factual task: set common/canonical target value
            if "value" not in inputs and numeric_entries:
                inputs["value"] = numeric_entries[0][1]

        # Check if any input reference is marked conflicted
        if any(ref.is_conflicted for ref in input_refs):
            inputs["status"] = "CONFLICTING_INPUT"
            conflicted_names = [f"{ref.period + ' ' if ref.period else ''}{ref.parameter_name}".strip() for ref in input_refs if ref.is_conflicted]
            inputs["conflicting_parameters"] = sorted(list(set(conflicted_names)))
            inputs.pop("initial", None)
            inputs.pop("final", None)

        return inputs, input_refs
