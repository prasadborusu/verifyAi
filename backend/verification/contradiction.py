"""
Generalized Claim / Evidence Graph & Contradiction Detection Engine.
Enforces the fundamental architectural principle:
GENERATION != VERIFICATION.

Core Responsibilities:
1. Preserve structured source identity (source_id, source_name, page, excerpt, confidence, metadata).
2. Build a canonical Claim / Evidence Graph grouping claims by real-world entity, period, and unit.
3. Perform contradiction analysis BEFORE candidate answer verification or final calculation.
4. Attempt objective resolution ONLY when valid metadata exists (restatement, revision, audit status).
5. Produce machine-readable ContradictionReport with explicit states:
   contradiction_detected, contradiction_count, unresolved_contradictions,
   resolved_contradictions, resolution_basis, verification_status, final_decision.
"""

import re
import uuid
import logging
from typing import List, Dict, Any, Optional, Tuple, Set
from backend.models.schemas import (
    EvidenceItem,
    EvidenceClaim,
    EvidenceGroup,
    ContradictionReport,
    FinalDecision,
)

logger = logging.getLogger("verification_contradiction")

# Known temporal periods
MONTH_PATTERN = r"\b(january|february|march|april|may|june|july|august|september|october|november|december|jan|feb|mar|apr|jun|jul|aug|sep|oct|nov|dec)\b"
QUARTER_PATTERN = r"\b(q[1-4]|quarter\s*[1-4])\b"
YEAR_PATTERN = r"\b(19\d\d|20\d\d)\b"

# Opposing qualitative states
OPPOSING_STATES = [
    ({"active", "enabled", "operational", "running"}, {"inactive", "disabled", "inoperative", "stopped"}),
    ({"online", "up", "connected"}, {"offline", "down", "disconnected"}),
    ({"open", "opened"}, {"closed"}),
    ({"valid"}, {"invalid"}),
    ({"pass", "passed", "approved", "success", "successful", "compliant"}, {"fail", "failed", "rejected", "error", "noncompliant"}),
    ({"available", "present", "provided", "recorded", "confirmed"}, {"unavailable", "missing", "unknown", "absent", "pending", "omitted"}),
    ({"increased", "growth", "grew"}, {"decreased", "decline", "declined", "fell", "dropped"}),
    ({"true", "yes"}, {"false", "no"}),
]

ALL_OPPOSING_WORDS: Set[str] = set()
for _pos, _neg in OPPOSING_STATES:
    ALL_OPPOSING_WORDS.update(_pos)
    ALL_OPPOSING_WORDS.update(_neg)


def are_opposing_states(val1: Any, val2: Any) -> bool:
    """Determines if two values represent mutually conflicting categorical states."""
    v1 = str(val1).strip().lower()
    v2 = str(val2).strip().lower()
    if v1 == v2:
        return False
    for pos_set, neg_set in OPPOSING_STATES:
        if (v1 in pos_set and v2 in neg_set) or (v1 in neg_set and v2 in pos_set):
            return True
    return False


def is_conflicting_values(vals: List[Any]) -> bool:
    """Determines if a set of distinct values represents a true conflict."""
    if len(vals) < 2:
        return False
    # If any values are numerical
    has_numeric = any(isinstance(v, (int, float)) for v in vals)
    if has_numeric:
        num_vals = [float(v) for v in vals if isinstance(v, (int, float))]
        if len(num_vals) > 1 and max(num_vals) - min(num_vals) > 0.001:
            return True
        if len(num_vals) != len(vals):
            return True
        return False

    # Categorical string values
    str_vals = [str(v).strip().lower() for v in vals]
    for i in range(len(str_vals)):
        for j in range(i + 1, len(str_vals)):
            if are_opposing_states(str_vals[i], str_vals[j]):
                return True
            if str_vals[i] != str_vals[j]:
                if str_vals[i] in ALL_OPPOSING_WORDS or str_vals[j] in ALL_OPPOSING_WORDS:
                    return True
                # Two distinct short categorical states for the same canonical entity
                if len(str_vals[i].split()) <= 2 and len(str_vals[j].split()) <= 2:
                    return True
    return False


# Objective superseding indicators
SUPERSEDING_KEYWORDS = [
    "restatement", "audit restatement", "restated", "revised", "revision", "amended",
    "updated filing", "supersedes", "superseded", "final audited", "audited certification",
    "corrected", "correction", "official correction", "errata", "official errata", "v2", "version 2", "second edition"
]

PRELIMINARY_KEYWORDS = [
    "preliminary", "unaudited", "draft", "provisional", "initial estimate",
    "unverified", "v1", "version 1", "first draft"
]

NUMBER_REGEX = r"([+-]?(?:[0-9]{1,3}(?:,[0-9]{3})+|[0-9]+)(?:\.[0-9]+)?)"
CURRENCY_REGEX = r"(?:[₹$€£¥]|\b(?:inr|rs\.?|usd|eur|gbp|jpy|rupees?|dollars?|euros?|pounds?|yen)\b)"
UNIT_REGEX = r"([a-zA-Z%°]+(?:\s+[a-zA-Z]+)?)"

SCALE_MULTIPLIERS: Dict[str, float] = {
    "crore": 10_000_000.0,
    "crores": 10_000_000.0,
    "cr": 10_000_000.0,
    "lakh": 100_000.0,
    "lakhs": 100_000.0,
    "lac": 100_000.0,
    "lacs": 100_000.0,
    "million": 1_000_000.0,
    "millions": 1_000_000.0,
    "m": 1_000_000.0,
    "billion": 1_000_000_000.0,
    "billions": 1_000_000_000.0,
    "b": 1_000_000_000.0,
    "thousand": 1_000.0,
    "thousands": 1_000.0,
    "k": 1_000.0,
}

CURRENCY_NORM: Dict[str, str] = {
    "₹": "INR",
    "inr": "INR",
    "rs": "INR",
    "rs.": "INR",
    "rupee": "INR",
    "rupees": "INR",
    "$": "USD",
    "usd": "USD",
    "dollar": "USD",
    "dollars": "USD",
    "€": "EUR",
    "eur": "EUR",
    "euro": "EUR",
    "euros": "EUR",
    "£": "GBP",
    "gbp": "GBP",
    "pound": "GBP",
    "pounds": "GBP",
    "¥": "JPY",
    "jpy": "JPY",
    "yen": "JPY",
}


def normalize_unit_and_scale(
    val_float: float,
    currency_raw: Optional[str] = None,
    unit_raw: Optional[str] = None,
) -> Tuple[Any, Optional[str], float]:
    """
    Returns (clean_extracted_value, normalized_unit, base_numeric_value).
    Domain-agnostic normalization:
    - Normalizes currencies (₹, INR, Rs -> INR; $, USD -> USD; etc.)
    - Normalizes scale multipliers (crore -> 1e7, lakh -> 1e5, million -> 1e6, etc.)
    - Computes canonical base_numeric_value for cross-unit equivalence comparison.
    """
    curr_norm = None
    if currency_raw:
        c_clean = currency_raw.strip().lower()
        curr_norm = CURRENCY_NORM.get(c_clean, currency_raw.strip().upper())

    unit_clean = (unit_raw or "").strip()
    scale = 1.0

    if unit_clean:
        u_lower = unit_clean.lower()
        parts = u_lower.split()
        for p in parts:
            if p in SCALE_MULTIPLIERS:
                scale = SCALE_MULTIPLIERS[p]
                break
            if not curr_norm and p in CURRENCY_NORM:
                curr_norm = CURRENCY_NORM[p]

    final_unit_parts = []
    if curr_norm:
        final_unit_parts.append(curr_norm)
    if unit_clean:
        # Don't duplicate currency if already present
        if not curr_norm or unit_clean.upper() != curr_norm:
            final_unit_parts.append(unit_clean)

    final_unit = " ".join(final_unit_parts) if final_unit_parts else None
    base_val = val_float * scale
    clean_val = int(val_float) if val_float.is_integer() else val_float

    return clean_val, final_unit, base_val


def normalize_entity_key(text: str) -> str:
    """
    Normalizes an entity, metric, or subject name into a canonical key.
    Strictly enforces: ENTITY != VALUE.
    Strips any trailing assertion values or delimiters (=, :).
    """
    clean = text.strip()
    if "=" in clean:
        clean = clean.split("=")[0].strip()
    elif ":" in clean:
        parts = clean.split(":")
        if len(parts[0].split()) <= 4:
            clean = parts[0].strip()

    clean = clean.lower()
    clean = re.sub(r"^(the|a|an|in|for|of|fy|fiscal\s+year|current)\s+", "", clean).strip()
    clean = re.sub(r"[^\w\s]", " ", clean)
    clean = re.sub(r"\s+", " ", clean).strip()
    return clean


def extract_period_from_text(text: str) -> Optional[str]:
    """Extracts temporal scope (month, quarter, year, or fiscal period)."""
    text_lower = text.lower()
    
    # Month match
    m_month = re.search(MONTH_PATTERN, text_lower)
    m_quarter = re.search(QUARTER_PATTERN, text_lower)
    m_year = re.search(YEAR_PATTERN, text_lower)

    parts = []
    if m_month:
        parts.append(m_month.group(1).capitalize())
    if m_quarter:
        parts.append(m_quarter.group(1).upper())
    if m_year:
        parts.append(m_year.group(1))

    if parts:
        return " ".join(parts)
    return None


def extract_period_and_metric(text: str, default_period: Optional[str] = None) -> Tuple[Optional[str], str]:
    """
    Extracts temporal scope (month, quarter, year) and isolates the canonical metric name.
    Domain-agnostic: works for any metric (e.g. 'January visitors' -> ('January', 'visitors'),
    'FY 2024 revenue' -> ('2024', 'revenue'), 'Q2 churn' -> ('Q2', 'churn')).
    """
    clean = text.strip()
    m_month = re.search(MONTH_PATTERN, clean, re.IGNORECASE)
    m_quarter = re.search(QUARTER_PATTERN, clean, re.IGNORECASE)
    m_year = re.search(YEAR_PATTERN, clean, re.IGNORECASE)

    parts = []
    if m_month:
        parts.append(m_month.group(1).capitalize())
    if m_quarter:
        parts.append(m_quarter.group(1).upper())
    if m_year:
        parts.append(m_year.group(1))

    period = " ".join(parts) if parts else default_period

    metric = re.sub(MONTH_PATTERN, "", clean, flags=re.IGNORECASE)
    metric = re.sub(QUARTER_PATTERN, "", metric, flags=re.IGNORECASE)
    metric = re.sub(YEAR_PATTERN, "", metric, flags=re.IGNORECASE)
    metric = normalize_entity_key(metric)
    return period, (metric or normalize_entity_key(clean))


def extract_claims_from_item(item: EvidenceItem) -> List[EvidenceClaim]:
    """
    Extracts structured EvidenceClaim instances from an EvidenceItem.
    Preserves source identity, temporal scope, unit, value, and metadata.
    """
    claims: List[EvidenceClaim] = []
    text = item.evidence.strip()
    if not text:
        return claims

    # Check for embedded source demarcations ONLY if source is generic
    source_name = item.source
    source_id = item.source_id or re.sub(r"[^\w\-]", "_", item.source.lower()).strip("_")
    body_text = text

    if source_name in ("provided_context", "doc", "direct_context"):
        src_match = re.match(r"^([A-Za-z0-9_\-\s]{2,40}?)\s*:\s*(.*)$", text, re.DOTALL)
        if src_match and len(src_match.group(1).split()) <= 4:
            header_src = src_match.group(1).strip()
            if not re.search(r"^(in|on|at|for|fy|\d{4})\b", header_src, re.IGNORECASE):
                source_name = header_src
                source_id = re.sub(r"[^\w\-]", "_", header_src.lower()).strip("_")
                body_text = src_match.group(2).strip()

    # Extract default temporal period from item.claim or body_text
    item_period = extract_period_from_text(f"{item.claim} {body_text}")

    # Check for objective metadata flags (superseding, restatement, revision)
    meta = dict(item.metadata or {})
    full_text_to_check = f"{source_name} {item.claim} {body_text}".lower()
    if any(kw in full_text_to_check for kw in SUPERSEDING_KEYWORDS) or meta.get("is_superseding") or meta.get("revised") or meta.get("corrected"):
        meta["is_superseding"] = True
        meta["resolution_reason"] = next((kw for kw in sorted(SUPERSEDING_KEYWORDS, key=len, reverse=True) if kw in full_text_to_check), "restatement")
    if any(kw in full_text_to_check for kw in PRELIMINARY_KEYWORDS) or meta.get("is_preliminary"):
        meta["is_preliminary"] = True

    seen_claims: Set[Tuple[str, Optional[str], float]] = set()

    for raw_line in body_text.splitlines():
        line = raw_line.strip()
        if not line:
            continue

        # Clean text to prevent date components from masquerading as quantities
        clean_line = re.sub(r"\b20\d\d\s*[-/]?\s*q[1-4]\b", "", line, flags=re.IGNORECASE)
        clean_line = re.sub(r"\b(?:jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*\s+\d{1,2}(?:st|nd|rd|th)?\b", "", clean_line, flags=re.IGNORECASE)
        clean_line = re.sub(r"\b\d{1,2}(?:st|nd|rd|th)?\s+(?:jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*\b", "", clean_line, flags=re.IGNORECASE)

        # 1. Pattern: <Named Entity> [is|was|are|were|=|:|of|at|reached|recorded at] <Number> [Unit]
        pattern_metric = re.compile(
            rf"([a-zA-Z0-9_\s]{{2,40}}?)\s*(?:is|was|are|were|=|:|\bat\b|\breached\b|\brecorded\s+at\b|\bof\b)\s*({CURRENCY_REGEX})?\s*{NUMBER_REGEX}\s*({UNIT_REGEX})?",
            re.IGNORECASE,
        )
        for m in pattern_metric.finditer(clean_line):
            entity_raw = m.group(1).strip()
            curr_raw = m.group(2)
            val_str = m.group(3).replace(",", "").strip()
            unit_raw = m.group(4)

            try:
                val_float = float(val_str)
                period_found, canonical_name = extract_period_and_metric(entity_raw, default_period=item_period)
                if not canonical_name or canonical_name in {"it", "there", "this", "that", "which"}:
                    continue

                clean_val, final_unit, base_numeric = normalize_unit_and_scale(val_float, curr_raw, unit_raw)

                claim_sig = (canonical_name, period_found, base_numeric)
                if claim_sig in seen_claims:
                    continue
                seen_claims.add(claim_sig)

                claim_meta = {
                    **meta,
                    "base_numeric_value": base_numeric,
                    "raw_currency": curr_raw,
                }

                claims.append(
                    EvidenceClaim(
                        claim_id=f"clm_{uuid.uuid4().hex[:8]}",
                        source_id=source_id,
                        source_name=source_name,
                        page=item.page or 1,
                        excerpt=line[:160],
                        canonical_entity=canonical_name,
                        raw_entity=entity_raw,
                        extracted_value=clean_val,
                        unit=final_unit,
                        period=period_found,
                        confidence=item.confidence,
                        metadata=claim_meta,
                    )
                )
            except ValueError:
                pass

        # 2. Pattern: <Period/Year> <Metric> [is|was|=|:] <Number> [Unit]
        pattern_period_metric = re.compile(
            rf"(?:fy\s*)?(\b\d{{4}}\b|[a-zA-Z]{{3,15}})\s+([a-zA-Z_\s]{{2,30}}?)\s*(?:is|was|are|were|=|:|\bat\b|\breached\b|\brecorded\s+at\b|\bof\b)?\s*({CURRENCY_REGEX})?\s*{NUMBER_REGEX}\s*({UNIT_REGEX})?",
            re.IGNORECASE,
        )
        for m in pattern_period_metric.finditer(clean_line):
            period_lbl = m.group(1).strip()
            metric = m.group(2).strip()
            curr_raw = m.group(3)
            val_str = m.group(4).replace(",", "").strip()
            unit_raw = m.group(5)

            try:
                val_float = float(val_str)
                if period_lbl.isdigit() and val_float == float(period_lbl):
                    continue
                canonical_name = normalize_entity_key(metric)
                period_norm = period_lbl.capitalize() if not period_lbl.isdigit() else period_lbl

                clean_val, final_unit, base_numeric = normalize_unit_and_scale(val_float, curr_raw, unit_raw)

                claim_sig = (canonical_name, period_norm, base_numeric)
                if claim_sig in seen_claims:
                    continue
                seen_claims.add(claim_sig)

                claim_meta = {
                    **meta,
                    "base_numeric_value": base_numeric,
                    "raw_currency": curr_raw,
                }

                claims.append(
                    EvidenceClaim(
                        claim_id=f"clm_{uuid.uuid4().hex[:8]}",
                        source_id=source_id,
                        source_name=source_name,
                        page=item.page or 1,
                        excerpt=line[:160],
                        canonical_entity=canonical_name,
                        raw_entity=f"{period_lbl} {metric}",
                        extracted_value=clean_val,
                        unit=final_unit,
                        period=period_norm,
                        confidence=item.confidence,
                        metadata=claim_meta,
                    )
                )
            except ValueError:
                pass


    # 3. Pattern: Categorical State & Key-Value Claims (Separating Canonical Entity from Value)
    pattern_key_val = re.compile(
        r"^([a-zA-Z0-9_\s]{2,40}?)\s*(?:=|:)\s*([A-Za-z0-9_\-]{2,30})(?:\s*[\(\[].*?[\)\]])?\s*$",
        re.IGNORECASE,
    )
    pattern_copula = re.compile(
        r"([a-zA-Z0-9_\s]{2,40}?)\s+(?:is|was|are|were)(?:\s+reported\s+as|\s+set\s+to)?\s+([A-Za-z0-9_\-]{2,30})\b(?:\s*[\(\[].*?[\)\]])?",
        re.IGNORECASE,
    )

    for raw_line in body_text.splitlines():
        line = raw_line.strip()
        if not line:
            continue

        # Try key-value assertion: Entity = Value or Entity: Value
        m_kv = pattern_key_val.match(line)
        if m_kv:
            ent_cand = m_kv.group(1).strip()
            val_cand = m_kv.group(2).strip()
            if not re.search(r"^\d+$", val_cand):
                period_found, canonical_name = extract_period_and_metric(ent_cand, default_period=item_period)
                if canonical_name and canonical_name not in {"it", "there", "this", "that", "which"}:
                    val_clean = val_cand.upper()
                    sig = (canonical_name, period_found, val_clean)
                    if sig not in seen_claims:
                        seen_claims.add(sig)
                        claims.append(
                            EvidenceClaim(
                                claim_id=f"clm_{uuid.uuid4().hex[:8]}",
                                source_id=source_id,
                                source_name=source_name,
                                page=item.page or 1,
                                excerpt=line[:160],
                                canonical_entity=canonical_name,
                                raw_entity=ent_cand,
                                extracted_value=val_clean,
                                unit="state",
                                period=period_found,
                                confidence=item.confidence,
                                metadata=meta,
                            )
                        )
                        continue

        # Try copula assertion: Entity is Value
        m_cop = pattern_copula.search(line)
        if m_cop:
            ent_cand = m_cop.group(1).strip()
            val_cand = m_cop.group(2).strip()
            if not re.search(r"^\d+$", val_cand):
                period_found, canonical_name = extract_period_and_metric(ent_cand, default_period=item_period)
                if canonical_name and canonical_name not in {"it", "there", "this", "that", "which"}:
                    val_clean = val_cand.upper()
                    sig = (canonical_name, period_found, val_clean)
                    if sig not in seen_claims:
                        seen_claims.add(sig)
                        claims.append(
                            EvidenceClaim(
                                claim_id=f"clm_{uuid.uuid4().hex[:8]}",
                                source_id=source_id,
                                source_name=source_name,
                                page=item.page or 1,
                                excerpt=line[:160],
                                canonical_entity=canonical_name,
                                raw_entity=ent_cand,
                                extracted_value=val_clean,
                                unit="state",
                                period=period_found,
                                confidence=item.confidence,
                                metadata=meta,
                            )
                        )
                        continue

    # 4. Fallback: check item.claim for categorical assertion or state words
    if not claims:
        m_claim_kv = pattern_key_val.match(item.claim)
        if m_claim_kv:
            ent_cand = m_claim_kv.group(1).strip()
            val_cand = m_claim_kv.group(2).strip()
            period_found, canonical_name = extract_period_and_metric(ent_cand, default_period=item_period)
            if canonical_name:
                val_clean = val_cand.upper()
                claims.append(
                    EvidenceClaim(
                        claim_id=f"clm_{uuid.uuid4().hex[:8]}",
                        source_id=source_id,
                        source_name=source_name,
                        page=item.page or 1,
                        excerpt=body_text[:160],
                        canonical_entity=canonical_name,
                        raw_entity=ent_cand,
                        extracted_value=val_clean,
                        unit="state",
                        period=period_found,
                        confidence=item.confidence,
                        metadata=meta,
                    )
                )

        if not claims:
            for word in ALL_OPPOSING_WORDS:
                if re.search(rf"\b{re.escape(word)}\b", body_text, re.IGNORECASE):
                    # Clean entity by stripping parentheticals, the state word and any punctuation
                    clean_ent = re.sub(r"\s*[\(\[].*?[\)\]]", "", item.claim)
                    clean_ent = re.sub(rf"\b{re.escape(word)}\b", "", clean_ent, flags=re.IGNORECASE)
                    clean_ent = re.sub(r"[=:]", "", clean_ent).strip()
                    canonical_name = normalize_entity_key(clean_ent) if clean_ent else normalize_entity_key(item.claim)
                    sig = (canonical_name, item_period, word.upper())
                    if sig not in seen_claims:
                        seen_claims.add(sig)
                        claims.append(
                            EvidenceClaim(
                                claim_id=f"clm_{uuid.uuid4().hex[:8]}",
                                source_id=source_id,
                                source_name=source_name,
                                page=item.page or 1,
                                excerpt=body_text[:160],
                                canonical_entity=canonical_name,
                                raw_entity=clean_ent or item.claim,
                                extracted_value=word.upper(),
                                unit="state",
                                period=item_period,
                                confidence=item.confidence,
                                metadata=meta,
                            )
                        )

    return claims


def build_evidence_graph(evidence_items: List[EvidenceItem]) -> Tuple[Dict[str, EvidenceGroup], List[EvidenceClaim]]:
    """
    Builds the Claim / Evidence Graph by grouping claims referring to the same
    real-world entity and temporal period.
    """
    all_claims: List[EvidenceClaim] = []
    graph: Dict[str, EvidenceGroup] = {}

    for item in evidence_items:
        extracted = extract_claims_from_item(item)
        all_claims.extend(extracted)

    for c in all_claims:
        # Group key combines canonical entity and period (e.g. "visitors_february", "revenue_2024")
        period_key = f"_{c.period.lower()}" if c.period else ""
        group_key = f"{c.canonical_entity}{period_key}"

        if group_key not in graph:
            graph[group_key] = EvidenceGroup(
                canonical_entity=c.canonical_entity,
                period=c.period,
                claims=[],
                distinct_values=[],
                supporting_sources=[],
            )

        group = graph[group_key]
        group.claims.append(c)

        if c.source_name not in group.supporting_sources:
            group.supporting_sources.append(c.source_name)

        # Check for distinct values using base_numeric_value or raw value
        is_distinct = True
        c_base = c.metadata.get("base_numeric_value") if isinstance(c.metadata, dict) else None

        for existing_claim in group.claims[:-1]:
            ex_base = existing_claim.metadata.get("base_numeric_value") if isinstance(existing_claim.metadata, dict) else None
            if c_base is not None and ex_base is not None:
                max_b = max(abs(c_base), abs(ex_base), 1.0)
                if abs(c_base - ex_base) / max_b <= 0.001:
                    is_distinct = False
                    break
            elif isinstance(c.extracted_value, (int, float)) and isinstance(existing_claim.extracted_value, (int, float)):
                if abs(c.extracted_value - existing_claim.extracted_value) <= 0.001:
                    is_distinct = False
                    break
            elif str(c.extracted_value).strip().lower() == str(existing_claim.extracted_value).strip().lower():
                is_distinct = False
                break

        if is_distinct:
            group.distinct_values.append(c.extracted_value)

    return graph, all_claims


def evaluate_contradictions(
    evidence_graph: Dict[str, EvidenceGroup],
    all_claims: List[EvidenceClaim],
) -> ContradictionReport:
    """
    Evaluates cross-source contradictions and attempts objective resolution.
    Returns structured ContradictionReport with machine-readable status.
    """
    unresolved: List[Dict[str, Any]] = []
    resolved: List[Dict[str, Any]] = []
    resolution_bases: List[str] = []

    for group_key, group in evidence_graph.items():
        # Check base numeric conflicts across claims from different sources
        has_base_conflict = False
        claims_from_diff_sources = len(group.supporting_sources) > 1

        if claims_from_diff_sources:
            for i in range(len(group.claims)):
                for j in range(i + 1, len(group.claims)):
                    if group.claims[i].source_id != group.claims[j].source_id:
                        b1 = group.claims[i].metadata.get("base_numeric_value")
                        b2 = group.claims[j].metadata.get("base_numeric_value")
                        if b1 is not None and b2 is not None:
                            max_b = max(abs(b1), abs(b2), 1.0)
                            if abs(b1 - b2) / max_b > 0.001:
                                has_base_conflict = True
                                break
                        elif are_opposing_states(group.claims[i].extracted_value, group.claims[j].extracted_value):
                            has_base_conflict = True
                            break

        is_conflict = has_base_conflict or (
            len(group.distinct_values) > 1
            and claims_from_diff_sources
            and is_conflicting_values(group.distinct_values)
        )

        if is_conflict:
            group.is_conflicted = True

            # Attempt Objective Resolution
            resolution_found = False
            resolution_reason = None
            resolved_val = None

            # 1. Check for explicit superseding / restatement metadata
            superseding_claims = [c for c in group.claims if c.metadata.get("is_superseding")]
            preliminary_claims = [c for c in group.claims if c.metadata.get("is_preliminary")]

            if superseding_claims and (preliminary_claims or len(superseding_claims) < len(group.claims)):
                best_claim = superseding_claims[-1]
                resolution_found = True
                resolution_reason = (
                    f"Document restatement/revision: '{best_claim.source_name}' superseded prior value "
                    f"due to {best_claim.metadata.get('resolution_reason', 'audit restatement')}."
                )
                resolved_val = best_claim.extracted_value

            if resolution_found:
                group.is_resolved = True
                group.resolution_basis = resolution_reason
                group.resolved_value = resolved_val
                resolved.append({
                    "entity": group.canonical_entity,
                    "period": group.period,
                    "distinct_values": group.distinct_values,
                    "supporting_sources": group.supporting_sources,
                    "resolved_value": resolved_val,
                    "basis": resolution_reason,
                })
                resolution_bases.append(resolution_reason)
            else:
                group.is_resolved = False
                unresolved.append({
                    "canonical_entity": group.canonical_entity,
                    "entity": group.canonical_entity,
                    "period": group.period,
                    "distinct_values": group.distinct_values,
                    "supporting_sources": group.supporting_sources,
                    "description": (
                        f"Unresolved contradiction for '{group.canonical_entity}'"
                        f"{f' ({group.period})' if group.period else ''}: "
                        f"Sources {group.supporting_sources} report conflicting values {group.distinct_values}."
                    ),
                    "claims": [
                        {
                            "source_id": c.source_id,
                            "source_name": c.source_name,
                            "value": c.extracted_value,
                            "extracted_value": c.extracted_value,
                            "unit": c.unit,
                            "period": c.period,
                            "excerpt": c.excerpt,
                            "confidence": c.confidence,
                        }
                        for c in group.claims
                    ],
                })

    has_unresolved = len(unresolved) > 0
    total_contradictions = len(unresolved) + len(resolved)

    if has_unresolved:
        verification_status = "BLOCKED"
        final_decision = FinalDecision.NEEDS_CLARIFICATION
    else:
        verification_status = "PASS"
        final_decision = FinalDecision.ACCEPT

    return ContradictionReport(
        contradiction_detected=total_contradictions > 0,
        contradiction_count=total_contradictions,
        unresolved_contradictions=unresolved,
        resolved_contradictions=resolved,
        resolution_basis=resolution_bases,
        verification_status=verification_status,
        final_decision=final_decision,
    )


def detect_contradictions(evidence_items: List[EvidenceItem]) -> Dict[str, Any]:
    """
    Main contradiction detection entrypoint.
    Returns structured contradiction data and machine-readable fields.
    """
    if not evidence_items:
        return {
            "has_contradiction": False,
            "contradiction_detected": False,
            "contradiction_count": 0,
            "conflicts": [],
            "conflicting_metrics": [],
            "unresolved_contradictions": [],
            "resolved_contradictions": [],
            "resolution_basis": [],
            "verification_status": "PASS",
            "final_decision": FinalDecision.ACCEPT,
            "evidence_graph": {},
            "claims": [],
        }

    evidence_graph, all_claims = build_evidence_graph(evidence_items)
    report = evaluate_contradictions(evidence_graph, all_claims)

    conflicts = []
    conflicting_metrics = set()

    for item in report.unresolved_contradictions:
        entity_name = item.get("entity", "metric")
        conflicts.append({
            "metric": entity_name,
            "status": "CONTRADICTION",
            "sources": item.get("supporting_sources", []),
            "description": item.get("description", ""),
        })
        conflicting_metrics.add(entity_name)

    # Propagate verification status back to EvidenceItems
    for ev in evidence_items:
        ev_key = normalize_entity_key(ev.claim)
        if any(c_m in ev_key or ev_key in c_m for c_m in conflicting_metrics):
            ev.verification_status = "CONTRADICTED"
        elif report.resolved_contradictions and any(c_m in ev_key for c_m in [r["entity"] for r in report.resolved_contradictions]):
            ev.verification_status = "RESOLVED"
        elif not conflicts:
            ev.verification_status = "SUPPORTED"
        else:
            ev.verification_status = "UNVERIFIED"

    return {
        "has_contradiction": report.contradiction_detected and len(report.unresolved_contradictions) > 0,
        "contradiction_detected": report.contradiction_detected,
        "contradiction_count": report.contradiction_count,
        "conflicts": conflicts,
        "conflicting_metrics": sorted(list(conflicting_metrics)),
        "unresolved_contradictions": report.unresolved_contradictions,
        "resolved_contradictions": report.resolved_contradictions,
        "resolution_basis": report.resolution_basis,
        "verification_status": report.verification_status,
        "final_decision": report.final_decision,
        "evidence_graph": evidence_graph,
        "claims": all_claims,
    }
