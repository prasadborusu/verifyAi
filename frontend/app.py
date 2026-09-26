"""
Streamlit Frontend for VERIFAI: Multi-Agent AI Reasoning & Verification Engine.
Genuine ChatGPT-Style Conversational Interface with On-Demand Verification Laboratory.
Preserves 100% of existing backend capabilities, orchestration, database, and verification logic.
"""

import os
import sys
import json
import time
import uuid
import re
from datetime import datetime
import pandas as pd
import requests
import streamlit as st

# ==========================================
# PAGE CONFIGURATION
# ==========================================
st.set_page_config(
    page_title="VERIFAI | Multi-Agent AI Verification Engine",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Seamlessly redirect to the official polished ChatGPT-style VERIFAI frontend at http://127.0.0.1:8000/
st.markdown("""
<meta http-equiv="refresh" content="0; url=http://127.0.0.1:8000/">
<script>window.location.replace("http://127.0.0.1:8000/");</script>
<div style="font-family:'Inter',sans-serif;padding:30px;color:#10b981;background:#080b10;border-radius:12px;margin:20px 0;border:1px solid #1c2635;">
  <h3>Opening official VERIFAI frontend...</h3>
  <p style="color:#8392a5;">If you are not redirected automatically, <a href="http://127.0.0.1:8000/" style="color:#10b981;font-weight:700;">click here to open VERIFAI at http://127.0.0.1:8000/</a>.</p>
</div>
""", unsafe_allow_html=True)
st.stop()


# ==========================================
# CUSTOM CSS: CLEAN CHATGPT INTERFACE
# ==========================================
st.markdown("""
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&family=JetBrains+Mono:wght@400;500;600&display=swap">
<style>
    /* Hide Streamlit default chrome & headers */
    header[data-testid="stHeader"] {
        background-color: transparent !important;
        height: 0px !important;
        min-height: 0px !important;
        padding: 0 !important;
    }
    header[data-testid="stHeader"] [data-testid="stToolbar"] {
        display: none !important;
    }
    footer {
        display: none !important;
    }
    #MainMenu {
        display: none !important;
    }

    /* Core Canvas */
    .stApp {
        background-color: #0d1117 !important;
        color: #e6edf3 !important;
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
    }

    code, pre, .mono {
        font-family: 'JetBrains Mono', monospace !important;
    }

    /* Main Container Spacing */
    .block-container {
        padding-top: 1.5rem !important;
        padding-bottom: 6rem !important;
        padding-left: 2rem !important;
        padding-right: 2rem !important;
        max-width: 860px !important;
        margin: 0 auto !important;
    }

    /* ================= SIDEBAR ================= */
    section[data-testid="stSidebar"] {
        width: 260px !important;
        min-width: 260px !important;
        background-color: #161b22 !important;
        border-right: 1px solid #30363d !important;
    }
    section[data-testid="stSidebar"] > div:first-child {
        padding-top: 1.2rem !important;
        padding-left: 0.9rem !important;
        padding-right: 0.9rem !important;
    }

    .sb-brand {
        display: flex;
        align-items: center;
        gap: 0.6rem;
        padding-bottom: 1rem;
        margin-bottom: 0.8rem;
        border-bottom: 1px solid #21262d;
    }
    .sb-brand-logo {
        font-size: 1.5rem;
        line-height: 1;
    }
    .sb-brand-title {
        font-size: 1.2rem;
        font-weight: 800;
        letter-spacing: -0.02em;
        color: #ffffff;
        line-height: 1.1;
    }
    .sb-brand-sub {
        font-size: 0.72rem;
        color: #10b981;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.05em;
    }

    .sb-heading {
        font-size: 0.72rem;
        font-weight: 700;
        text-transform: uppercase;
        letter-spacing: 0.08em;
        color: #8b949e;
        margin: 1.2rem 0 0.5rem 0.2rem;
    }

    .sb-footer {
        padding-top: 1rem;
        border-top: 1px solid #21262d;
        margin-top: 2rem;
    }
    .sb-status-pill {
        display: inline-flex;
        align-items: center;
        gap: 0.45rem;
        padding: 0.25rem 0.65rem;
        border-radius: 9999px;
        font-size: 0.75rem;
        font-weight: 600;
        background: #21262d;
        border: 1px solid #30363d;
        color: #8b949e;
        margin-bottom: 0.4rem;
    }
    .dot-green {
        width: 7px;
        height: 7px;
        border-radius: 50%;
        background-color: #10b981;
        display: inline-block;
        box-shadow: 0 0 6px #10b981;
    }
    .dot-red {
        width: 7px;
        height: 7px;
        border-radius: 50%;
        background-color: #f85149;
        display: inline-block;
    }

    /* ================= WELCOME SCREEN ================= */
    .welcome-box {
        padding: 4rem 0 2rem 0;
        text-align: left;
    }
    .welcome-title {
        font-size: 2.5rem;
        font-weight: 800;
        letter-spacing: -0.03em;
        color: #ffffff;
        margin: 0 0 0.5rem 0;
        line-height: 1.15;
    }
    .welcome-tagline {
        font-size: 1.25rem;
        color: #c9d1d9;
        font-weight: 500;
        line-height: 1.4;
    }
    .welcome-tagline strong {
        color: #10b981;
        font-weight: 700;
    }

    /* ================= CHAT MESSAGES ================= */
    .chat-stream {
        display: flex;
        flex-direction: column;
        gap: 1.8rem;
        padding-top: 0.5rem;
    }

    /* User Message */
    .user-block {
        display: flex;
        flex-direction: column;
        align-items: flex-end;
    }
    .user-label {
        font-size: 0.78rem;
        font-weight: 700;
        color: #8b949e;
        margin-bottom: 0.25rem;
        padding-right: 0.2rem;
    }
    .user-bubble {
        background-color: #21262d;
        border: 1px solid #30363d;
        border-radius: 16px 16px 4px 16px;
        padding: 0.8rem 1.15rem;
        color: #f0f6fc;
        font-size: 0.95rem;
        line-height: 1.5;
        max-width: 82%;
    }
    .user-att-tag {
        display: inline-flex;
        align-items: center;
        gap: 0.4rem;
        background: rgba(16, 185, 129, 0.12);
        border: 1px solid rgba(16, 185, 129, 0.3);
        border-radius: 6px;
        padding: 0.18rem 0.45rem;
        font-size: 0.76rem;
        color: #34d399;
        font-weight: 600;
        margin-bottom: 0.4rem;
    }

    /* Assistant Message (Answer-First) */
    .assistant-block {
        display: flex;
        flex-direction: column;
        align-items: flex-start;
    }
    .assistant-label {
        display: flex;
        align-items: center;
        gap: 0.45rem;
        font-size: 0.82rem;
        font-weight: 700;
        color: #f0f6fc;
        margin-bottom: 0.5rem;
    }
    .assistant-logo {
        color: #10b981;
        font-size: 1rem;
    }

    .answer-hero {
        font-size: 2.1rem;
        font-weight: 800;
        letter-spacing: -0.02em;
        color: #10b981;
        line-height: 1.15;
        margin: 0.2rem 0 0.5rem 0;
    }
    .answer-hero.blocked {
        color: #e3b341;
    }
    .answer-hero.rejected {
        color: #f85149;
    }
    .answer-narrative {
        font-size: 0.96rem;
        color: #e6edf3;
        line-height: 1.6;
        margin-bottom: 0.8rem;
    }

    /* Verification Meta Row */
    .verif-meta-bar {
        display: flex;
        align-items: center;
        gap: 0.75rem;
        flex-wrap: wrap;
        padding: 0.55rem 0;
        border-top: 1px solid #21262d;
        margin-top: 0.3rem;
        margin-bottom: 0.5rem;
    }
    .badge-pass {
        display: inline-flex;
        align-items: center;
        gap: 0.35rem;
        padding: 0.18rem 0.65rem;
        border-radius: 9999px;
        font-size: 0.78rem;
        font-weight: 700;
        background: rgba(16, 185, 129, 0.12);
        color: #34d399;
        border: 1px solid rgba(16, 185, 129, 0.3);
    }
    .badge-warn {
        display: inline-flex;
        align-items: center;
        gap: 0.35rem;
        padding: 0.18rem 0.65rem;
        border-radius: 9999px;
        font-size: 0.78rem;
        font-weight: 700;
        background: rgba(227, 179, 65, 0.12);
        color: #e3b341;
        border: 1px solid rgba(227, 179, 65, 0.3);
    }
    .badge-fail {
        display: inline-flex;
        align-items: center;
        gap: 0.35rem;
        padding: 0.18rem 0.65rem;
        border-radius: 9999px;
        font-size: 0.78rem;
        font-weight: 700;
        background: rgba(248, 81, 73, 0.12);
        color: #f85149;
        border: 1px solid rgba(248, 81, 73, 0.3);
    }
    .meta-desc {
        font-size: 0.8rem;
        color: #8b949e;
        font-weight: 500;
    }

    /* Rejection Notice */
    .rejection-box {
        background: rgba(248, 81, 73, 0.08);
        border: 1px solid rgba(248, 81, 73, 0.3);
        border-radius: 8px;
        padding: 0.85rem 1rem;
        margin: 0.4rem 0 0.7rem 0;
    }
    .rejection-box-title {
        color: #f85149;
        font-weight: 700;
        font-size: 0.9rem;
        margin-bottom: 0.25rem;
    }
    .rejection-box-text {
        color: #c9d1d9;
        font-size: 0.88rem;
        line-height: 1.45;
    }

    /* ================= ATTACHMENT CHIP NEAR INPUT ================= */
    .active-chip-container {
        display: flex;
        align-items: center;
        justify-content: space-between;
        background: #161b22;
        border: 1px solid #30363d;
        border-bottom: none;
        border-radius: 10px 10px 0 0;
        padding: 0.5rem 0.9rem;
        margin-bottom: -1px;
    }
    .active-chip-left {
        display: flex;
        align-items: center;
        gap: 0.5rem;
        font-size: 0.85rem;
        color: #f0f6fc;
        font-weight: 600;
    }
    .active-chip-badge {
        font-size: 0.75rem;
        color: #10b981;
        background: rgba(16, 185, 129, 0.12);
        padding: 0.1rem 0.4rem;
        border-radius: 4px;
        font-weight: 600;
    }

    /* ================= VERIFICATION LAB ================= */
    .lab-banner {
        background: #161b22;
        border: 1px solid #30363d;
        border-radius: 12px;
        padding: 1.2rem;
        margin-bottom: 1.2rem;
    }
    .lab-banner-label {
        font-size: 0.75rem;
        font-weight: 700;
        color: #10b981;
        text-transform: uppercase;
        letter-spacing: 0.07em;
        margin-bottom: 0.3rem;
    }
    .lab-banner-q {
        font-size: 1.15rem;
        font-weight: 700;
        color: #ffffff;
        margin-bottom: 0.5rem;
    }
    .lab-banner-a {
        font-size: 0.95rem;
        color: #c9d1d9;
        line-height: 1.5;
    }

    /* 8-stage pipeline */
    .pipeline-wrapper {
        background: #0d1117;
        border: 1px solid #30363d;
        border-radius: 10px;
        padding: 1rem;
        margin-bottom: 1.2rem;
    }
    .pipeline-track {
        display: flex;
        align-items: center;
        justify-content: space-between;
        gap: 0.3rem;
        overflow-x: auto;
    }
    .pipe-node {
        flex: 1;
        min-width: 90px;
        padding: 0.55rem 0.35rem;
        background: #161b22;
        border: 1px solid #30363d;
        border-radius: 8px;
        text-align: center;
    }
    .pipe-node.done {
        background: rgba(16, 185, 129, 0.08);
        border-color: rgba(16, 185, 129, 0.35);
    }
    .pipe-node.blocked {
        background: rgba(248, 81, 73, 0.08);
        border-color: rgba(248, 81, 73, 0.35);
    }
    .pipe-node-step {
        font-size: 0.65rem;
        font-weight: 800;
        color: #8b949e;
    }
    .pipe-node.done .pipe-node-step { color: #10b981; }
    .pipe-node.blocked .pipe-node-step { color: #f85149; }
    .pipe-node-title {
        font-size: 0.78rem;
        font-weight: 700;
        color: #f0f6fc;
        margin: 0.1rem 0;
    }
    .pipe-node-sub {
        font-size: 0.68rem;
        color: #8b949e;
    }
    .pipe-arrow {
        color: #484f58;
        font-weight: 700;
        font-size: 0.85rem;
    }

    .contra-panel {
        display: grid;
        grid-template-columns: 1fr 1fr;
        gap: 0.9rem;
        margin: 0.7rem 0;
    }
    .contra-card {
        background: rgba(248, 81, 73, 0.05);
        border: 1px solid rgba(248, 81, 73, 0.3);
        border-radius: 8px;
        padding: 0.9rem;
    }
    .quote-box {
        background: #0d1117;
        border-left: 3px solid #10b981;
        padding: 0.5rem 0.8rem;
        border-radius: 0 6px 6px 0;
        font-size: 0.85rem;
        color: #c9d1d9;
        font-style: italic;
        margin-top: 0.4rem;
    }
</style>
""", unsafe_allow_html=True)


# ==========================================
# SESSION STATE INITIALIZATION
# ==========================================
if "messages" not in st.session_state:
    st.session_state["messages"] = []

if "current_chat_id" not in st.session_state:
    st.session_state["current_chat_id"] = str(uuid.uuid4())[:8]

if "saved_chats" not in st.session_state:
    st.session_state["saved_chats"] = {}

# Single source of truth for attachments
if "active_attachment" not in st.session_state:
    st.session_state["active_attachment"] = None

if "view" not in st.session_state:
    st.session_state["view"] = "chat"  # "chat" or "verification_lab"

if "active_task_for_lab" not in st.session_state:
    st.session_state["active_task_for_lab"] = None

if "backend_url" not in st.session_state:
    st.session_state["backend_url"] = "http://127.0.0.1:8000"

backend_url = st.session_state["backend_url"]


# ==========================================
# BACKEND HEALTH CHECK & DB RECENT TASKS
# ==========================================
backend_healthy = False
gemini_model = "gemini-2.5-flash"

try:
    health_resp = requests.get(f"{backend_url}/health", timeout=2)
    if health_resp.status_code == 200:
        backend_healthy = True
        h_json = health_resp.json()
        gemini_model = h_json.get("model", "gemini-2.5-flash")
except Exception:
    backend_healthy = False

db_recent_tasks = []
try:
    from backend.database.database import list_recent_tasks, get_task_record
    db_recent_tasks = list_recent_tasks(limit=20)
except Exception:
    pass


# ==========================================
# HELPER FUNCTIONS
# ==========================================
def clean_chat_title(query: str) -> str:
    """Format short readable title with clean emoji for sidebar."""
    q_low = query.lower()
    if any(k in q_low for k in ["phone", "ram", "price", "mobile"]):
        icon = "📊"
        fallback = "Phone Dataset Analysis"
    elif any(k in q_low for k in ["growth", "revenue", "lakh", "profit"]):
        icon = "💰"
        fallback = "Revenue Growth"
    elif any(k in q_low for k in ["*", "+", "-", "/", "calculate", "multiply", "math"]):
        icon = "🧮"
        fallback = "Deterministic Math"
    elif any(k in q_low for k in ["contradict", "conflict", "report a", "report b"]):
        icon = "🔍"
        fallback = "Contradiction Detection"
    else:
        icon = "💬"
        fallback = "Verification Query"

    first_line = query.strip().split("\n")[0]
    first_line = re.sub(r'^[^\w]+', '', first_line).strip()
    if not first_line:
        first_line = fallback
    elif len(first_line) > 26:
        first_line = first_line[:24] + "..."

    return f"{icon} {first_line}"


def parse_prominent_answer(final_answer: str, coder_res: any = None) -> tuple[str, str]:
    """Extract prominent metric (e.g. 18.96%, 1200) and narrative text."""
    if not final_answer:
        return ("", "")

    # Look for bold result like **18.96%** or **1200**
    bold_match = re.search(r'\*\*([^*]+)\*\*', final_answer)
    if bold_match and len(bold_match.group(1)) <= 40:
        hero = bold_match.group(1).strip()
        narrative = final_answer.split("### Verified Evidence Citations:")[0]
        narrative = narrative.split("### Verification Summary:")[0]
        narrative = narrative.split("### Verification Steps:")[0].strip()
        return (hero, narrative)

    if coder_res is not None and str(coder_res).strip():
        hero = str(coder_res).strip()
        narrative = final_answer.split("### Verified Evidence Citations:")[0]
        narrative = narrative.split("### Verification Summary:")[0]
        narrative = narrative.split("### Verification Steps:")[0].strip()
        return (hero, narrative)

    return ("", final_answer)


def get_attachment_info(file_name: str, file_path: str = None) -> dict:
    """Retrieve row count and metadata for attached file."""
    meta = {"type": "file", "name": file_name, "rows": None}
    if not file_path:
        docs_dir = os.path.abspath("./documents")
        file_path = os.path.join(docs_dir, file_name)

    if os.path.exists(file_path):
        meta["path"] = file_path
        if file_name.lower().endswith(".csv"):
            try:
                df = pd.read_csv(file_path)
                meta["rows"] = len(df)
            except Exception:
                pass
    return meta


def submit_query_workflow(task_text: str, attachment: dict = None):
    """
    Execute multi-agent verification using existing backend without modifying verification logic.
    Clears active attachment immediately after use so subsequent questions route normally.
    """
    clean_task = task_text.strip()
    if not clean_task:
        return

    doc_ids = []
    ctx_text = None
    att_meta = None

    # Automatic routing: dataset vs context vs general reasoning
    if attachment:
        if attachment.get("type") == "file":
            doc_ids = [attachment["name"]]
            att_meta = {
                "type": "file",
                "name": attachment["name"],
                "rows": attachment.get("rows"),
            }
        elif attachment.get("type") == "context":
            ctx_text = attachment.get("text")
            att_meta = {
                "type": "context",
                "name": attachment.get("name", "Direct Context"),
            }

    # Record User Message
    user_msg = {
        "id": f"msg_{uuid.uuid4().hex[:6]}",
        "role": "user",
        "content": clean_task,
        "attachment": att_meta,
    }
    st.session_state["messages"].append(user_msg)

    # Execute backend analysis
    with st.status("VERIFAI is verifying...", expanded=False):
        payload = {
            "task": clean_task,
            "context_text": ctx_text,
            "document_ids": doc_ids,
        }

        task_id = f"task_{uuid.uuid4().hex[:8]}"
        res_data = None
        success = False

        try:
            resp = requests.post(f"{backend_url}/analyze", json=payload, timeout=60)
            if resp.status_code == 200:
                res_data = resp.json()
                success = True
        except Exception:
            success = False

        if not success:
            try:
                from backend.orchestration.graph import run_multi_agent_workflow
                res_obj = run_multi_agent_workflow(
                    task_id=task_id,
                    task=clean_task,
                    context_text=ctx_text,
                    document_ids=doc_ids if doc_ids else None,
                )
                res_data = res_obj.model_dump()
                success = True
            except Exception as ex:
                res_data = {
                    "task_id": task_id,
                    "final_decision": "REJECT",
                    "final_answer": f"Execution halted: {str(ex)}",
                    "confidence": 0.0,
                    "duration_seconds": 0.0,
                    "contradiction_detected": False,
                    "audit_trail": [],
                }

    # Record Assistant Message
    assistant_msg = {
        "id": f"msg_{uuid.uuid4().hex[:6]}",
        "role": "assistant",
        "content": res_data.get("final_answer", ""),
        "task_id": res_data.get("task_id", task_id),
        "result": res_data,
        "attachment": att_meta,
    }
    st.session_state["messages"].append(assistant_msg)

    # Save to session chat list
    cid = st.session_state["current_chat_id"]
    st.session_state["saved_chats"][cid] = {
        "id": cid,
        "title": clean_chat_title(clean_task),
        "messages": list(st.session_state["messages"]),
    }

    # Clear active attachment immediately so subsequent questions are normal general reasoning
    st.session_state["active_attachment"] = None


# ==============================================================================
# SIDEBAR
# ==============================================================================
with st.sidebar:
    # 1. VERIFAI Brand
    st.markdown("""
    <div class="sb-brand">
        <span class="sb-brand-logo">🛡</span>
        <div>
            <div class="sb-brand-title">VERIFAI</div>
            <div class="sb-brand-sub">Proof & Verification Engine</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # 2. + New Chat Button (Completely resets state)
    if st.button("＋ New Chat", use_container_width=True, type="primary", key="sb_new_chat_btn"):
        st.session_state["messages"] = []
        st.session_state["current_chat_id"] = str(uuid.uuid4())[:8]
        st.session_state["active_attachment"] = None
        st.session_state["view"] = "chat"
        st.session_state["active_task_for_lab"] = None
        st.rerun()

    # 3. Recent Chats
    st.markdown('<div class="sb-heading">RECENT CHATS</div>', unsafe_allow_html=True)

    all_chats = []
    seen = set()

    # In-memory session chats
    for cid, cinfo in reversed(list(st.session_state["saved_chats"].items())):
        t_label = cinfo.get("title", "Conversation")
        all_chats.append({"id": cid, "title": t_label, "is_mem": True, "data": cinfo})
        seen.add(t_label)

    # Persistent SQLite past tasks
    for r in db_recent_tasks[:10]:
        q = r.get("original_question", "")
        f_title = clean_chat_title(q)
        if f_title not in seen:
            all_chats.append({"id": r.get("task_id"), "title": f_title, "is_mem": False, "task_id": r.get("task_id")})
            seen.add(f_title)

    if not all_chats:
        st.caption("No recent chats.")
    else:
        for c in all_chats[:7]:
            is_cur = (c["id"] == st.session_state.get("current_chat_id"))
            label = f"▸ {c['title']}" if is_cur else c["title"]
            if st.button(label, key=f"sb_chat_btn_{c['id']}", use_container_width=True):
                st.session_state["view"] = "chat"
                st.session_state["active_attachment"] = None
                if c.get("is_mem"):
                    st.session_state["current_chat_id"] = c["id"]
                    st.session_state["messages"] = list(c["data"]["messages"])
                else:
                    rec = get_task_record(c["task_id"])
                    if rec:
                        st.session_state["current_chat_id"] = c["task_id"]
                        st.session_state["messages"] = [
                            {"id": f"q_{c['task_id']}", "role": "user", "content": rec.get("original_question", ""), "attachment": None},
                            {"id": f"a_{c['task_id']}", "role": "assistant", "content": rec.get("final_answer", ""), "task_id": c["task_id"], "result": rec, "attachment": None},
                        ]
                st.rerun()

    # 4. Settings & Status at Bottom
    st.markdown('<div class="sb-footer">', unsafe_allow_html=True)

    dot_cls = "dot-green" if backend_healthy else "dot-red"
    dot_text = "Engine Online" if backend_healthy else "Offline"
    st.markdown(f"""
    <div>
        <span class="sb-status-pill">
            <span class="{dot_cls}"></span> {dot_text}
        </span>
    </div>
    """, unsafe_allow_html=True)

    with st.popover("⚙ Settings", use_container_width=True):
        st.markdown("**Backend Endpoint**")
        n_url = st.text_input("URL", value=backend_url, key="sb_pop_url")
        if n_url != backend_url:
            st.session_state["backend_url"] = n_url
            st.rerun()

        st.markdown("---")
        if st.button("🗑️ Clear History", key="sb_clear_history_btn", use_container_width=True):
            st.session_state["messages"] = []
            st.session_state["saved_chats"] = {}
            st.session_state["active_attachment"] = None
            st.rerun()

    st.markdown('</div>', unsafe_allow_html=True)


# ==============================================================================
# MAIN PAGE: CHAT (VIEW == 'chat')
# ==============================================================================
if st.session_state["view"] == "chat":

    # --- A. CLEAN WELCOME SCREEN (Only when messages list is empty) ---
    if not st.session_state["messages"]:
        st.markdown("""
        <div class="welcome-box">
            <h1 class="welcome-title">VERIFAI</h1>
            <div class="welcome-tagline">
                Don't just generate answers.<br>
                <strong>Verify them.</strong>
            </div>
        </div>
        """, unsafe_allow_html=True)

    # --- B. ACTUAL CONVERSATION (When messages exist) ---
    else:
        st.markdown('<div class="chat-stream">', unsafe_allow_html=True)

        for msg in st.session_state["messages"]:
            if msg["role"] == "user":
                # User message
                att = msg.get("attachment")
                att_badge = ""
                if att:
                    if att.get("type") == "file":
                        rows_str = f" • {att.get('rows')} rows" if att.get("rows") else ""
                        att_badge = f'<div class="user-att-tag">📄 {att.get("name")}{rows_str}</div>'
                    else:
                        att_badge = f'<div class="user-att-tag">📝 {att.get("name")}</div>'

                st.markdown(f"""
                <div class="user-block">
                    <div class="user-label">User</div>
                    <div class="user-bubble">
                        {att_badge}
                        <div>{msg['content']}</div>
                    </div>
                </div>
                """, unsafe_allow_html=True)

            else:
                # Assistant message (Answer-First)
                res = msg.get("result", {})
                decision = res.get("final_decision", "ACCEPT")
                confidence = res.get("confidence", 0.0)
                coder_val = (res.get("coder_output") or {}).get("execution_result")
                hero_val, narrative = parse_prominent_answer(msg["content"], coder_val)

                is_contra = res.get("contradiction_detected", False)
                unresolved = (res.get("contradiction_report") or {}).get("unresolved_contradictions", [])
                has_conflict = bool(is_contra or unresolved)

                # Determine badge styling
                if decision == "ACCEPT":
                    b_cls = "badge-pass"
                    b_txt = "✓ Verified"
                    h_cls = ""
                elif has_conflict or decision in ["BLOCKED", "NEEDS_CLARIFICATION"]:
                    b_cls = "badge-warn"
                    b_txt = "⚠ Verification required"
                    h_cls = "blocked"
                else:
                    b_cls = "badge-fail"
                    b_txt = "⛔ Rejected"
                    h_cls = "rejected"

                # Show source file pill ONLY if this query actually used an attachment
                src_pill = ""
                if msg.get("attachment") and msg["attachment"].get("name"):
                    src_pill = f'<span class="meta-desc">📊 {msg["attachment"]["name"]}</span>'

                st.markdown("""
                <div class="assistant-block">
                    <div class="assistant-label">
                        <span class="assistant-logo">🛡</span> VERIFAI
                    </div>
                """, unsafe_allow_html=True)

                if has_conflict or decision in ["BLOCKED", "NEEDS_CLARIFICATION"]:
                    st.markdown("""
                    <div class="rejection-box">
                        <div class="rejection-box-title">⚠ Verification required</div>
                        <div class="rejection-box-text">
                            VERIFAI could not safely accept an answer because the supplied sources contain conflicting values.
                        </div>
                    </div>
                    """, unsafe_allow_html=True)
                elif hero_val:
                    st.markdown(f'<div class="answer-hero {h_cls}">{hero_val}</div>', unsafe_allow_html=True)

                if narrative:
                    st.markdown(f'<div class="answer-narrative">{narrative}</div>', unsafe_allow_html=True)

                st.markdown(f"""
                    <div class="verif-meta-bar">
                        <span class="{b_cls}">{b_txt}</span>
                        <span class="meta-desc">{confidence * 100:.0f}% confidence</span>
                        {src_pill}
                    </div>
                """, unsafe_allow_html=True)

                # 'View verification →' button
                if st.button("View verification →", key=f"btn_lab_view_{msg['id']}"):
                    st.session_state["active_task_for_lab"] = res
                    st.session_state["view"] = "verification_lab"
                    st.rerun()

                st.markdown('</div>', unsafe_allow_html=True)

        st.markdown('</div>', unsafe_allow_html=True)

    # --- C. CHATGPT-STYLE BOTTOM INPUT & ATTACHMENT BAR ---
    # Attachment Chip: ONLY rendered right above input if active_attachment exists
    active_att = st.session_state.get("active_attachment")
    if active_att:
        c_chip, c_del = st.columns([0.88, 0.12])
        with c_chip:
            if active_att["type"] == "file":
                r_tag = f'<span class="active-chip-badge">{active_att.get("rows")} rows</span>' if active_att.get("rows") else ""
                st.markdown(f"""
                <div class="active-chip-container">
                    <div class="active-chip-left">
                        <span>📄</span> <span>{active_att.get('name')}</span> {r_tag}
                    </div>
                </div>
                """, unsafe_allow_html=True)
            else:
                st.markdown(f"""
                <div class="active-chip-container">
                    <div class="active-chip-left">
                        <span>📝</span> <span>{active_att.get('name', 'Direct Context')}</span>
                        <span class="active-chip-badge">Context attached</span>
                    </div>
                </div>
                """, unsafe_allow_html=True)
        with c_del:
            if st.button("× Remove", key="btn_remove_active_attachment"):
                st.session_state["active_attachment"] = None
                st.rerun()

    # Input Row: "+" attachment popover button + Streamlit chat_input
    col_plus, col_input = st.columns([0.08, 0.92])

    with col_plus:
        with st.popover("＋", help="Attach file, dataset, or context"):
            st.markdown("**Add to Conversation**")

            p_tabs = st.tabs(["📊 Choose Dataset", "📎 Upload File", "📝 Add Context"])

            with p_tabs[0]:
                st.caption("Available datasets:")
                datasets = [
                    ("Mobile-Price-Prediction-cleaned_data.csv", "807 rows • Mobile specs & prices"),
                    ("sample_financial_report_2025.txt", "Annual financial metrics"),
                    ("sample_quarterly_filing.csv", "Quarterly operational results"),
                    ("webscraper-io-2026-01-21.csv", "E-commerce scraped records"),
                ]
                for d_name, d_desc in datasets:
                    if st.button(f"📊 {d_name}\n({d_desc})", key=f"sel_ds_{d_name}", use_container_width=True):
                        st.session_state["active_attachment"] = get_attachment_info(d_name)
                        st.rerun()

            with p_tabs[1]:
                uploaded_file = st.file_uploader(
                    "Upload file (CSV, TXT, PDF):",
                    type=["csv", "txt", "pdf"],
                    key="popover_file_upload",
                )
                if uploaded_file is not None:
                    docs_dir = os.path.abspath("./documents")
                    os.makedirs(docs_dir, exist_ok=True)
                    f_dest = os.path.join(docs_dir, uploaded_file.name)
                    with open(f_dest, "wb") as f:
                        f.write(uploaded_file.getbuffer())
                    st.session_state["active_attachment"] = get_attachment_info(uploaded_file.name, f_dest)
                    st.success(f"Attached {uploaded_file.name}")
                    st.rerun()

            with p_tabs[2]:
                st.caption("Direct context text:")
                pasted_ctx = st.text_area("Content:", height=90, placeholder="Paste excerpts, financial notes, or claims...", key="popover_ctx_area")
                if st.button("Attach Context", key="btn_apply_ctx", type="primary"):
                    if pasted_ctx.strip():
                        st.session_state["active_attachment"] = {
                            "type": "context",
                            "name": "Direct Context",
                            "text": pasted_ctx.strip(),
                        }
                        st.rerun()

    with col_input:
        user_text = st.chat_input("Ask anything...", key="chat_input_field")

    if user_text:
        submit_query_workflow(user_text, st.session_state.get("active_attachment"))
        st.rerun()


# ==============================================================================
# SECOND PAGE: DEDICATED VERIFICATION LAB (VIEW == 'verification_lab')
# ==============================================================================
elif st.session_state["view"] == "verification_lab":

    res = st.session_state.get("active_task_for_lab") or {}
    t_id = res.get("task_id", "N/A")
    dec = res.get("final_decision", "ACCEPT")
    conf = res.get("confidence", 0.0)
    lat = res.get("duration_seconds", 0.0)

    p_out = res.get("planner_output") or {}
    s_out = res.get("safety_output") or {}
    r_out = res.get("researcher_output") or {}
    c_out = res.get("coder_output") or {}
    v_out = res.get("verifier_output") or {}
    crit_out = res.get("critic_output") or {}
    final_out = res.get("finalizer_output") or {}
    audit_trail = res.get("audit_trail") or []
    rev_hist = res.get("revision_history") or []

    c_rep = res.get("contradiction_report") or r_out.get("contradiction_report") or {}
    unres = c_rep.get("unresolved_contradictions", [])
    has_conflict = bool(unres or res.get("contradiction_detected"))

    # Top Row: ← Back to Chat button & status
    t1, t2 = st.columns([0.25, 0.75])
    with t1:
        if st.button("← Back to Chat", key="btn_back_to_chat"):
            st.session_state["view"] = "chat"
            st.rerun()

    with t2:
        dec_tag = "✓ VERIFIED" if dec == "ACCEPT" else f"⛔ {dec}"
        st.markdown(f"""
        <div style="display: flex; justify-content: flex-end; align-items: center; gap: 0.8rem;">
            <span class="sb-status-pill">Task: <strong style="color: #f0f6fc;">{t_id}</strong></span>
            <span class="sb-status-pill">Status: <strong style="color: #34d399;">{dec_tag}</strong></span>
            <span class="sb-status-pill">Confidence: <strong style="color: #34d399;">{conf * 100:.1f}%</strong></span>
            <span class="sb-status-pill">Latency: <strong style="color: #38bdf8;">{lat}s</strong></span>
        </div>
        """, unsafe_allow_html=True)

    # Verification Banner
    st.markdown(f"""
    <div class="lab-banner">
        <div class="lab-banner-label">INTERACTIVE VERIFICATION LABORATORY</div>
        <div class="lab-banner-q">"{res.get('current_query') or res.get('original_question') or 'Verification Query'}"</div>
        <div class="lab-banner-a">{res.get('final_answer', '')}</div>
    </div>
    """, unsafe_allow_html=True)

    # 8-Stage Pipeline Track
    s_q = "done"
    s_p = "done" if p_out else ""
    s_r = "done" if r_out else ""
    s_c = ("blocked" if has_conflict else "done") if c_out else ""
    s_v = ("blocked" if dec in ["REJECT", "BLOCKED"] else "done") if v_out else ""
    s_crit = "done" if crit_out else ""
    s_corr = ("done" if len(rev_hist) > 0 else "skipped")
    s_dec = ("blocked" if dec in ["REJECT", "BLOCKED"] else "done")

    st.markdown(f"""
    <div class="pipeline-wrapper">
        <div style="font-size: 0.75rem; font-weight: 700; color: #8b949e; text-transform: uppercase; margin-bottom: 0.7rem;">
            Multi-Agent Verification Pipeline Flow
        </div>
        <div class="pipeline-track">
            <div class="pipe-node {s_q}">
                <div class="pipe-node-step">01</div>
                <div class="pipe-node-title">QUESTION</div>
                <div class="pipe-node-sub">Input</div>
            </div>
            <div class="pipe-arrow">→</div>
            <div class="pipe-node {s_p}">
                <div class="pipe-node-step">02</div>
                <div class="pipe-node-title">PLANNER</div>
                <div class="pipe-node-sub">Decompose</div>
            </div>
            <div class="pipe-arrow">→</div>
            <div class="pipe-node {s_r}">
                <div class="pipe-node-step">03</div>
                <div class="pipe-node-title">RESEARCH</div>
                <div class="pipe-node-sub">Grounding</div>
            </div>
            <div class="pipe-arrow">→</div>
            <div class="pipe-node {s_c}">
                <div class="pipe-node-step">04</div>
                <div class="pipe-node-title">CODER</div>
                <div class="pipe-node-sub">Sandbox</div>
            </div>
            <div class="pipe-arrow">→</div>
            <div class="pipe-node {s_v}">
                <div class="pipe-node-step">05</div>
                <div class="pipe-node-title">VERIFIER</div>
                <div class="pipe-node-sub">Gatekeeper</div>
            </div>
            <div class="pipe-arrow">→</div>
            <div class="pipe-node {s_crit}">
                <div class="pipe-node-step">06</div>
                <div class="pipe-node-title">CRITIC</div>
                <div class="pipe-node-sub">Adversarial</div>
            </div>
            <div class="pipe-arrow">→</div>
            <div class="pipe-node {s_corr}">
                <div class="pipe-node-step">07</div>
                <div class="pipe-node-title">CORRECT</div>
                <div class="pipe-node-sub">{len(rev_hist)}/3 Retries</div>
            </div>
            <div class="pipe-arrow">→</div>
            <div class="pipe-node {s_dec}">
                <div class="pipe-node-step">08</div>
                <div class="pipe-node-title">FINALIZER</div>
                <div class="pipe-node-sub">{dec}</div>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # Detailed Verification Tabs
    lab_tabs = st.tabs([
        "🧮 Deterministic Sandbox",
        "📚 Evidence & Provenance",
        "🛡️ Independent Verification",
        "🤖 Agent Ensemble Trace",
        "📜 System Audit Trail",
        "🛠️ Raw JSON Contract",
    ])

    # Tab 1: Deterministic Sandbox
    with lab_tabs[0]:
        st.markdown("#### 🧮 Deterministic Python Sandbox Execution")
        st.caption("Executes logic in an isolated Python runtime to guarantee zero hallucinated mathematics.")

        if has_conflict:
            st.markdown("""
            <div style="background: rgba(248, 81, 73, 0.08); border: 1px solid rgba(248, 81, 73, 0.3); border-radius: 8px; padding: 0.85rem; color: #f85149;">
                ⛔ <strong>Sandbox Execution Halted:</strong> Conflicting candidate values detected. Computation suspended to prevent arbitrary guessing.
            </div>
            """, unsafe_allow_html=True)
        else:
            calc_val = c_out.get("execution_result")
            sc1, sc2 = st.columns([0.4, 0.6])
            with sc1:
                st.metric("Deterministic Output", str(calc_val) if calc_val is not None else "N/A")
                st.markdown(f"**Rationale:** {c_out.get('explanation', 'Deterministic evaluation')}")
                if c_out.get("inputs"):
                    st.markdown("**Bound Parameters:**")
                    st.json(c_out.get("inputs"))
            with sc2:
                c_code = c_out.get("code")
                if c_code:
                    st.markdown("**Executed Sandbox Script:**")
                    st.code(c_code, language="python")
                else:
                    st.info("Task resolved via qualitative verification.")

    # Tab 2: Evidence & Grounding
    with lab_tabs[1]:
        st.markdown("#### 📚 Grounded Evidence Provenance")
        st.caption("Extracted claims, page citations, and cross-source consistency validation.")

        # Side-by-side contradiction panels
        if unres:
            st.markdown("##### ⚔️ Cross-Source Contradictions (Side-by-Side Isolation)")
            for u in unres:
                u_ent = u.get("canonical_entity") or u.get("entity", "Metric")
                claims = u.get("claims", [])
                st.markdown(f"**Conflicting Entity:** `{u_ent}`")

                if len(claims) >= 2:
                    st.markdown(f"""
                    <div class="contra-panel">
                        <div class="contra-card">
                            <span class="badge-fail">Source A</span>
                            <h4 style="margin: 6px 0; color: #f85149;">{claims[0].get('source_name', 'Source A')}</h4>
                            <p style="margin: 0; color: #c9d1d9;">Value: <strong>{claims[0].get('value') or claims[0].get('extracted_value')} {claims[0].get('unit') or ''}</strong></p>
                            <div class="quote-box">"{claims[0].get('excerpt', '')}"</div>
                        </div>
                        <div class="contra-card">
                            <span class="badge-fail">Source B</span>
                            <h4 style="margin: 6px 0; color: #f85149;">{claims[1].get('source_name', 'Source B')}</h4>
                            <p style="margin: 0; color: #c9d1d9;">Value: <strong>{claims[1].get('value') or claims[1].get('extracted_value')} {claims[1].get('unit') or ''}</strong></p>
                            <div class="quote-box">"{claims[1].get('excerpt', '')}"</div>
                        </div>
                    </div>
                    """, unsafe_allow_html=True)

        ev_items = r_out.get("evidence_items", [])
        if ev_items:
            for idx, ev in enumerate(ev_items):
                st.markdown(f"""
                <div style="background: #161b22; border: 1px solid #30363d; border-radius: 8px; padding: 0.85rem; margin-bottom: 0.6rem;">
                    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.3rem;">
                        <strong>Source #{idx+1}: {ev.get('source', 'Document')}</strong>
                        <span class="badge-pass">{ev.get('verification_status', 'VERIFIED')}</span>
                    </div>
                    <div style="color: #f0f6fc; font-weight: 600; margin-bottom: 0.3rem;">{ev.get('claim')}</div>
                    <div class="quote-box">"{ev.get('evidence')}"</div>
                    <div style="font-size: 0.78rem; color: #8b949e; margin-top: 0.4rem;">
                        Entity: <code>{ev.get('normalized_claim', 'N/A')}</code> &nbsp;|&nbsp; Page: {ev.get('page', 1)} &nbsp;|&nbsp; Confidence: {ev.get('confidence', 1.0)}
                    </div>
                </div>
                """, unsafe_allow_html=True)
        elif r_out.get("status") == "EVIDENCE_NOT_REQUIRED":
            st.info("ℹ️ External evidence not required: Self-contained arithmetic problem verified via Python sandbox.")

    # Tab 3: Independent Verification Checks
    with lab_tabs[2]:
        st.markdown("#### 🛡️ Independent Verification Checks")
        st.caption("Zero Blind Faith: Validation of arithmetic equations, factual claims, and citation fidelity.")

        v_reason = v_out.get("reason", "Verification passed")
        st.markdown(f"**Gatekeeper Verdict:** {v_reason}")

        checks = v_out.get("checks", [])
        if checks:
            for chk in checks:
                passed = chk.get("passed", False)
                chk_badge = '<span class="badge-pass">✓ PASS</span>' if passed else '<span class="badge-fail">⛔ FAIL</span>'
                st.markdown(f"""
                <div style="display: flex; justify-content: space-between; align-items: center; padding: 0.6rem 0; border-bottom: 1px solid #21262d;">
                    <div>
                        <strong>[{chk.get('check_type', '').upper()}] {chk.get('check_name')}</strong>
                        <div style="font-size: 0.8rem; color: #8b949e; margin-top: 0.15rem;">{chk.get('details')}</div>
                    </div>
                    <div>{chk_badge}</div>
                </div>
                """, unsafe_allow_html=True)

    # Tab 4: Agent Ensemble Trace
    with lab_tabs[3]:
        st.markdown("#### 🤖 Specialized Multi-Agent Trace")

        agents = [
            ("Planner Agent", p_out.get("task_type", "Planned"), f"{len(p_out.get('subtasks', []))} subtasks formulated", "COMPLETED"),
            ("Safety Agent", s_out.get("risk_level", "SAFE"), s_out.get("reason", "Passed security checks"), "PASS" if s_out.get("is_safe", True) else "BLOCKED"),
            ("Researcher Agent", r_out.get("status", "FOUND"), f"{len(ev_items)} grounded claims cataloged", "PASS"),
            ("Coder Sandbox", "Deterministic Execution", f"Output: {c_out.get('execution_result', 'N/A')}", "BLOCKED" if has_conflict else "PASS"),
            ("Independent Verifier", v_out.get("status", "PASS"), f"Action: {v_out.get('recommended_action', 'ACCEPT')}", v_out.get("status", "PASS")),
            ("Critic Agent", f"Risk score: {crit_out.get('risk_score', 0.0)}", crit_out.get("recommendation", "PROCEED"), "PASS"),
            ("Self-Correction Loop", f"{len(rev_hist)}/3 retries", "Remediated" if len(rev_hist) > 0 else "Clean on First Pass", "PASS"),
            ("Finalizer Agent", dec, f"Final confidence: {conf*100:.1f}%", dec),
        ]

        for aname, role, details, stat in agents:
            st.markdown(f"""
            <div style="background: #161b22; border: 1px solid #30363d; border-radius: 8px; padding: 0.75rem 1rem; margin-bottom: 0.5rem; display: flex; justify-content: space-between; align-items: center;">
                <div>
                    <div style="font-size: 0.88rem; font-weight: 700; color: #f0f6fc;">{aname}</div>
                    <div style="font-size: 0.78rem; color: #8b949e;">{role} &nbsp;•&nbsp; {details}</div>
                </div>
                <div><span class="sb-status-pill">{stat}</span></div>
            </div>
            """, unsafe_allow_html=True)

    # Tab 5: System Audit Trail
    with lab_tabs[4]:
        st.markdown("#### 📜 System Event Timeline & SQLite Audit Trail")
        st.caption("Chronological event logs with millisecond timestamps stored permanently in SQLite.")

        if audit_trail:
            df_a = pd.DataFrame(audit_trail)
            cols = [c for c in ["timestamp", "stage", "agent", "status", "message"] if c in df_a.columns]
            st.dataframe(df_a[cols], use_container_width=True)
        else:
            st.info("No audit logs captured for this task.")

    # Tab 6: Raw JSON Response Contract
    with lab_tabs[5]:
        st.markdown("#### 🛠️ API Response Contract Payload")
        st.caption("Exact structured JSON payload returned by the multi-agent backend.")
        st.json(res)
