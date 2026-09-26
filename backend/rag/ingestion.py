"""
Document Ingestion & Chunking for RAG System.
Supports PDF, TXT, and CSV document parsing with page & source metadata preservation.
"""

import os
import re
import uuid
import logging
from typing import List, Dict, Any
import pandas as pd
from fastapi import UploadFile

logger = logging.getLogger("rag_ingestion")

DOCUMENTS_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "documents")
CHROMA_DIR = os.getenv("CHROMA_PERSIST_DIR", "./chroma_db")


def extract_text_from_file(file_path: str, filename: str) -> List[Dict[str, Any]]:
    """
    Extracts text chunks preserving page numbers and document names.
    Returns list of {"text": str, "source": str, "page": int, "chunk_id": str}
    """
    ext = os.path.splitext(filename)[1].lower()
    chunks = []

    if ext == ".pdf":
        try:
            import pypdf
            reader = pypdf.PdfReader(file_path)
            for page_num, page in enumerate(reader.pages, start=1):
                page_text = page.extract_text() or ""
                page_text = page_text.strip()
                if not page_text:
                    continue
                # Split page into chunks if large
                subchunks = split_text_into_chunks(page_text, max_chars=800, overlap=100)
                for sc in subchunks:
                    chunks.append({
                        "text": sc,
                        "source": filename,
                        "page": page_num,
                        "chunk_id": f"{filename}_p{page_num}_{uuid.uuid4().hex[:6]}",
                    })
        except Exception as e:
            logger.error(f"Error reading PDF {filename}: {e}")
            raise ValueError(f"Failed to parse PDF file: {e}")

    elif ext == ".csv":
        try:
            df = pd.read_csv(file_path)
            # Create readable table summary or row chunks
            csv_summary = df.to_string(index=False)
            chunks.append({
                "text": f"CSV Dataset: {filename}\nColumns: {list(df.columns)}\nRows: {len(df)}\n\nSample / Data:\n{csv_summary[:3000]}",
                "source": filename,
                "page": 1,
                "chunk_id": f"{filename}_p1_{uuid.uuid4().hex[:6]}",
            })
        except Exception as e:
            logger.error(f"Error reading CSV {filename}: {e}")
            raise ValueError(f"Failed to parse CSV file: {e}")

    elif ext in [".txt", ".md", ".json"]:
        try:
            with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                content = f.read()
            subchunks = split_text_into_chunks(content, max_chars=800, overlap=100)
            for i, sc in enumerate(subchunks):
                chunks.append({
                    "text": sc,
                    "source": filename,
                    "page": 1,
                    "chunk_id": f"{filename}_c{i}_{uuid.uuid4().hex[:6]}",
                })
        except Exception as e:
            logger.error(f"Error reading text file {filename}: {e}")
            raise ValueError(f"Failed to parse text file: {e}")
    else:
        raise ValueError(f"Unsupported file type: {ext}. Supported: PDF, CSV, TXT")

    return chunks


def split_text_into_chunks(text: str, max_chars: int = 800, overlap: int = 100) -> List[str]:
    """Sliding window chunking by character boundaries."""
    if len(text) <= max_chars:
        return [text]

    chunks = []
    start = 0
    while start < len(text):
        end = min(start + max_chars, len(text))
        chunk = text[start:end].strip()
        if chunk:
            chunks.append(chunk)
        start += max_chars - overlap
    return chunks


async def ingest_document_file(upload_file: UploadFile) -> Dict[str, Any]:
    """Saves uploaded file and indexes its chunks into ChromaDB."""
    os.makedirs(DOCUMENTS_DIR, exist_ok=True)
    filename = upload_file.filename or f"doc_{uuid.uuid4().hex[:6]}.txt"
    file_path = os.path.join(DOCUMENTS_DIR, filename)

    contents = await upload_file.read()
    with open(file_path, "wb") as f:
        f.write(contents)

    chunks = extract_text_from_file(file_path, filename)
    doc_id = f"doc_{uuid.uuid4().hex[:8]}"

    from backend.rag.retrieval import get_vector_store
    store = get_vector_store()
    store.add_documents(chunks)

    return {
        "document_id": doc_id,
        "filename": filename,
        "file_path": file_path,
        "chunks_count": len(chunks),
    }


def parse_sources_from_text(text: str, default_source: str = "direct_context") -> List[Dict[str, Any]]:
    """
    Parses multi-source text into distinct source blocks preserving source identity.
    Recognizes patterns like:
      - Source A — Monthly Analytics / Source B — Management Summary (em-dash, hyphen, en-dash)
      - Source A: ... / Report Beta: ...
      - [Monthly Analytics] ... / [Management Summary] ...
      - # Source Name ...
      - Document A / Filing 2024 ...
    """
    cleaned = text.strip()
    if not cleaned:
        return []

    # 1. Bracketed sources: [Source Name.ext]
    if re.search(r"(?:^|\n)\[([A-Za-z0-9_\-\s\.]{2,60})\]", cleaned):
        parts = re.split(r"(?:^|\n)\[([A-Za-z0-9_\-\s\.]{2,60})\]\s*\n?", cleaned)
        results = []
        i = 1
        while i < len(parts):
            src_name = parts[i].strip()
            content = parts[i+1].strip() if i + 1 < len(parts) else ""
            if content:
                results.append({"source": src_name, "text": content})
            i += 2
        if results:
            return results

    # 2. Markdown headers: # Source Name or ## Source Name
    if re.search(r"(?:^|\n)#{1,3}\s+([A-Za-z0-9_\-\s]{2,50})\n", cleaned):
        parts = re.split(r"(?:^|\n)#{1,3}\s+([A-Za-z0-9_\-\s]{2,50})\n+", cleaned)
        results = []
        i = 1
        while i < len(parts) - 1:
            src_name = parts[i].strip()
            content = parts[i+1].strip()
            if content:
                results.append({"source": src_name, "text": content})
            i += 2
        if results:
            return results

    # 3. Source header blocks with dash / em-dash / colon: e.g. Source A — Monthly Analytics
    # or Source A:\n or Report Alpha:\n
    header_pattern = r"(?:^|\n\n+|\n)(?=(?:Source|Report|Document|Filing|Doc|Dataset)\s+[A-Za-z0-9_\-]+(?:\s*[\:\—\–\-]\s*[^\n]{1,60})?\s*\n|[A-Za-z0-9_\-\s]{2,40}\s*[\—\–]\s*[^\n]{1,60}\s*\n)"
    sections = re.split(header_pattern, cleaned)
    sections = [s.strip() for s in sections if s.strip()]
    if len(sections) >= 2:
        results = []
        for s in sections:
            m = re.match(r"^((?:Source|Report|Document|Filing|Doc|Dataset)\s+[A-Za-z0-9_\-]+(?:\s*[\:\—\–\-]\s*[^\n]{1,60})?|[A-Za-z0-9_\-\s]{2,40}\s*[\—\–]\s*[^\n]{1,60}|[A-Za-z0-9_\-\s]{2,40}:)\s*\n(.*)", s, re.DOTALL)
            if m:
                src = m.group(1).strip().rstrip(":")
                body = m.group(2).strip()
                if body:
                    results.append({"source": src, "text": body})
            else:
                results.append({"source": default_source, "text": s})
        if len(results) >= 2:
            return results

    # 4. Standard colon split: Source Name: ...
    sections = re.split(r"\n+(?=[A-Za-z0-9_\-\s]{2,40}:)", cleaned)
    if len(sections) >= 2:
        results = []
        for s in sections:
            m = re.match(r"^([A-Za-z0-9_\-\s]{2,40}):\s*(.*)", s, re.DOTALL)
            if m:
                src_name = m.group(1).strip()
                content = m.group(2).strip()
                if content:
                    results.append({"source": src_name, "text": content})
            elif s.strip():
                results.append({"source": default_source, "text": s.strip()})
        if len(results) >= 2:
            return results

    # Single source fallback
    return [{"source": default_source, "text": cleaned}]


def ingest_raw_text(text: str, source_name: str = "direct_context") -> List[Dict[str, Any]]:
    """
    Parses raw direct context text into in-memory chunks preserving distinct source identities.

    CRITICAL: This function does NOT write anything to ChromaDB.
    Provided context is ephemeral and must never pollute the persistent RAG store.
    Each agent execution receives context only in its local in-memory chunks list.
    """
    parsed_sources = parse_sources_from_text(text, default_source=source_name)
    chunks = []

    for entry in parsed_sources:
        src = entry["source"]
        src_text = entry["text"]
        subchunks = split_text_into_chunks(src_text, max_chars=800, overlap=100)
        clean_src_id = re.sub(r"[^\w\-]", "_", src.lower()).strip("_")
        for i, sc in enumerate(subchunks):
            chunks.append({
                "text": sc,
                "source": src,
                "source_id": f"{clean_src_id}_c{i}",
                "page": 1,
                "chunk_id": f"{clean_src_id}_c{i}_{uuid.uuid4().hex[:6]}",
            })

    # NOTE: Intentionally NOT writing to ChromaDB.
    # Context provided by the user is ephemeral and scoped to this execution only.
    return chunks
