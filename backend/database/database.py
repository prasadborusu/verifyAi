"""
Audit Database Module for Multi-Agent AI Reasoning & Verification Engine.
Stores tasks, agent executions, verification results, revision attempts, and decision audits in SQLite.
"""

import os
import sqlite3
import json
from datetime import datetime
from typing import Dict, Any, List, Optional
from dotenv import load_dotenv

load_dotenv()

DB_PATH = os.getenv("AUDIT_DB_PATH", "./audit.db")


def get_db_connection(db_path: str = DB_PATH) -> sqlite3.Connection:
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn


def init_db(db_path: str = DB_PATH) -> None:
    """Initializes tables for tasks and detailed audit logs."""
    os.makedirs(os.path.dirname(os.path.abspath(db_path)), exist_ok=True) if os.path.dirname(db_path) else None
    conn = get_db_connection(db_path)
    cursor = conn.cursor()

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS tasks (
        task_id TEXT PRIMARY KEY,
        original_question TEXT NOT NULL,
        final_decision TEXT NOT NULL,
        final_answer TEXT,
        confidence REAL,
        retry_count INTEGER DEFAULT 0,
        rejection_reason TEXT,
        duration_seconds REAL DEFAULT 0.0,
        planner_output TEXT,
        researcher_output TEXT,
        coder_output TEXT,
        verifier_output TEXT,
        critic_output TEXT,
        safety_output TEXT,
        finalizer_output TEXT,
        revision_history TEXT,
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL
    );
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS audit_logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        task_id TEXT NOT NULL,
        stage TEXT NOT NULL,
        agent TEXT NOT NULL,
        status TEXT NOT NULL,
        details TEXT,
        message TEXT,
        timestamp TEXT NOT NULL,
        FOREIGN KEY (task_id) REFERENCES tasks (task_id)
    );
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS documents_metadata (
        document_id TEXT PRIMARY KEY,
        filename TEXT NOT NULL,
        file_path TEXT,
        chunks_count INTEGER DEFAULT 0,
        created_at TEXT NOT NULL
    );
    """)

    conn.commit()
    conn.close()


def save_task_record(
    task_id: str,
    original_question: str,
    final_decision: str,
    final_answer: str,
    confidence: float,
    retry_count: int = 0,
    rejection_reason: Optional[str] = None,
    duration_seconds: float = 0.0,
    planner_output: Optional[Dict[str, Any]] = None,
    researcher_output: Optional[Dict[str, Any]] = None,
    coder_output: Optional[Dict[str, Any]] = None,
    verifier_output: Optional[Dict[str, Any]] = None,
    critic_output: Optional[Dict[str, Any]] = None,
    safety_output: Optional[Dict[str, Any]] = None,
    finalizer_output: Optional[Dict[str, Any]] = None,
    revision_history: Optional[List[Dict[str, Any]]] = None,
    db_path: str = DB_PATH,
) -> None:
    init_db(db_path)
    now = datetime.utcnow().isoformat()
    conn = get_db_connection(db_path)
    cursor = conn.cursor()

    cursor.execute("""
    INSERT OR REPLACE INTO tasks (
        task_id, original_question, final_decision, final_answer,
        confidence, retry_count, rejection_reason, duration_seconds,
        planner_output, researcher_output, coder_output, verifier_output,
        critic_output, safety_output, finalizer_output, revision_history,
        created_at, updated_at
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, COALESCE((SELECT created_at FROM tasks WHERE task_id = ?), ?), ?);
    """, (
        task_id,
        original_question,
        final_decision,
        final_answer,
        confidence,
        retry_count,
        rejection_reason or "",
        duration_seconds,
        json.dumps(planner_output) if planner_output else None,
        json.dumps(researcher_output) if researcher_output else None,
        json.dumps(coder_output) if coder_output else None,
        json.dumps(verifier_output) if verifier_output else None,
        json.dumps(critic_output) if critic_output else None,
        json.dumps(safety_output) if safety_output else None,
        json.dumps(finalizer_output) if finalizer_output else None,
        json.dumps(revision_history) if revision_history else "[]",
        task_id,
        now,
        now,
    ))

    conn.commit()
    conn.close()


def log_audit_event(
    task_id: str,
    stage: str,
    agent: str,
    status: str,
    details: Optional[Any] = None,
    message: str = "",
    db_path: str = DB_PATH,
) -> None:
    init_db(db_path)
    conn = get_db_connection(db_path)
    cursor = conn.cursor()
    if isinstance(details, (dict, list)):
        details_str = json.dumps(details)
    elif details is not None:
        details_str = json.dumps({"description": str(details)})
    else:
        details_str = json.dumps({})

    cursor.execute("""
    INSERT INTO audit_logs (task_id, stage, agent, status, details, message, timestamp)
    VALUES (?, ?, ?, ?, ?, ?, ?);
    """, (
        task_id,
        stage,
        agent,
        status,
        details_str,
        message,
        datetime.utcnow().isoformat(),
    ))
    conn.commit()
    conn.close()


def get_task_record(task_id: str, db_path: str = DB_PATH) -> Optional[Dict[str, Any]]:
    init_db(db_path)
    conn = get_db_connection(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM tasks WHERE task_id = ?", (task_id,))
    row = cursor.fetchone()
    conn.close()
    if not row:
        return None
    d = dict(row)
    for col in [
        "planner_output", "researcher_output", "coder_output",
        "verifier_output", "critic_output", "safety_output",
        "finalizer_output", "revision_history"
    ]:
        if d.get(col):
            try:
                d[col] = json.loads(d[col])
            except Exception:
                pass
    return d


def get_task_audit_trail(task_id: str, db_path: str = DB_PATH) -> List[Dict[str, Any]]:
    init_db(db_path)
    conn = get_db_connection(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM audit_logs WHERE task_id = ? ORDER BY id ASC", (task_id,))
    rows = cursor.fetchall()
    conn.close()
    results = []
    for r in rows:
        item = dict(r)
        if item.get("details"):
            try:
                item["details"] = json.loads(item["details"])
            except Exception:
                pass
        results.append(item)
    return results


def list_recent_tasks(limit: int = 50, db_path: str = DB_PATH) -> List[Dict[str, Any]]:
    init_db(db_path)
    conn = get_db_connection(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT task_id, original_question, final_decision, confidence, retry_count, created_at FROM tasks ORDER BY created_at DESC LIMIT ?", (limit,))
    rows = cursor.fetchall()
    conn.close()
    return [dict(r) for r in rows]


def save_document_metadata(
    document_id: str,
    filename: str,
    file_path: Optional[str] = None,
    chunks_count: int = 0,
    db_path: str = DB_PATH,
) -> None:
    init_db(db_path)
    conn = get_db_connection(db_path)
    cursor = conn.cursor()
    cursor.execute("""
    INSERT OR REPLACE INTO documents_metadata (document_id, filename, file_path, chunks_count, created_at)
    VALUES (?, ?, ?, ?, ?)
    """, (document_id, filename, file_path, chunks_count, datetime.utcnow().isoformat()))
    conn.commit()
    conn.close()


def get_document_by_id(document_id: str, db_path: str = DB_PATH) -> Optional[Dict[str, Any]]:
    init_db(db_path)
    conn = get_db_connection(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM documents_metadata WHERE document_id = ?", (document_id,))
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None


def get_document_by_filename(filename: str, db_path: str = DB_PATH) -> Optional[Dict[str, Any]]:
    init_db(db_path)
    conn = get_db_connection(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM documents_metadata WHERE filename = ? ORDER BY created_at DESC LIMIT 1", (filename,))
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None


def list_all_documents(db_path: str = DB_PATH) -> List[Dict[str, Any]]:
    init_db(db_path)
    conn = get_db_connection(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT document_id, filename, file_path, chunks_count, created_at FROM documents_metadata ORDER BY created_at DESC")
    rows = cursor.fetchall()
    conn.close()
    return [dict(r) for r in rows]

