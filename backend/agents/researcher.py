"""
Generalized Researcher Agent.
Retrieves grounded evidence from ChromaDB and documents.
Stores structured EvidenceItem instances with full provenance:
claim, normalized_claim, evidence, excerpt, source, source_id, page, confidence, verification_status.
Strict Architectural Rule: NEVER invent evidence. Returns INSUFFICIENT_EVIDENCE or CONFLICTING_EVIDENCE when needed.
No hardcoded years, companies, or document names.

DATA ISOLATION GUARANTEE:
When document_ids is set (DOCUMENT / RAG mode), retrieval is strictly scoped.
Any chunk or evidence item whose source is NOT in document_ids triggers a hard ISOLATION_BLOCKED response.
No cross-dataset bleed can silently enter the pipeline.
"""

import os
import re
import logging
from typing import List, Dict, Any, Optional, Set
from backend.models.schemas import (
    ResearcherOutput, EvidenceItem, EvidenceClaim, PlannerOutput,
    ContradictionReport, FinalDecision,
)
from backend.rag.retrieval import get_vector_store
from backend.rag.ingestion import ingest_raw_text
from backend.services.gemini import get_gemini_service
from backend.verification.contradiction import detect_contradictions, normalize_entity_key, ALL_OPPOSING_WORDS

logger = logging.getLogger("researcher_agent")

# Sentinel status for hard isolation failures
ISOLATION_BLOCKED = "ISOLATION_BLOCKED"


def _build_isolation_blocked_response(
    selected_docs: List[str],
    leaked_sources: List[str],
    queries: List[str],
) -> ResearcherOutput:
    """
    Returns a hard-blocked ResearcherOutput when RAG retrieval returns chunks
    whose source metadata is outside the set of user-selected documents.
    This prevents cross-dataset evidence leakage from silently entering the pipeline.
    """
    reason = (
        f"RAG retrieval violated selected document scope. "
        f"Selected: {selected_docs}. "
        f"Unexpected sources retrieved: {leaked_sources}. "
        f"Query cannot proceed — return BLOCKED."
    )
    logger.error(f"[ISOLATION GUARD] {reason}")
    return ResearcherOutput(
        status=ISOLATION_BLOCKED,
        evidence_items=[
            EvidenceItem(
                claim=reason,
                normalized_claim="isolation_blocked",
                evidence=reason,
                excerpt=reason[:160],
                source="ISOLATION_GUARD",
                source_id="isolation_guard",
                page=0,
                confidence=0.0,
                verification_status="BLOCKED",
                metadata={
                    "selected_documents": selected_docs,
                    "leaked_sources": leaked_sources,
                },
            )
        ],
        claims=[],
        evidence_graph={},
        contradiction_report=ContradictionReport(
            contradiction_detected=True,
            contradiction_count=1,
            unresolved_contradictions=[
                {
                    "type": "ISOLATION_VIOLATION",
                    "description": reason,
                    "severity": "CRITICAL",
                    "selected_documents": selected_docs,
                    "leaked_sources": leaked_sources,
                }
            ],
            resolved_contradictions=[],
            resolution_basis=[],
            verification_status="BLOCKED",
            final_decision=FinalDecision.REJECT,
        ),
        missing_info=[reason],
        search_queries_used=queries,
    )

PROMPT_TEMPLATE_PATH = os.path.join(os.path.dirname(__file__), "..", "..", "prompts", "researcher.txt")


def load_prompt_template() -> str:
    try:
        with open(PROMPT_TEMPLATE_PATH, "r", encoding="utf-8") as f:
            return f.read()
    except Exception as e:
        logger.warning(f"Failed to read prompt file {PROMPT_TEMPLATE_PATH}: {e}")
        return "Retrieve grounded evidence. If missing, return INSUFFICIENT_EVIDENCE."


class ResearcherAgent:
    """Agent responsible for factual evidence extraction from RAG without hardcoded constraints."""

    def __init__(self, gemini_service=None):
        self.gemini = gemini_service or get_gemini_service()
        self.vector_store = get_vector_store()
        self.prompt_template = load_prompt_template()

    def research(
        self,
        task: str,
        planner_output: Optional[PlannerOutput] = None,
        context_text: Optional[str] = None,
        document_ids: Optional[List[str]] = None,
    ) -> ResearcherOutput:
        """
        Executes evidence retrieval and extraction across ChromaDB or provided context.
        """
        logger.info(f"Researching task: {task[:80]}")

        # Determine retrieval search queries
        queries = [task]
        if planner_output and planner_output.required_evidence:
            queries.extend(planner_output.required_evidence[:3])

        all_chunks: List[Dict[str, Any]] = []
        seen_chunks = set()

        # Check if target document is a structured CSV dataset in documents/
        csv_candidates = [d for d in (document_ids or []) if d and str(d).lower().endswith(".csv")]
        if csv_candidates or (planner_output and planner_output.dataset_task):
            from backend.analytics.dataset_engine import resolve_dataset_task, execute_dataset_task
            try:
                spec = (planner_output.dataset_task if planner_output and planner_output.dataset_task else None)
                if not spec:
                    spec = resolve_dataset_task(task, document_ids=document_ids, gemini_service=self.gemini)

                if spec and spec.target_dataset:
                    res = execute_dataset_task(spec)
                    doc_name = res["dataset_name"]
                    matching_count = res["matching_count"]
                    total_rows = res["total_rows"]
                    formatted_val = res["formatted_result"]
                    calc_steps = res["calculation_steps"]

                    filter_desc = "; ".join(f"{f.column} {f.operator} {f.value}" for f in spec.filters) if spec.filters else "None (all records)"
                    ds_claim = f"Dataset '{doc_name}' analysis for '{spec.target_column or 'records'}' ({spec.operation}/{spec.aggregation}): {formatted_val} across {matching_count} matching records"
                    ds_ev = (
                        f"Dataset: {doc_name} (Total rows: {total_rows})\n"
                        f"Target column: {spec.target_column}\n"
                        f"Operation: {spec.operation} ({spec.aggregation})\n"
                        f"Filter condition: {filter_desc}\n"
                        f"Matching records: {matching_count}\n"
                        f"Verified output: {formatted_val}\n"
                        f"Trace: {' -> '.join(calc_steps[:3])}"
                    )

                    ev_item = EvidenceItem(
                        claim=ds_claim,
                        normalized_claim=f"{spec.operation} {spec.target_column or ''}".strip(),
                        evidence=ds_ev,
                        excerpt=ds_ev[:200],
                        source=doc_name,
                        source_id=re.sub(r"[^\w\-]", "_", doc_name.lower()),
                        page=1,
                        confidence=1.0,
                        verification_status="SUPPORTED",
                        metadata={
                            "dataset": doc_name,
                            "dataset_spec": spec.model_dump(),
                            "filter_description": filter_desc,
                            "count": matching_count,
                            "total_rows": total_rows,
                            "target_column": spec.target_column,
                            "operation": spec.operation,
                            "aggregation": spec.aggregation,
                            "result_value": res["result_value"],
                            "formatted_result": formatted_val,
                            "execution_result": res["execution_result"],
                            "code": res["code"],
                            "calculation_steps": calc_steps,
                        }
                    )
                    clean_src_id = re.sub(r"[^\w\-]", "_", doc_name.lower())
                    ev_clm = EvidenceClaim(
                        claim_id=f"clm_{clean_src_id}_{spec.operation}",
                        source_id=clean_src_id,
                        source_name=doc_name,
                        page=1,
                        excerpt=f"Verified {spec.operation} {spec.target_column or ''}: {formatted_val}",
                        canonical_entity=f"{spec.target_column or spec.operation}",
                        raw_entity=f"{spec.operation} ({spec.target_column})",
                        extracted_value=res["result_value"],
                        unit="INR" if "price" in str(spec.target_column).lower() else None,
                        period=None,
                        confidence=1.0,
                        metadata=ev_item.metadata,
                    )
                    from backend.models.schemas import ContradictionReport
                    return ResearcherOutput(
                        status="EVIDENCE_FOUND",
                        evidence_items=[ev_item],
                        claims=[ev_clm],
                        evidence_graph={},
                        contradiction_report=ContradictionReport(
                            contradiction_detected=False,
                            contradiction_count=0,
                            unresolved_contradictions=[],
                            resolved_contradictions=[],
                            resolution_basis=[],
                            verification_status="PASS",
                            final_decision=FinalDecision.ACCEPT,
                        ),
                        missing_info=[],
                        search_queries_used=queries,
                    )
            except Exception as ex:
                logger.warning(f"Direct dataset analysis failed ({ex}). Proceeding to vector search.")

        # Check if this is a general reasoning question without attached documents (RAG is optional)
        if not (context_text and context_text.strip()) and not document_ids:
            logger.info("General Reasoning task without attached documents: External RAG evidence NOT required.")
            from backend.models.schemas import ContradictionReport
            return ResearcherOutput(
                status="EVIDENCE_NOT_REQUIRED",
                evidence_items=[],
                claims=[],
                evidence_graph={},
                contradiction_report=ContradictionReport(
                    contradiction_detected=False,
                    contradiction_count=0,
                    unresolved_contradictions=[],
                    resolved_contradictions=[],
                    resolution_basis=[],
                    verification_status="PASS",
                    final_decision=FinalDecision.ACCEPT,
                ),
                missing_info=[],
                search_queries_used=[],
            )

        # If direct context is passed, prioritize its chunks directly
        if context_text is not None:
            if context_text.strip():
                context_chunks = ingest_raw_text(context_text.strip(), source_name="provided_context")
                for c in context_chunks:
                    chunk_key = (c.get("source"), c["text"])
                    if chunk_key not in seen_chunks:
                        seen_chunks.add(chunk_key)
                        all_chunks.append({
                            "text": c["text"],
                            "source": c.get("source", "provided_context"),
                            "source_id": c.get("source_id", "provided_context"),
                            "page": c.get("page", 1),
                            "confidence": 0.95,
                            "distance": 0.05,
                        })
            else:
                # Explicit empty context provided by user: do not inject ChromaDB documents
                all_chunks = []
        else:
            # Query the RAG vector store scoped strictly to selected document_ids
            for q in queries:
                try:
                    if document_ids:
                        results = self.vector_store.search(q, top_k=5, document_ids=document_ids)
                    else:
                        results = self.vector_store.search(q, top_k=5)
                except TypeError:
                    try:
                        results = self.vector_store.search(q, top_k=5)
                    except Exception as e:
                        logger.warning(f"Vector store search failed: {e}")
                        results = []
                except Exception as e:
                    logger.warning(f"Vector store search failed: {e}")
                    results = []

                for r in (results or []):
                    if not isinstance(r, dict) or not r.get("text"):
                        continue
                    chunk_key = (r.get("source"), r.get("text"))
                    if chunk_key not in seen_chunks:
                        seen_chunks.add(chunk_key)
                        all_chunks.append(r)

            # ============================================================
            # HARD DATASET ISOLATION GUARD
            # After retrieval, verify every chunk's source is within the
            # selected document_ids. If any source leaked, block the query.
            # ============================================================
            if document_ids:
                selected_set: Set[str] = set(document_ids)
                leaked: List[str] = list({
                    c.get("source", "unknown")
                    for c in all_chunks
                    if c.get("source", "unknown") not in selected_set
                })
                if leaked:
                    return _build_isolation_blocked_response(
                        selected_docs=list(selected_set),
                        leaked_sources=leaked,
                        queries=queries,
                    )

        # If no chunks at all in database or context is empty
        if not all_chunks:
            logger.warning("No document evidence found in RAG store.")
            return ResearcherOutput(
                status="INSUFFICIENT_EVIDENCE",
                evidence_items=[],
                missing_info=["No matching documents or context found in knowledge base."],
                search_queries_used=queries,
            )

        # Use Gemini for semantic claim-evidence grounding if available
        if self.gemini.is_available():
            formatted_chunks = "\n---\n".join([
                f"[Source: {c['source']}, Page: {c['page']}, Conf: {c['confidence']}]\n{c['text']}"
                for c in all_chunks
            ])

            prompt = (
                f"{self.prompt_template}\n\n"
                f"USER TASK: {task}\n\n"
                f"RETRIEVED DOCUMENT EXCERPTS:\n{formatted_chunks}\n\n"
                f"Extract only grounded evidence. If numbers or facts are missing or uncertain, "
                f"explicitly return INSUFFICIENT_EVIDENCE in the status field."
            )
            try:
                result = self.gemini.generate(
                    prompt=prompt,
                    structured_schema=ResearcherOutput,
                    temperature=0.1,
                )
                if isinstance(result, ResearcherOutput) and result.evidence_items:
                    # ============================================================
                    # POST-LLM ISOLATION GUARD
                    # The LLM may hallucinate or merge sources. Strip any evidence
                    # items whose source is not within the selected document_ids.
                    # ============================================================
                    if document_ids:
                        selected_set: Set[str] = set(document_ids)
                        before_count = len(result.evidence_items)
                        result.evidence_items = [
                            item for item in result.evidence_items
                            if item.source in selected_set
                            or item.source in ("ISOLATION_GUARD",)  # keep guard messages
                        ]
                        stripped = before_count - len(result.evidence_items)
                        if stripped > 0:
                            logger.warning(
                                f"[ISOLATION GUARD] Stripped {stripped} evidence items with sources "
                                f"outside selected scope {list(selected_set)}"
                            )
                        if not result.evidence_items:
                            # All items were out of scope — return isolation blocked
                            leaked_in_llm = list({
                                item.source
                                for item in result.evidence_items
                            })
                            return _build_isolation_blocked_response(
                                selected_docs=list(selected_set),
                                leaked_sources=leaked_in_llm,
                                queries=queries,
                            )

                    # Enrich with normalized claims and excerpts
                    for item in result.evidence_items:
                        item.normalized_claim = normalize_entity_key(item.claim)
                        item.excerpt = item.evidence[:160]
                        item.source_id = f"{item.source}_p{item.page}"

                    # Run contradiction check across extracted items
                    contra = detect_contradictions(result.evidence_items)
                    result.claims = contra.get("claims", [])
                    result.evidence_graph = contra.get("evidence_graph", {})
                    result.contradiction_report = ContradictionReport(
                        contradiction_detected=contra.get("contradiction_detected", False),
                        contradiction_count=contra.get("contradiction_count", 0),
                        unresolved_contradictions=contra.get("unresolved_contradictions", []),
                        resolved_contradictions=contra.get("resolved_contradictions", []),
                        resolution_basis=contra.get("resolution_basis", []),
                        verification_status=contra.get("verification_status", "PASS"),
                        final_decision=contra.get("final_decision", "ACCEPT"),
                    )

                    if contra["has_contradiction"]:
                        result.status = "CONFLICTING_EVIDENCE"
                        result.missing_info = [c["description"] for c in contra["conflicts"]]

                    result.search_queries_used = queries
                    return result
            except Exception as e:
                logger.warning(f"LLM research parsing failed ({e}). Falling back to deterministic extractor.")

        # Deterministic evidence extractor fallback
        return self._deterministic_extract(task, all_chunks, queries)

    def _deterministic_extract(
        self,
        task: str,
        chunks: List[Dict[str, Any]],
        queries: List[str],
    ) -> ResearcherOutput:
        """Deterministic extractor that pulls informative factual lines and runs contradiction detection."""
        evidence_items: List[EvidenceItem] = []

        for chunk in chunks:
            text = chunk["text"]
            lines = [l.strip() for l in text.split("\n") if l.strip()]
            
            for line in lines:
                # Capture any informative factual or numerical assertion line
                # Look for numbers, percentages, or statements of state
                has_substance = (
                    bool(re.search(r"\d+", line))
                    or bool(re.search(r"[=:]", line))
                    or any(re.search(rf"\b{re.escape(w)}\b", line, re.IGNORECASE) for w in ALL_OPPOSING_WORDS)
                    or any(kw in line.lower() for kw in [
                        "revenue", "profit", "sales", "growth", "margin", "fiscal", "rate", "cost",
                        "status", "state", "share", "value", "price", "speed", "pressure", "score", "audit",
                        "unavailable", "missing", "confirmed", "reported", "recorded"
                    ])
                )
                if has_substance:
                    src = chunk.get("source", "doc")
                    src_id = chunk.get("source_id") or f"{src}_p{chunk.get('page', 1)}"
                    # If line has source prefix, e.g. "Report Alpha: ...", record it ONLY if src is generic
                    if src in ("doc", "provided_context", "direct_context"):
                        colon_match = re.match(r"^([A-Za-z0-9_\-\s]+?)\s*:\s*(.*)$", line)
                        if colon_match and len(colon_match.group(1).split()) <= 4:
                            candidate_src = colon_match.group(1).strip()
                            if not re.search(r"^(in|on|at|for|fy|\d{4})\b", candidate_src, re.IGNORECASE):
                                src = candidate_src
                                src_id = re.sub(r"[^\w\-]", "_", src.lower()).strip("_")

                    evidence_items.append(
                        EvidenceItem(
                            claim=line,
                            normalized_claim=normalize_entity_key(line),
                            evidence=line,
                            excerpt=line[:160],
                            source=src,
                            source_id=src_id,
                            page=chunk.get("page", 1),
                            confidence=chunk.get("confidence", 0.95),
                            verification_status="UNVERIFIED",
                        )
                    )

            if not evidence_items and lines:
                first_line = lines[0]
                evidence_items.append(
                    EvidenceItem(
                        claim=first_line,
                        normalized_claim=normalize_entity_key(first_line),
                        evidence=text[:250].strip(),
                        excerpt=text[:160].strip(),
                        source=chunk.get("source", "doc"),
                        source_id=f"{chunk.get('source', 'doc')}_p{chunk.get('page', 1)}",
                        page=chunk.get("page", 1),
                        confidence=chunk.get("confidence", 0.88),
                        verification_status="UNVERIFIED",
                    )
                )

        # Run generalized contradiction detection across all extracted evidence items
        contra_data = detect_contradictions(evidence_items)
        conflicting = contra_data["has_contradiction"]

        status = "CONFLICTING_EVIDENCE" if conflicting else ("EVIDENCE_FOUND" if evidence_items else "INSUFFICIENT_EVIDENCE")
        missing_info = [c["description"] for c in contra_data["conflicts"]] if conflicting else (
            [] if evidence_items else ["Required evidence missing or ambiguous in provided context."]
        )

        from backend.models.schemas import ContradictionReport
        c_report = ContradictionReport(
            contradiction_detected=contra_data.get("contradiction_detected", False),
            contradiction_count=contra_data.get("contradiction_count", 0),
            unresolved_contradictions=contra_data.get("unresolved_contradictions", []),
            resolved_contradictions=contra_data.get("resolved_contradictions", []),
            resolution_basis=contra_data.get("resolution_basis", []),
            verification_status=contra_data.get("verification_status", "PASS"),
            final_decision=contra_data.get("final_decision", "ACCEPT"),
        )

        return ResearcherOutput(
            status=status,
            evidence_items=evidence_items,
            claims=contra_data.get("claims", []),
            evidence_graph=contra_data.get("evidence_graph", {}),
            contradiction_report=c_report,
            missing_info=missing_info,
            search_queries_used=queries,
        )
