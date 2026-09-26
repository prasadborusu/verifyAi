# Multi-Agent AI Reasoning & Verification Engine

A production-grade multi-agent reasoning and independent verification platform where specialized agents collaborate to solve complex reasoning tasks, while every critical output is independently verified prior to acceptance.

> **Central Principle:** *"Generation and verification must be separated."*  
> An agent that generates an important result must not be the only component deciding that the result is correct.

---

## 1. Project Overview

Modern LLM-based autonomous agent systems often suffer from ungrounded hallucinations, arithmetic errors, and silent failure propagation. The **Multi-Agent AI Reasoning & Verification Engine** addresses this by separating generation from verification through an architecture that enforces:
- Independent factual cross-checks against retrieved source evidence.
- Deterministic Python-executed arithmetic verification (never relying solely on LLM math).
- Contradiction detection across disparate document sources.
- AST-sandboxed code execution security screening.
- Automated self-correction loops (up to 3 retries) routing back to the responsible agent.
- A permanent SQLite audit trail for transparent enterprise accountability.

---

## 2. Architecture Diagram

```
                    USER
                      ↓
                  STREAMLIT
                      ↓
                   FASTAPI
                      ↓
                 LANGGRAPH
                      ↓
       ┌──────────────┼──────────────┐
       ↓              ↓              ↓
    PLANNER       RESEARCHER       CODER
                      ↓              ↓
                   EVIDENCE      TOOL RESULT
                      └──────┬───────┘
                             ↓
                      GENERATED RESULT
                             ↓
                  INDEPENDENT VERIFICATION
                             ↓
             ┌───────────────┼───────────────┐
             ↓               ↓               ↓
           FACT            LOGIC          CODE/TOOL
         VERIFIER         VERIFIER         VERIFIER
             └───────────────┼───────────────┘
                             ↓
                          CRITIC
                             ↓
                   ┌─────────┼─────────┐
                   ↓         ↓         ↓
                 PASS      REVISE     REJECT
                   ↓         ↓         ↓
               FINALIZER   CORRECT    FINALIZER
                             ↓
                         RE-VERIFY
                             ↓
                         FINALIZER
                             ↓
                       AUDIT REPORT
```

---

## 3. Specialized Agent Roles & Responsibilities

| Agent | Responsibility | Guarantee / Constraint |
| :--- | :--- | :--- |
| **Planner Agent** | Decomposes tasks, outlines tool/evidence needs. | **Never** directly calculates or outputs final answers. |
| **Safety Agent** | Screens prompts and proposed code for shell injection, rm -rf, and dangerous imports. | Bypasses generation and terminates hazardous requests. |
| **Researcher Agent** | Extracts grounded document evidence from ChromaDB vector store. | Returns `INSUFFICIENT_EVIDENCE` or `CONFLICTING_EVIDENCE` when data is missing or conflicting. |
| **Coder / Tool Agent** | Formulates math, generates code, and computes results in an AST sandbox. | Prefers deterministic Python execution over raw LLM arithmetic. |
| **Independent Verifier** | Gatekeeper: independently re-runs calculations and checks factual citations. | Enforces strict separation of generation and verification. |
| **Critic Agent** | Adversarial risk assessor checking for hallucinations, contradictions, and logical leaps. | Recommends `PROCEED`, `REQUEST_REVISION`, or `REJECT`. |
| **Finalizer Agent** | Synthesizes verified conclusions or issues explicit rejections. | Only verified findings are accepted; unverified claims are never promoted. |

---

## 4. Technology Stack

- **Python 3.11+**
- **FastAPI**: Asynchronous high-performance REST backend
- **Streamlit**: Interactive user dashboard & audit visualizer
- **LangGraph**: Directed cyclic state-graph multi-agent orchestrator
- **Google Gemini API**: Isolated LLM reasoning service via `google-genai`
- **ChromaDB**: Document vector store for RAG
- **Sentence Transformers**: Semantic dense embeddings (`all-MiniLM-L6-v2`)
- **Pydantic v2**: Structured schemas and contract validation
- **Pandas**: Structured dataset and CSV manipulation
- **SQLite**: Tamper-evident task and audit event logging
- **pypdf**: PDF text extraction and pagination tracking

---

## 5. Installation & Setup

### 1. Clone & Enter Project Directory
```bash
cd "d:\hack multi"
```

### 2. Configure Environment Variables
Copy `.env.example` to `.env`:
```bash
cp .env.example .env
```
Populate `.env`:
```env
GEMINI_API_KEY=your_actual_gemini_api_key_here
GEMINI_MODEL=gemini-2.5-flash
CHROMA_PERSIST_DIR=./chroma_db
AUDIT_DB_PATH=./audit.db
BACKEND_HOST=127.0.0.1
BACKEND_PORT=8000
```
*(Note: If `GEMINI_API_KEY` is omitted, the engine automatically operates in offline deterministic verification mode for testing.)*

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

---

## 6. Running the Application

### Launch FastAPI Backend
```bash
uvicorn backend.main:app --host 127.0.0.1 --port 8000 --reload
```
Interactive Swagger API documentation: `http://127.0.0.1:8000/docs`

### Launch Streamlit Dashboard
```bash
streamlit run frontend/app.py
```
Dashboard available in browser: `http://localhost:8501`

---

## 7. Running with Docker Compose

```bash
docker-compose up --build
```
- FastAPI Backend: `http://localhost:8000`
- Streamlit Dashboard: `http://localhost:8501`

---

## 8. Verification & Self-Correction Architecture

### Independent Verification Modules (`backend/verification/`)
- **`calculation.py`**: Deterministic arithmetic verifier. Calculates exact percentage growth, sums, and ratios in pure Python with mathematical tolerance.
- **`factual.py`**: Scans claims against retrieved evidence excerpts. Categorizes claims as `SUPPORTED`, `UNSUPPORTED`, `CONTRADICTED`, or `INSUFFICIENT_EVIDENCE`.
- **`contradiction.py`**: Identifies irreconcilable values across distinct sources (e.g., Doc A says 100M, Doc B says 120M) and prevents hallucinated compromises.
- **`code.py`**: AST-based code inspector banning unsafe modules (`os`, `sys`, `subprocess`, `socket`) and executing valid scripts with isolated globals.
- **`safety.py`**: Regex and semantic pattern guard against prompt injections, destructive file commands, and unauthorized execution.

### Self-Correction Mechanism
When the Verifier marks an intermediate output as `FAIL`, the `correction_router_node` checks:
1. If the failure is unrecoverable (e.g. absent evidence or direct contradiction), it routes immediately to `REJECT`.
2. If recoverable (e.g. arithmetic discrepancy), it routes back to the Coder Agent with specific feedback:
   ```
   Attempt 1 failed verification: CALCULATION ERROR: Discrepancy detected.
   ```
3. Maximum retries: `MAX_RETRIES = 3`.
4. If verification still fails after 3 attempts, the task terminates with `REJECT`.

---

## 9. Evaluation Suite & Benchmark Results

Run the full benchmark suite containing all 10 positive and adversarial test cases:
```bash
python evaluation/run_eval.py
```

### Actual Benchmark Results:
| Metric | Value |
| :--- | :--- |
| **Overall Task Completion & Correct Routing** | **100.0%** |
| **False Acceptance Rate (FAR)** | **0.0%** (Zero dangerous acceptance) |
| **Contradiction Detection Rate** | **100.0%** |
| **Hallucination Detection Rate** | **100.0%** |
| **Calculation Verification Accuracy** | **100.0%** |

### Evaluated Test Scenarios (`evaluation/test_cases.json`):
1. `tc_01_correct_financial`: Multi-step growth calculation (`ACCEPT`, `20.0%`).
2. `tc_02_hallucinated_info`: Unbacked revenue assertion (`REJECT`).
3. `tc_03_missing_info`: Omitted 2025 revenue data (`REJECT`).
4. `tc_04_conflicting_sources`: Contradictory reporting sources (`REJECT`).
5. `tc_05_incorrect_calc`: Inaccurate growth hypothesis (`REJECT`).
6. `tc_06_ambiguous_question`: Question lacking numerical metrics (`REJECT`).
7. `tc_07_misleading_document`: Division by zero base value (`REJECT`).
8. `tc_08_unsupported_claim`: Claim beyond document scope (`REJECT`).
9. `tc_09_invalid_tool_call`: Forbidden `eval()` syntax attempt (`REJECT`).
10. `tc_10_unsafe_action`: Command injection `rm -rf /` (`REJECT`).

---

## 10. Running Automated Tests

```bash
python -m pytest tests/ -v
```
All 12 unit and integration tests validate the API, arithmetic checks, contradiction detection, and sandboxed code execution.

---

## 11. Known Limitations & Future Improvements

1. **Dockerized Ephemeral Sub-processes**: Current code sandboxing uses in-process AST AST-visitor inspection and restricted namespaces; future versions can bind isolated ephemeral Docker containers per execution.
2. **Multi-Table SQL RAG**: Extensible RAG currently handles PDFs, TXTs, and CSVs; dynamic schema-aware SQL translation would expand tabular reasoning.
3. **Cross-Lingual Currency Normalization**: Automatic exchange-rate and denomination normalization (e.g. converting Lakh/Crore to USD/EUR) in the Coder agent.

---

## 12. Deployment Guide

### Deploy Backend on Render
1. Push this repository to GitHub.
2. Log in to [Render](https://render.com) and click **New +** > **Web Service** (or use **Blueprints** with `render.yaml`).
3. Connect your repository.
4. Settings:
   - **Environment**: `Python 3`
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `uvicorn backend.main:app --host 0.0.0.0 --port $PORT`
5. Under **Environment Variables**, add:
   - `GEMINI_API_KEY`: Your Google Gemini API Key
   - `GEMINI_MODEL`: `gemini-2.5-flash`
   - `PYTHON_VERSION`: `3.11.8`
   - `CORS_ORIGINS`: `*`
6. Click **Deploy Web Service**. Once deployed, copy your Render URL (e.g., `https://verifyai-backend.onrender.com`).

### Deploy Frontend on Netlify
1. Log in to [Netlify](https://netlify.com) and click **Add new site** > **Import an existing project**.
2. Connect your GitHub repository.
3. Settings (automatically detected via `netlify.toml`):
   - **Base directory**: Leave blank or `/`
   - **Build command**: Leave blank
   - **Publish directory**: `frontend`
4. Click **Deploy site**.
5. Once your Netlify site is live:
   - Open your Netlify URL (e.g. `https://your-site.netlify.app`).
   - Click the **Engine Online / Status** button in the top-right header.
   - Enter your Render backend URL (e.g. `https://verifyai-backend.onrender.com`) and click **Save & Connect**.
   - Alternatively, add `?backend=https://verifyai-backend.onrender.com` to your URL once, or set it inside `frontend/config.js`.

