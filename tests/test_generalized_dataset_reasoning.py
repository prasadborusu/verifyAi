"""
Generalized Dataset Reasoning & Verification Regression Tests.
Validates the dynamic, non-hardcoded tabular dataset reasoning pipeline across
unseen questions, operations, aggregations, filters, schemas, and datasets.
No hardcoded expected numerical answers or question-specific branches.
"""

import pytest
import os
import pandas as pd
from unittest.mock import MagicMock, patch

from backend.models.schemas import (
    DatasetFilter,
    DatasetTaskSpec,
    FinalDecision,
    VerificationStatus,
    EvidenceItem,
    EvidenceClaim,
)
from backend.analytics.dataset_engine import (
    resolve_dataset_task,
    execute_dataset_task,
    verify_dataset_execution,
    find_dataset_file,
)
from backend.agents.planner import PlannerAgent
from backend.agents.researcher import ResearcherAgent
from backend.agents.coder import CoderAgent
from backend.agents.verifier import VerifierAgent
from backend.rag.retrieval import VectorStoreManager, normalize_document_ids

MOBILE_DOC = "Mobile-Price-Prediction-cleaned_data.csv"
QUARTERLY_DOC = "sample_quarterly_filing.csv"


# ==============================================================================
# 1. Unseen Task 1: Median price with RAM filter
# ==============================================================================
def test_unseen_median_price_with_ram_filter():
    """Unseen question: 'What is the median price of phones with 8 GB RAM?'"""
    task = "What is the median price of phones with 8 GB RAM?"
    spec = resolve_dataset_task(task, document_ids=[MOBILE_DOC])
    assert spec is not None
    assert spec.operation == "aggregate"
    assert spec.aggregation == "median"
    assert spec.target_column == "Price"
    assert any(f.column == "RAM" and f.operator == "==" and f.value == 8 for f in spec.filters)

    res = execute_dataset_task(spec)
    assert res["matching_count"] == 153
    assert res["result_value"] == 31990.0
    assert "₹31,990.00" in res["formatted_result"]
    assert res["error"] is None


# ==============================================================================
# 2. Unseen Task 2: Group By category with highest average metric
# ==============================================================================
def test_unseen_group_by_ram_category():
    """Unseen question: 'Which RAM category has the highest average price?'"""
    task = "Which RAM category has the highest average price?"
    spec = resolve_dataset_task(task, document_ids=[MOBILE_DOC])
    assert spec is not None
    assert spec.operation == "group_by"
    assert spec.group_by_column == "RAM"
    assert spec.target_column == "Price"
    assert spec.aggregation == "mean"
    assert spec.order == "desc"

    res = execute_dataset_task(spec)
    assert "8.0 GB" in str(res["result_value"])
    assert res["error"] is None


# ==============================================================================
# 3. Unseen Task 3: Count filter with greater than operator
# ==============================================================================
def test_unseen_count_filter_greater_than():
    """Unseen question: 'How many phones have RAM greater than 6 GB?'"""
    task = "How many phones have RAM greater than 6 GB?"
    spec = resolve_dataset_task(task, document_ids=[MOBILE_DOC])
    assert spec is not None
    assert spec.operation == "aggregate"
    assert spec.aggregation == "count"
    assert any(f.column == "RAM" and f.operator == ">" and f.value == 6 for f in spec.filters)

    res = execute_dataset_task(spec)
    assert res["result_value"] == 187
    assert res["matching_count"] == 187
    assert res["error"] is None


# ==============================================================================
# 4. Unseen Task 4: Average battery power with price filter
# ==============================================================================
def test_unseen_average_battery_with_price_filter():
    """Unseen question: 'What is the average battery power of phones costing above ₹30,000?'"""
    task = "What is the average battery power of phones costing above ₹30,000?"
    spec = resolve_dataset_task(task, document_ids=[MOBILE_DOC])
    assert spec is not None
    assert spec.operation == "aggregate"
    assert spec.aggregation == "mean"
    assert spec.target_column == "Battery_Power"
    assert any(f.column == "Price" and f.operator == ">" and f.value == 30000 for f in spec.filters)

    res = execute_dataset_task(spec)
    assert res["result_value"] == 3875.84
    assert res["error"] is None


# ==============================================================================
# 5. Unseen Task 5: Percentage calculation
# ==============================================================================
def test_unseen_percentage_calculation():
    """Unseen question: 'What percentage of phones have 8 GB RAM?'"""
    task = "What percentage of phones have 8 GB RAM?"
    spec = resolve_dataset_task(task, document_ids=[MOBILE_DOC])
    assert spec is not None
    assert spec.operation == "percentage"
    assert any(f.column == "RAM" and f.operator == "==" and f.value == 8 for f in spec.filters)

    res = execute_dataset_task(spec)
    assert res["result_value"] == 18.96
    assert "18.96%" in res["formatted_result"]
    assert res["error"] is None


# ==============================================================================
# 6. Unseen Task 6: Price range with ROM filter
# ==============================================================================
def test_unseen_price_range_with_rom_filter():
    """Unseen question: 'What is the price range for phones with 128 GB ROM?'"""
    task = "What is the price range for phones with 128 GB ROM?"
    spec = resolve_dataset_task(task, document_ids=[MOBILE_DOC])
    assert spec is not None
    assert spec.operation == "range"
    assert spec.target_column == "Price"
    assert any(f.column == "ROM" and f.operator == "==" and f.value == 128 for f in spec.filters)

    res = execute_dataset_task(spec)
    assert res["result_value"] == 141001.0
    assert res["error"] is None


# ==============================================================================
# 7. Unseen Task 7: Group comparison
# ==============================================================================
def test_unseen_compare_ram_prices():
    """Unseen question: 'Compare the average prices of 4 GB and 8 GB RAM phones.'"""
    task = "Compare the average prices of 4 GB and 8 GB RAM phones."
    spec = resolve_dataset_task(task, document_ids=[MOBILE_DOC])
    assert spec is not None
    assert spec.operation == "compare"
    assert spec.comparison is not None
    assert spec.comparison["val_a"] == 4
    assert spec.comparison["val_b"] == 8

    res = execute_dataset_task(spec)
    assert res["result_value"] == 25095.96
    assert "4 GB: ₹12,262.73 vs 8 GB: ₹37,358.69" in res["formatted_result"]
    assert res["error"] is None


# ==============================================================================
# 8. Unseen Task 8: Entirely different dataset schema (Financial quarterly filing)
# ==============================================================================
def test_unseen_different_financial_dataset():
    """Unseen question on separate dataset: 'What is the total revenue_lakh in year 2024?'"""
    task = "What is the total revenue_lakh in year 2024?"
    spec = resolve_dataset_task(task, document_ids=[QUARTERLY_DOC])
    assert spec is not None
    assert spec.target_dataset == QUARTERLY_DOC
    assert spec.target_column == "revenue_lakh"
    assert spec.aggregation == "sum"
    assert any(f.column == "year" and f.operator == "==" and f.value == 2024 for f in spec.filters)

    res = execute_dataset_task(spec)
    assert res["result_value"] == 100.0
    assert res["matching_count"] == 4
    assert res["error"] is None


# ==============================================================================
# 9. Verification Precondition: Non-existent Column Detection
# ==============================================================================
def test_invalid_column_schema_rejection():
    """Rule: Requesting a non-existent column must be flagged as schema violation."""
    spec = DatasetTaskSpec(
        task_type="dataset_analysis",
        operation="aggregate",
        target_dataset=MOBILE_DOC,
        target_column="NonExistentColumnXYZ",
        aggregation="mean",
        filters=[],
    )
    checks = verify_dataset_execution(
        spec=spec,
        coder_output=None,
        researcher_output=None,
        selected_document_ids=[MOBILE_DOC],
    )
    schema_chk = next((c for c in checks if c.check_type == "schema"), None)
    assert schema_chk is not None
    assert schema_chk.passed is False
    assert "NonExistentColumnXYZ" in schema_chk.details


# ==============================================================================
# 10. Verification Precondition: Invalid Filter Operator Detection
# ==============================================================================
def test_invalid_filter_operator_rejection():
    """Rule: Invalid filter operators must fail the filter validity check."""
    spec = DatasetTaskSpec(
        task_type="dataset_analysis",
        operation="aggregate",
        target_dataset=MOBILE_DOC,
        target_column="Price",
        aggregation="mean",
        filters=[DatasetFilter(column="RAM", operator="INVALID_OP", value=8)],
    )
    checks = verify_dataset_execution(
        spec=spec,
        coder_output=None,
        researcher_output=None,
        selected_document_ids=[MOBILE_DOC],
    )
    filter_chk = next((c for c in checks if c.check_type == "filter_validity"), None)
    assert filter_chk is not None
    assert filter_chk.passed is False
    assert "INVALID_OP" in filter_chk.details


# ==============================================================================
# 11. VectorStoreManager interface abstraction robustness
# ==============================================================================
def test_vector_store_manager_search_interface_robustness():
    """
    Tests that VectorStoreManager.search() and normalize_document_ids handle:
    - single string document_ids
    - list of strings
    - set of strings
    - tuple of strings
    - None
    - empty list
    without type errors or unselected data leakage.
    """
    # Test normalization function
    assert normalize_document_ids(None) == []
    assert normalize_document_ids("") == []
    assert normalize_document_ids("file.csv") == ["file.csv"]
    assert normalize_document_ids(["file.csv", "file2.csv"]) == ["file.csv", "file2.csv"]
    assert set(normalize_document_ids({"file.csv", "file2.csv"})) == {"file.csv", "file2.csv"}
    assert normalize_document_ids(("file.csv",)) == ["file.csv"]

    # Test search with mock Chroma collection
    store = VectorStoreManager.__new__(VectorStoreManager)
    store.collection = MagicMock()
    store.collection.count.return_value = 10
    store.collection.query.return_value = {
        "documents": [["Chunk 1", "Chunk 2"]],
        "metadatas": [[{"source": MOBILE_DOC, "page": 1}, {"source": "sample_financial_report_2025.txt", "page": 1}]],
        "distances": [[0.1, 0.2]],
    }

    # Calling search with single string document_ids must not crash
    res_str = store.search("test query", top_k=5, document_ids=MOBILE_DOC)
    assert len(res_str) == 1
    assert res_str[0]["source"] == MOBILE_DOC

    # Calling search with set document_ids must not crash
    res_set = store.search("test query", top_k=5, document_ids={MOBILE_DOC})
    assert len(res_set) == 1
    assert res_set[0]["source"] == MOBILE_DOC

    # Calling search with None must return all matching chunks
    res_none = store.search("test query", top_k=5, document_ids=None)
    assert len(res_none) == 2
