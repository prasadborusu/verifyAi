"""
RAG Retrieval Engine using ChromaDB.
Provides semantic search over ingested document chunks with source, page, and confidence scores.
"""

import os
import logging
from typing import List, Dict, Any, Optional, Union, Protocol, runtime_checkable
import chromadb
from chromadb.config import Settings

logger = logging.getLogger("rag_retrieval")

CHROMA_PERSIST_DIR = os.getenv("CHROMA_PERSIST_DIR", "./chroma_db")
COLLECTION_NAME = "agent_knowledge_base"


def normalize_document_ids(document_ids: Any) -> List[str]:
    """
    Standardizes document_ids input into a clean list of non-empty strings.
    Handles None, single string, list, set, tuple, etc.
    """
    if not document_ids:
        return []
    if isinstance(document_ids, str):
        cleaned = document_ids.strip()
        return [cleaned] if cleaned else []
    if isinstance(document_ids, (list, tuple, set)):
        clean_list = []
        for d in document_ids:
            if d is not None:
                d_str = str(d).strip()
                if d_str and d_str not in clean_list:
                    clean_list.append(d_str)
        return clean_list
    return []


@runtime_checkable
class VectorStoreProtocol(Protocol):
    """Abstract protocol for vector store implementations."""
    def add_documents(self, chunks: List[Dict[str, Any]]) -> None: ...
    def search(
        self,
        query: str,
        top_k: int = 4,
        document_ids: Optional[Union[List[str], str, Any]] = None,
        **kwargs: Any,
    ) -> List[Dict[str, Any]]: ...


class VectorStoreManager:
    """Manages ChromaDB persistent collection with robust embeddings."""

    def __init__(self, persist_dir: str = CHROMA_PERSIST_DIR):
        self.persist_dir = persist_dir
        os.makedirs(self.persist_dir, exist_ok=True)
        self.client = chromadb.PersistentClient(
            path=self.persist_dir,
            settings=Settings(anonymized_telemetry=False),
        )
        self.collection = self.client.get_or_create_collection(
            name=COLLECTION_NAME,
            metadata={"description": "Grounded document repository for verification"},
        )
        logger.info(f"ChromaDB initialized at {self.persist_dir} (docs: {self.collection.count()})")

    def add_documents(self, chunks: List[Dict[str, Any]]) -> None:
        """Adds document chunks with metadata to ChromaDB."""
        if not chunks:
            return

        ids = [c["chunk_id"] for c in chunks]
        documents = [c["text"] for c in chunks]
        metadatas = [
            {"source": c.get("source", "unknown"), "page": int(c.get("page", 1))}
            for c in chunks
        ]

        self.collection.upsert(
            ids=ids,
            documents=documents,
            metadatas=metadatas,
        )
        logger.info(f"Upserted {len(chunks)} chunks into ChromaDB.")

    def search(
        self,
        query: str,
        top_k: int = 4,
        document_ids: Optional[Union[List[str], str, Any]] = None,
        **kwargs: Any,
    ) -> List[Dict[str, Any]]:
        """
        Retrieves top_k relevant chunks.
        Optionally scopes retrieval strictly to selected document_ids.
        Returns list of {text, source, page, distance, confidence}.
        """
        # Handle interface mismatches where document_ids or top_k might be passed in kwargs or swapped
        if document_ids is None:
            document_ids = (
                kwargs.get("doc_ids")
                or kwargs.get("filter_ids")
                or kwargs.get("dataset")
                or kwargs.get("document_id")
                or kwargs.get("selected_documents")
            )

        # Handle case where caller passed search(query, document_ids) positionally
        if isinstance(top_k, (list, tuple, set)) or (isinstance(top_k, str) and not top_k.isdigit()):
            if document_ids is None:
                document_ids = top_k
            top_k = kwargs.get("top_k", 4)
        elif isinstance(top_k, str) and top_k.isdigit():
            top_k = int(top_k)
        elif not isinstance(top_k, int) or top_k <= 0:
            top_k = 4

        try:
            count = self.collection.count()
        except Exception as e:
            logger.warning(f"Error checking collection count: {e}")
            return []

        if count == 0:
            return []

        actual_k = min(top_k, count)
        clean_docs = normalize_document_ids(document_ids)

        query_kwargs = {
            "query_texts": [query],
            "n_results": actual_k,
            "include": ["documents", "metadatas", "distances"],
        }

        if clean_docs:
            if len(clean_docs) == 1:
                query_kwargs["where"] = {"source": clean_docs[0]}
            elif len(clean_docs) > 1:
                query_kwargs["where"] = {"source": {"$in": clean_docs}}

        try:
            results = self.collection.query(**query_kwargs)
        except Exception as e:
            logger.warning(f"ChromaDB search query failed with filter {e}. Retrying with broader in-memory filter.")
            query_kwargs.pop("where", None)
            # Query more chunks so post-filtering does not discard everything
            query_kwargs["n_results"] = min(max(actual_k * 5, 20), count)
            try:
                results = self.collection.query(**query_kwargs)
            except Exception as e2:
                logger.error(f"Fallback ChromaDB query also failed: {e2}")
                results = None

        if not results or not isinstance(results, dict):
            return []

        docs_list = results.get("documents")
        if not docs_list or not isinstance(docs_list, list) or len(docs_list) == 0:
            return []

        docs = docs_list[0] or []
        raw_metas = results.get("metadatas")
        metas = (raw_metas[0] if raw_metas and len(raw_metas) > 0 and raw_metas[0] else None) or [{}] * len(docs)
        raw_dist = results.get("distances")
        distances = (raw_dist[0] if raw_dist and len(raw_dist) > 0 and raw_dist[0] else None) or [0.5] * len(docs)

        items = []
        for doc_text, meta, dist in zip(docs, metas, distances):
            src = meta.get("source", "document")
            if clean_docs:
                # Match exact source or basename
                src_base = os.path.basename(src)
                if src not in clean_docs and src_base not in clean_docs and not any(os.path.basename(cd) == src_base for cd in clean_docs):
                    continue

            # Convert distance to a normalized confidence score between 0.0 and 1.0
            conf = max(0.0, min(1.0, round(1.0 / (1.0 + float(dist)), 3)))
            items.append({
                "text": doc_text,
                "source": src,
                "page": meta.get("page", 1),
                "confidence": conf,
                "distance": float(dist),
            })
            if len(items) >= actual_k:
                break

        return items

# Canonical set of real indexed documents. Chunks from any other source
# (e.g., provided_context, test fixtures, ephemeral text) must not persist in ChromaDB.
KNOWN_REAL_DOCUMENTS: set = set()  # populated dynamically by scan_documents_directory()


def scan_documents_directory(documents_dir: str = "./documents") -> None:
    """
    Scans the documents/ directory and registers all filenames as known real documents.
    Must be called on startup so the purge guard knows which sources are legitimate.
    """
    import glob
    global KNOWN_REAL_DOCUMENTS
    abs_dir = os.path.abspath(documents_dir)
    if os.path.isdir(abs_dir):
        for fpath in glob.glob(os.path.join(abs_dir, "*")):
            fname = os.path.basename(fpath)
            if fname and not fname.startswith("."):
                KNOWN_REAL_DOCUMENTS.add(fname)
    logger.info(f"Known real documents: {sorted(KNOWN_REAL_DOCUMENTS)}")


def purge_non_document_chunks(store: "VectorStoreManager") -> int:
    """
    Removes all ChromaDB chunks whose 'source' metadata field is NOT in
    KNOWN_REAL_DOCUMENTS. This prevents ephemeral provided_context chunks from
    a previous session poisoning RAG retrieval.

    Returns the number of chunks deleted.
    """
    if not KNOWN_REAL_DOCUMENTS:
        logger.warning("KNOWN_REAL_DOCUMENTS is empty — skipping purge to avoid deleting everything.")
        return 0

    try:
        all_data = store.collection.get(include=["metadatas"])
        all_ids = all_data.get("ids", [])
        all_metas = all_data.get("metadatas", [])

        ids_to_delete = [
            chunk_id
            for chunk_id, meta in zip(all_ids, all_metas)
            if meta.get("source", "") not in KNOWN_REAL_DOCUMENTS
        ]

        if not ids_to_delete:
            logger.info("ChromaDB store is clean — no contaminated chunks found.")
            return 0

        batch_size = 100
        for i in range(0, len(ids_to_delete), batch_size):
            store.collection.delete(ids=ids_to_delete[i : i + batch_size])

        logger.warning(
            f"[PURGE] Deleted {len(ids_to_delete)} contaminated chunks "
            f"(sources outside known documents)."
        )
        return len(ids_to_delete)
    except Exception as e:
        logger.error(f"[PURGE] Failed to purge contaminated chunks: {e}")
        return 0


_vector_store_instance: Optional[VectorStoreManager] = None


def get_vector_store(documents_dir: str = "./documents") -> VectorStoreManager:
    """
    Returns the singleton VectorStoreManager.
    On first creation, scans the documents directory and purges any ephemeral
    chunks from previous sessions that should not be in the persistent store.
    """
    global _vector_store_instance
    if _vector_store_instance is None:
        _vector_store_instance = VectorStoreManager()
        scan_documents_directory(documents_dir)
        purge_non_document_chunks(_vector_store_instance)
    return _vector_store_instance

