"""
Pydantic Schemas for Multi-Agent AI Reasoning & Verification Engine.
Defines structured input/output contracts for all agents and verification modules.
"""

from typing import List, Dict, Any, Optional
from enum import Enum
from pydantic import BaseModel, Field
from datetime import datetime


class VerificationStatus(str, Enum):
    PASS = "PASS"
    FAIL = "FAIL"
    NEEDS_EVIDENCE = "NEEDS_EVIDENCE"
    BLOCKED = "BLOCKED"


class FinalDecision(str, Enum):
    ACCEPT = "ACCEPT"
    REVISE = "REVISE"
    REJECT = "REJECT"
    NEEDS_CLARIFICATION = "NEEDS_CLARIFICATION"


class SubTask(BaseModel):
    step_number: int
    description: str
    target_agent: str
    expected_output: str


class DatasetFilter(BaseModel):
    column: str
    operator: str = "=="  # "==", "!=", ">", ">=", "<", "<=", "in", "contains", "between"
    value: Any


class DatasetTaskSpec(BaseModel):
    task_type: str = "dataset_analysis"
    operation: str = "aggregate"  # "aggregate", "group_by", "compare", "range", "percentage", "filter", "extreme"
    target_dataset: Optional[str] = None
    target_column: Optional[str] = None
    aggregation: Optional[str] = None  # "mean", "median", "max", "min", "count", "sum", "std", "range"
    group_by_column: Optional[str] = None
    filters: List[DatasetFilter] = Field(default_factory=list)
    comparison: Optional[Dict[str, Any]] = None  # e.g. {"column": "RAM", "val_a": 4, "val_b": 8}
    order: Optional[str] = None  # "asc", "desc"
    limit: Optional[int] = None
    derived_metrics: List[str] = Field(default_factory=list)


class PlannerOutput(BaseModel):
    task_type: str = Field(description="Classification of the task, e.g., Financial Analysis, Calculation, Fact-Check")
    subtasks: List[str] = Field(default_factory=list, description="Ordered list of steps to accomplish the task")
    required_tools: List[str] = Field(default_factory=list, description="Tools needed, e.g., Python REPL, RAG, Calculator")
    required_evidence: List[str] = Field(default_factory=list, description="Evidence items required from source documents")
    dataset_task: Optional[DatasetTaskSpec] = Field(default=None, description="Structured dataset task specification if task is dataset analysis")
    is_self_contained: bool = Field(default=False, description="True if task is self-contained and requires no external evidence")
    requires_external_evidence: bool = Field(default=True, description="True if task requires external facts or document retrieval")



class EvidenceItem(BaseModel):
    claim: str
    normalized_claim: Optional[str] = None
    evidence: str
    excerpt: Optional[str] = None
    source: str
    source_id: Optional[str] = None
    page: Optional[int] = 1
    location: Optional[str] = None
    url: Optional[str] = None
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)
    verification_status: str = Field(
        default="UNVERIFIED",
        description="SUPPORTED | INSUFFICIENT_EVIDENCE | CONTRADICTED | UNVERIFIED"
    )
    metadata: Dict[str, Any] = Field(default_factory=dict)


class EvidenceClaim(BaseModel):
    claim_id: str
    source_id: str
    source_name: str
    page: Optional[int] = 1
    section: Optional[str] = None
    excerpt: str
    canonical_entity: str
    raw_entity: str
    extracted_value: Any
    unit: Optional[str] = None
    period: Optional[str] = None
    confidence: float = 1.0
    metadata: Dict[str, Any] = Field(default_factory=dict)


class EvidenceGroup(BaseModel):
    canonical_entity: str
    period: Optional[str] = None
    claims: List[EvidenceClaim] = Field(default_factory=list)
    distinct_values: List[Any] = Field(default_factory=list)
    supporting_sources: List[str] = Field(default_factory=list)
    is_conflicted: bool = False
    is_resolved: bool = False
    resolution_basis: Optional[str] = None
    resolved_value: Optional[Any] = None


class ContradictionReport(BaseModel):
    contradiction_detected: bool = False
    contradiction_count: int = 0
    unresolved_contradictions: List[Dict[str, Any]] = Field(default_factory=list)
    resolved_contradictions: List[Dict[str, Any]] = Field(default_factory=list)
    resolution_basis: List[str] = Field(default_factory=list)
    verification_status: str = "PASS"  # PASS | FAIL | BLOCKED
    final_decision: FinalDecision = FinalDecision.ACCEPT


class CandidateInputReference(BaseModel):
    parameter_name: str
    selected_value: Any
    source_id: str
    source_name: str
    period: Optional[str] = None
    has_alternative_evidence: bool = False
    is_conflicted: bool = False


class ResearcherOutput(BaseModel):
    status: str = Field(default="EVIDENCE_FOUND", description="EVIDENCE_FOUND | INSUFFICIENT_EVIDENCE | CONFLICTING_EVIDENCE")
    evidence_items: List[EvidenceItem] = Field(default_factory=list)
    claims: List[EvidenceClaim] = Field(default_factory=list)
    evidence_graph: Dict[str, EvidenceGroup] = Field(default_factory=dict)
    contradiction_report: Optional[ContradictionReport] = None
    missing_info: List[str] = Field(default_factory=list)
    search_queries_used: List[str] = Field(default_factory=list)


class CoderOutput(BaseModel):
    code: str = Field(default="", description="Python code generated or executed")
    explanation: str = Field(default="", description="Explanation of calculation/logic")
    inputs: Dict[str, Any] = Field(default_factory=dict, description="Variables extracted/used")
    input_references: List[CandidateInputReference] = Field(default_factory=list, description="Provenance for each input variable")
    execution_result: Optional[Any] = Field(default=None, description="Deterministic output from execution")
    calculation_steps: List[str] = Field(default_factory=list)
    error: Optional[str] = None


class VerificationCheck(BaseModel):
    check_name: str
    check_type: str = "factual"  # factual | calculation | contradiction | code | safety | consistency | logic
    passed: bool
    details: str
    expected: Optional[Any] = None
    actual: Optional[Any] = None
    calculation_status: Optional[str] = None  # VALID_INPUT | INSUFFICIENT_INPUT | CONFLICTING_INPUT | INVALID_INPUT | VERIFIED | MISMATCH | ERROR
    missing_parameters: List[str] = Field(default_factory=list)
    conflicting_parameters: List[str] = Field(default_factory=list)
    source: Optional[str] = None
    location: Optional[str] = None
    url: Optional[str] = None


class VerifierOutput(BaseModel):
    status: VerificationStatus
    reason: str
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    checks: List[VerificationCheck] = Field(default_factory=list)
    discrepancies: List[str] = Field(default_factory=list)
    recommended_action: FinalDecision
    calculated_value: Optional[Any] = None
    expected_value: Optional[Any] = None


class CriticFinding(BaseModel):
    severity: str = "MEDIUM"  # LOW | MEDIUM | HIGH | CRITICAL
    issue_type: str = "UNSUPPORTED"  # HALLUCINATION | CONTRADICTION | UNSUPPORTED | LOGICAL_FLAW | AMBIGUITY
    description: str
    evidence_involved: Optional[str] = None


class CriticOutput(BaseModel):
    has_critical_issues: bool = False
    findings: List[CriticFinding] = Field(default_factory=list)
    risk_score: float = Field(default=0.0, ge=0.0, le=1.0)
    recommendation: str = "PROCEED"  # PROCEED | REQUEST_REVISION | REJECT


class SafetyOutput(BaseModel):
    is_safe: bool = True
    risk_level: str = "SAFE"  # SAFE | LOW | MEDIUM | HIGH | CRITICAL
    reason: str = "No security violations detected"
    flagged_elements: List[str] = Field(default_factory=list)


class CitedEvidence(BaseModel):
    claim: str
    source: str
    page: Optional[int] = 1
    location: Optional[str] = None
    url: Optional[str] = None
    evidence: Optional[str] = None
    verified: bool = True


class SourceConflict(BaseModel):
    source_name: str
    location: Optional[str] = None
    value: Any = None
    evidence: str = ""


class ProvenanceInfo(BaseModel):
    source_type: str = "INTERNAL"  # DOCUMENT | WEB | DETERMINISTIC | CALCULATION | CODE | LOGIC | INTERNAL | CONTRADICTION | NOT_REQUIRED
    source_name: str = "No external source retrieved"
    location: Optional[str] = None
    url: Optional[str] = None
    evidence: str = ""
    verification: str = "Internal/independent verification"
    status: str = "PASS"  # PASS | FAIL | CONTRADICTION | BLOCKED | NOT_REQUIRED | UNVERIFIED
    confidence: float = 0.95
    conflicts: List[SourceConflict] = Field(default_factory=list)
    # Structured provenance fields
    source_title: Optional[str] = None
    source_domain: Optional[str] = None
    source_url: Optional[str] = None
    retrieved_evidence: Optional[str] = None
    retrieved_at: Optional[str] = None
    claim_supported: Optional[bool] = None
    expression: Optional[str] = None
    computed_result: Optional[Any] = None
    page: Optional[int] = None
    chunk_id: Optional[str] = None


class FinalizerOutput(BaseModel):
    final_answer: str
    decision: FinalDecision
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    cited_evidence: List[CitedEvidence] = Field(default_factory=list)
    verification_summary: str
    limitations: List[str] = Field(default_factory=list)
    source_provenance: Optional[ProvenanceInfo] = None


class RevisionAttempt(BaseModel):
    attempt_number: int
    trigger_reason: str
    target_agent: str
    previous_output: Dict[str, Any] = Field(default_factory=dict)
    correction_prompt: str
    revised_output: Dict[str, Any] = Field(default_factory=dict)
    verification_result: str
    timestamp: str


class AuditLogEntry(BaseModel):
    timestamp: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
    stage: str
    agent: str
    status: str
    details: Dict[str, Any] = Field(default_factory=dict)
    message: str = ""


# API Request/Response Schemas
class AnalyzeRequest(BaseModel):
    task: str = Field(..., description="The user task or query to process")
    context_text: Optional[str] = Field(default=None, description="Optional raw text document context")
    document_ids: List[str] = Field(default_factory=list, description="Uploaded document names or IDs")
    execution_mode: str = Field(default="standard", description="standard | strict_verification")


class AnalyzeResponse(BaseModel):
    task_id: str
    status: str
    final_decision: FinalDecision
    verification_status: str = "PASS"  # PASS | FAIL | BLOCKED
    contradiction_detected: bool = False
    contradiction_count: int = 0
    final_answer: str
    confidence: float
    planner_output: Optional[PlannerOutput] = None
    researcher_output: Optional[ResearcherOutput] = None
    coder_output: Optional[CoderOutput] = None
    verifier_output: Optional[VerifierOutput] = None
    critic_output: Optional[CriticOutput] = None
    safety_output: Optional[SafetyOutput] = None
    finalizer_output: Optional[FinalizerOutput] = None
    contradiction_report: Optional[ContradictionReport] = None
    audit_trail: List[AuditLogEntry] = Field(default_factory=list)
    revision_history: List[Dict[str, Any]] = Field(default_factory=list)
    raw_ai_output: Optional[str] = Field(default=None, description="Initial AI-generated answer from Gemini/API before verification")
    extracted_claims: List[str] = Field(default_factory=list, description="Claims extracted from raw AI answer")
    source_provenance: Optional[ProvenanceInfo] = Field(default=None, description="Structured source provenance information")
    limitations: List[str] = Field(default_factory=list)
    duration_seconds: float = 0.0


class DocumentUploadResponse(BaseModel):
    document_id: str
    filename: str
    chunks_count: int
    message: str
