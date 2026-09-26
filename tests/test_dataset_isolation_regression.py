"""
Dataset Isolation Regression Tests.

Verifies that DOCUMENT / RAG mode strictly scopes retrieval to the selected dataset.
No cross-dataset bleed, no provided_context persistence, no stale execution state leakage.

Covers:
1. Mobile dataset retrieves ONLY mobile dataset chunks (source filtering).
2. Financial document chunks cannot appear in a mobile query.
3. ingest_raw_text does NOT write to ChromaDB.
4. Researcher source count corresponds to the selected dataset only.
5. Cross-dataset retrieval is blocked by the isolation guard.
6. A mobile query must never produce financial/revenue evidence.
7. The isolation guard returns ISOLATION_BLOCKED when leakage is detected.
"""

import sys
import os
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from unittest.mock import patch, MagicMock
from backend.rag.retrieval import VectorStoreManager, purge_non_document_chunks
from backend.rag.ingestion import ingest_raw_text
from backend.agents.researcher import ResearcherAgent, ISOLATION_BLOCKED, _build_isolation_blocked_response


MOBILE_DOC = "Mobile-Price-Prediction-cleaned_data.csv"
FINANCIAL_DOC = "sample_financial_report_2025.txt"


def _make_chunk(source: str, text: str = "test data") -> dict:
    return {"text": text, "source": source, "page": 1, "confidence": 0.9, "distance": 0.1}


class TestRetrievalDocumentIdsFilter:
    """Verify ChromaDB search enforces document_ids scoping at retrieval time."""

    def test_search_with_single_document_id_builds_where_clause(self):
        store = VectorStoreManager.__new__(VectorStoreManager)
        store.collection = MagicMock()
        store.collection.count.return_value = 10
        store.collection.query.return_value = {
            "documents": [["RAM: 8 GB Price: 35000"]],
            "metadatas": [[{"source": MOBILE_DOC, "page": 1}]],
            "distances": [[0.05]],
        }

        store.search("average price 8 GB RAM", top_k=5, document_ids=[MOBILE_DOC])

        call_kwargs = store.collection.query.call_args[1]
        assert "where" in call_kwargs, "Must include where filter when document_ids is set"
        assert call_kwargs["where"] == {"source": MOBILE_DOC}

    def test_search_without_document_ids_no_where_clause(self):
        store = VectorStoreManager.__new__(VectorStoreManager)
        store.collection = MagicMock()
        store.collection.count.return_value = 10
        store.collection.query.return_value = {
            "documents": [["some text"]],
            "metadatas": [[{"source": "any_doc.txt", "page": 1}]],
            "distances": [[0.1]],
        }

        store.search("some query", top_k=5, document_ids=None)

        call_kwargs = store.collection.query.call_args[1]
        assert "where" not in call_kwargs, "Must NOT include where filter when document_ids is None"

    def test_search_post_filter_strips_wrong_source(self):
        store = VectorStoreManager.__new__(VectorStoreManager)
        store.collection = MagicMock()
        store.collection.count.return_value = 10
        store.collection.query.return_value = {
            "documents": [["Revenue 2025: 120M", "RAM: 8 Price: 35000"]],
            "metadatas": [[{"source": FINANCIAL_DOC, "page": 1}, {"source": MOBILE_DOC, "page": 1}]],
            "distances": [[0.2, 0.05]],
        }

        results = store.search("average price 8 GB RAM", top_k=5, document_ids=[MOBILE_DOC])

        sources = [r["source"] for r in results]
        assert FINANCIAL_DOC not in sources, "Financial doc chunk must be stripped by post-filter"
        assert MOBILE_DOC in sources, "Mobile doc chunk must remain"


class TestIngestRawTextDoesNotPolluteChromeDB:
    """ingest_raw_text() must be purely in-memory -- no side effects to ChromaDB."""

    def test_ingest_raw_text_returns_chunks_without_chroma_write(self):
        financial_text = "Revenue 2024: 75 lakh. Revenue 2025: 120 lakh."

        with patch("backend.rag.retrieval.get_vector_store") as mock_get_store:
            mock_store = MagicMock()
            mock_get_store.return_value = mock_store

            chunks = ingest_raw_text(financial_text, source_name="provided_context")

        assert len(chunks) > 0, "Should return at least one chunk"
        mock_store.add_documents.assert_not_called()

    def test_ingest_raw_text_chunks_have_correct_source(self):
        chunks = ingest_raw_text("Some text about revenue.", source_name="my_test_context")
        assert len(chunks) > 0
        for chunk in chunks:
            assert "my_test_context" in chunk["source"]


class TestResearcherIsolationGuard:
    """Researcher returns ISOLATION_BLOCKED when retrieved sources are outside document_ids."""

    def test_isolation_guard_blocks_wrong_source_chunks_for_txt_document(self):
        """
        When a TXT document is selected (financial report), but the vector store
        returns chunks from a DIFFERENT source (mobile CSV), the isolation guard
        must block with ISOLATION_BLOCKED.

        This tests the vector store path (non-CSV documents don't use the CSV fast-path).
        """
        agent = ResearcherAgent.__new__(ResearcherAgent)
        agent.gemini = MagicMock()
        agent.gemini.is_available.return_value = False
        agent.prompt_template = ""

        # Selected: financial TXT doc. But vector store returns: mobile CSV chunks (wrong source)
        mock_store = MagicMock()
        mock_store.search.return_value = [
            _make_chunk(MOBILE_DOC, "RAM: 8 GB, Price: 35000"),
            _make_chunk(MOBILE_DOC, "RAM: 8 GB, Price: 40000"),
        ]
        agent.vector_store = mock_store

        result = agent.research(
            task="What was the revenue in 2025?",
            document_ids=[FINANCIAL_DOC],  # TXT doc -- uses vector store path
        )

        assert result.status == ISOLATION_BLOCKED, f"Expected ISOLATION_BLOCKED but got: {result.status}"
        guard_item = result.evidence_items[0]
        assert guard_item.verification_status == "BLOCKED"
        assert MOBILE_DOC in str(guard_item.metadata.get("leaked_sources", []))
        assert FINANCIAL_DOC in str(guard_item.metadata.get("selected_documents", []))

    def test_isolation_guard_blocks_financial_chunks_when_csv_not_found(self):
        """
        When mobile CSV is selected but the CSV file doesn't exist on disk,
        code falls through to vector store search. If the vector store then
        returns financial chunks, the isolation guard must fire.
        """
        agent = ResearcherAgent.__new__(ResearcherAgent)
        agent.gemini = MagicMock()
        agent.gemini.is_available.return_value = False
        agent.prompt_template = ""

        mock_store = MagicMock()
        mock_store.search.return_value = [
            _make_chunk(FINANCIAL_DOC, "Revenue 2025: 120 lakh"),
            _make_chunk(FINANCIAL_DOC, "Revenue 2024: 75 lakh"),
        ]
        agent.vector_store = mock_store

        # Force os.path.exists to return False for the CSV path
        with patch("os.path.exists", return_value=False):
            result = agent.research(
                task="What is the average price of mobile phones with 8 GB RAM?",
                document_ids=[MOBILE_DOC],
            )

        assert result.status == ISOLATION_BLOCKED, f"Expected ISOLATION_BLOCKED but got: {result.status}"
        guard_item = result.evidence_items[0]
        assert guard_item.verification_status == "BLOCKED"
        assert FINANCIAL_DOC in str(guard_item.metadata.get("leaked_sources", []))
        assert MOBILE_DOC in str(guard_item.metadata.get("selected_documents", []))

    def test_isolation_guard_passes_when_only_selected_source_returned(self):
        agent = ResearcherAgent.__new__(ResearcherAgent)
        agent.gemini = MagicMock()
        agent.gemini.is_available.return_value = False
        agent.prompt_template = ""

        mock_store = MagicMock()
        mock_store.search.return_value = [
            _make_chunk(MOBILE_DOC, "RAM: 8 GB, Price: 35000"),
            _make_chunk(MOBILE_DOC, "RAM: 8 GB, Price: 40000"),
        ]
        agent.vector_store = mock_store

        result = agent.research(
            task="What is the average price of mobile phones with 8 GB RAM?",
            document_ids=[MOBILE_DOC],
        )

        assert result.status != ISOLATION_BLOCKED, f"Should NOT be blocked, got: {result.status}"

    def test_no_document_ids_does_not_trigger_guard(self):
        agent = ResearcherAgent.__new__(ResearcherAgent)
        agent.gemini = MagicMock()
        agent.gemini.is_available.return_value = False
        agent.prompt_template = ""

        mock_store = MagicMock()
        mock_store.search.return_value = [
            _make_chunk(FINANCIAL_DOC, "Revenue 2025: 120 lakh"),
        ]
        agent.vector_store = mock_store

        result = agent.research(
            task="What was the revenue in 2025?",
            document_ids=None,
        )

        assert result.status != ISOLATION_BLOCKED


class TestIsolationBlockedResponseStructure:
    def test_builds_correct_metadata(self):
        resp = _build_isolation_blocked_response(
            selected_docs=[MOBILE_DOC],
            leaked_sources=[FINANCIAL_DOC],
            queries=["test query"],
        )
        assert resp.status == ISOLATION_BLOCKED
        assert len(resp.evidence_items) == 1
        item = resp.evidence_items[0]
        assert item.verification_status == "BLOCKED"
        assert item.metadata["selected_documents"] == [MOBILE_DOC]
        assert item.metadata["leaked_sources"] == [FINANCIAL_DOC]
        assert resp.contradiction_report.contradiction_detected is True
        assert resp.contradiction_report.verification_status == "BLOCKED"

    def test_contradiction_report_has_reject_decision(self):
        from backend.models.schemas import FinalDecision
        resp = _build_isolation_blocked_response(
            selected_docs=[MOBILE_DOC],
            leaked_sources=[FINANCIAL_DOC],
            queries=[],
        )
        assert resp.contradiction_report.final_decision == FinalDecision.REJECT


class TestPurgeNonDocumentChunks:
    def test_purges_non_real_document_chunks(self):
        mock_store = MagicMock()
        mock_store.collection.get.return_value = {
            "ids": ["id_mobile_1", "id_context_1", "id_financial_1"],
            "metadatas": [
                {"source": MOBILE_DOC},
                {"source": "provided_context"},
                {"source": FINANCIAL_DOC},
            ],
        }

        import backend.rag.retrieval as retrieval_mod
        original_known = retrieval_mod.KNOWN_REAL_DOCUMENTS.copy()
        try:
            retrieval_mod.KNOWN_REAL_DOCUMENTS = {MOBILE_DOC, FINANCIAL_DOC}
            deleted = purge_non_document_chunks(mock_store)
            assert deleted == 1
            mock_store.collection.delete.assert_called_once()
            deleted_ids = mock_store.collection.delete.call_args[1]["ids"]
            assert "id_context_1" in deleted_ids
            assert "id_mobile_1" not in deleted_ids
        finally:
            retrieval_mod.KNOWN_REAL_DOCUMENTS = original_known

    def test_purge_skips_when_no_known_documents_registered(self):
        mock_store = MagicMock()
        import backend.rag.retrieval as retrieval_mod
        original_known = retrieval_mod.KNOWN_REAL_DOCUMENTS.copy()
        try:
            retrieval_mod.KNOWN_REAL_DOCUMENTS = set()
            deleted = purge_non_document_chunks(mock_store)
            assert deleted == 0
            mock_store.collection.delete.assert_not_called()
        finally:
            retrieval_mod.KNOWN_REAL_DOCUMENTS = original_known


class TestCrossDatasetEvidencePrevention:
    """Mobile query + mobile dataset must produce zero financial evidence."""

    def test_mobile_query_produces_no_financial_evidence(self):
        agent = ResearcherAgent.__new__(ResearcherAgent)
        agent.gemini = MagicMock()
        agent.gemini.is_available.return_value = False
        agent.prompt_template = ""

        mock_store = MagicMock()
        mock_store.search.return_value = [
            _make_chunk(MOBILE_DOC, "RAM: 8 GB, Price: 35000, Brand: Samsung"),
            _make_chunk(MOBILE_DOC, "RAM: 8 GB, Price: 42000, Brand: Apple"),
        ]
        agent.vector_store = mock_store

        result = agent.research(
            task="What is the average price of mobile phones with 8 GB RAM?",
            document_ids=[MOBILE_DOC],
        )

        assert result.status != ISOLATION_BLOCKED

        financial_keywords = ["revenue", "lakh", "fiscal", "financial report"]
        all_text = " ".join(item.evidence for item in result.evidence_items).lower()
        for keyword in financial_keywords:
            assert keyword not in all_text, f"Financial keyword '{keyword}' leaked into mobile query result"

    def test_financial_query_produces_no_mobile_evidence(self):
        agent = ResearcherAgent.__new__(ResearcherAgent)
        agent.gemini = MagicMock()
        agent.gemini.is_available.return_value = False
        agent.prompt_template = ""

        mock_store = MagicMock()
        mock_store.search.return_value = [
            _make_chunk(FINANCIAL_DOC, "Revenue FY 2024: 75 lakh"),
            _make_chunk(FINANCIAL_DOC, "Revenue FY 2025: 120 lakh"),
        ]
        agent.vector_store = mock_store

        result = agent.research(
            task="What was the revenue in the 2025 financial report?",
            document_ids=[FINANCIAL_DOC],
        )

        assert result.status != ISOLATION_BLOCKED

        mobile_keywords = ["mobile", "phone", "ram", "smartphone", "brand"]
        all_text = " ".join(item.evidence for item in result.evidence_items).lower()
        for keyword in mobile_keywords:
            assert keyword not in all_text, f"Mobile keyword '{keyword}' leaked into financial query result"
