# 🚀 Enterprise AI Onboarding & Compliance Accelerator (Agentic LMS)

[![Python](https://img.shields.io/badge/Python-3.12%2B-blue?style=for-the-badge&logo=python&logoColor=white)](https://www.python.org/)
[![LangGraph](https://img.shields.io/badge/Orchestration-LangGraph_1.1.10-orange?style=for-the-badge)](https://github.com/langchain-ai/langgraph)
[![Gemini](https://img.shields.io/badge/LLM-Google_Gemini_3_Flash-red?style=for-the-badge&logo=google-gemini&logoColor=white)](https://ai.google.dev/)
[![FastAPI](https://img.shields.io/badge/API-FastAPI_0.136-green?style=for-the-badge&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![React](https://img.shields.io/badge/Frontend-React_19-61DAFB?style=for-the-badge&logo=react&logoColor=black)](https://react.dev/)
[![Langfuse](https://img.shields.io/badge/Observability-Langfuse_4.6-black?style=for-the-badge)](https://langfuse.com/)
[![ChromaDB](https://img.shields.io/badge/VectorDB-ChromaDB_1.5.9-purple?style=for-the-badge)](https://www.trychroma.com/)

> **Standardizing Enterprise Onboarding through Agentic Workflows, Flow Engineering, and Human-in-the-Loop Certification.**

A **production-grade multi-agent system** that transforms static company SOPs into an interactive, AI-driven learning experience. Powered by **LangGraph** for cyclic state-machine orchestration, **Agentic RAG** for hallucination-free knowledge retrieval, and **Human-in-the-Loop (HITL)** interrupts for supervisor-verified certification.

---

## Table of Contents

- [The Problem & Vision](#-the-problem--vision)
- [System Architecture](#-system-architecture)
- [Multi-Agent Ecosystem](#-multi-agent-ecosystem)
- [LangGraph Workflow & Flow Engineering](#-langgraph-workflow--flow-engineering)
- [RAG Ingestion Pipeline](#-rag-ingestion-pipeline)
- [API Layer (FastAPI + SSE Streaming)](#-api-layer-fastapi--sse-streaming)
- [Frontend (React 19 + Vite)](#-frontend-react-19--vite)
- [Observability & Evaluation](#-observability--evaluation)
- [Tech Stack](#-tech-stack)
- [Project Structure](#-project-structure)
- [Getting Started](#-getting-started)
- [Testing](#-testing)
- [Deployment](#-deployment)
- [Roadmap](#-roadmap)

---

## 🎯 The Problem & Vision

Traditional enterprise onboarding involves reading hundreds of pages of static PDFs — leading to **low engagement**, **poor knowledge retention**, and **compliance risks**. This project reimagines onboarding as a **conversational journey** where AI agents don't just "show" information, but **teach**, **assess**, and **certify** understanding in real-time.

### The 4C Onboarding Framework

The system is architected around the industry-standard **4C Framework**:

| Pillar | Implementation |
|:---|:---|
| **Compliance** | Automated teaching of legal/administrative SOPs (AML/KYC, GDPR, IT Security) |
| **Clarification** | Role-specific KPI alignment and technical expectation setting |
| **Culture** | Immersive introduction to company vision and core values |
| **Connection** | Guided integration into team workflows and internal tools |

---

## 🏗️ System Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                        FRONTEND (React 19 + Vite)                   │
│  SetupScreen → ChatWindow (SSE) → Sidebar → SupervisorModal        │
│  Langfuse Web SDK (OpenTelemetry) for client-side tracing           │
└──────────────────────────────┬──────────────────────────────────────┘
                               │ HTTP / SSE
┌──────────────────────────────▼──────────────────────────────────────┐
│                      API LAYER (FastAPI 0.136)                      │
│  POST /sessions          → Create session (Planner runs)            │
│  POST /sessions/{id}/chat → SSE-streamed multi-agent response       │
│  GET  /sessions/{id}/status → Session progress                      │
│  POST /sessions/{id}/approve → HITL supervisor approval             │
│  POST /sessions/{id}/reject  → HITL supervisor rejection            │
│  POST /sessions/{id}/feedback → Langfuse user feedback              │
│  POST /documents/ingest  → RAG document ingestion                   │
└──────────────────────────────┬──────────────────────────────────────┘
                               │
┌──────────────────────────────▼──────────────────────────────────────┐
│                   LANGGRAPH STATE MACHINE                           │
│                                                                     │
│  __start__ → planner_node → END (await user input)                  │
│                               ↓                                     │
│                         route_intent (LLM classifier)               │
│                        /        |          \                         │
│                 explainer   assessor    status_node                  │
│                    ↓           ↓           ↓                        │
│                   END      grade_check    END                       │
│                           /          \                               │
│                     fail→END    pass→advance_topic                   │
│                                        ↓                            │
│                                   topic_check                       │
│                                  /          \                        │
│                           more→END    all_done→[HITL]→certifier→END │
└──────────────────────────────┬──────────────────────────────────────┘
                               │
┌──────────────────────────────▼──────────────────────────────────────┐
│                     PERSISTENCE & KNOWLEDGE                         │
│  ChromaDB (Vector Store)  │  SQLite/PostgreSQL (Checkpointer)       │
│  Gemini Embeddings        │  Session state across restarts          │
│  17 SOP documents indexed │  HITL interrupt persistence             │
└─────────────────────────────────────────────────────────────────────┘
```

---

## 🤖 Multi-Agent Ecosystem

### Agent Inventory

| Agent | File | Responsibility | Pattern |
|:---|:---|:---|:---|
| **🧭 Router** | `agents/router.py` | LLM-based intent classification into `learn`/`quiz`/`status` | Structured Output (`RouterDecision`) |
| **📋 Planner** | `agents/planner.py` | Generates personalized syllabus (3–5 topics) based on employee role | Structured Output (`SyllabusOutput`) |
| **📚 Explainer** | `agents/explainer.py` | RAG-powered tutoring grounded in company SOPs | ReAct Agent (`create_react_agent`) |
| **⚖️ Assessor** | `agents/assessor.py` | Case-study quiz generation + LLM-as-a-Judge grading | ReAct Agent + Tool Calls |
| **📊 Status** | `agents/status.py` | Visual progress report with progress bar and topic tracking | Pure function (no LLM) |
| **🎓 Certifier** | `agents/certifier.py` | Issues compliance certificate after HITL approval | Pure function (no LLM) |

### Agent Details

#### Router Agent — Intent Classification
- Uses **LLM structured output** (`with_structured_output(RouterDecision)`) to classify every user message into one of three intents.
- **Assessor Context Guard**: A state-based short-circuit that prevents quiz answers from being misclassified as "learn" intent. When `current_agent == "assessor_node"` and the current topic hasn't been graded yet, the router bypasses LLM classification and returns `"quiz"` directly.

#### Explainer Agent — RAG Tutor
- Built as a **LangChain ReAct sub-agent** using `create_react_agent()` with a dynamic `state_modifier` that injects the current topic and role into the system prompt.
- Uses the `retrieve_internal_policies` tool for **MMR (Maximal Marginal Relevance)** search — balancing relevance with diversity to avoid redundant chunks.
- **Guardrails**: Explicitly instructed to never grade quiz answers (anti-role-confusion prompt) and to politely decline off-topic questions.

#### Assessor Agent — LLM-as-a-Judge
- Generates practical, case-study style quiz questions using retrieved SOP context.
- Grades answers using a structured rubric (`generate_evaluation_rubric` tool) with three tiers: Pass (≥80), Needs Review (50–79), Fail (<50).
- Submits grades via a `submit_grade` tool call — the wrapper node (`assessor_node`) intercepts the tool call arguments to extract score/feedback and update graph state.
- **Module-level caching**: Agent instance is cached after first creation to avoid re-initializing LLM + sub-graph per invocation.

### Agent Tools (`agents/tools.py`)

| Tool | Used By | Description |
|:---|:---|:---|
| `retrieve_internal_policies` | Explainer, Assessor | MMR semantic search on ChromaDB (top-5, fetch_k=20) with source attribution |
| `generate_evaluation_rubric` | Assessor | Generates structured grading criteria for a given topic |
| `submit_grade` | Assessor | Dummy tool for LLM to call — actual state update happens in wrapper node |
| `retrieve_documents_with_scores` | Evaluation pipeline | Utility function (not a LangChain tool) for debugging retrieval quality |

---

## 🔄 LangGraph Workflow & Flow Engineering

### Core Design: Multi-Turn Conversation Pattern

Unlike simple linear chains, this system uses a **cyclic state graph** where each node returns to `END`, waiting for the next user message. The graph is re-invoked with the same `thread_id`, resuming from the persisted checkpoint.

### Graph State (`OnboardingState`)

```python
class OnboardingState(TypedDict):
    messages: Annotated[list[BaseMessage], add_messages]  # Conversation memory
    employee_role: str              # e.g., "Software Engineer"
    employee_name: str              # For personalized interactions
    syllabus: list[str]             # Ordered learning plan
    current_topic: str              # Active topic being studied
    completed_topics: Annotated[list[str], operator.add]  # Append-only
    quiz_score: int                 # Latest score (0-100)
    failed_attempts: int            # Consecutive failures
    assessment_history: Annotated[list[dict], operator.add]  # Append-only
    is_certified: bool              # True after supervisor approval
    requires_human_review: bool     # HITL interrupt flag
    current_agent: str | None       # Active agent tracker
```

### Conditional Edge Functions (Zero-Latency, No LLM)

| Function | After Node | Logic |
|:---|:---|:---|
| `route_start` | `__start__` | If no syllabus → `planner_node`; else → LLM intent classification |
| `grade_check` | `assessor_node` | Score ≥ 80 → `"pass"` (advance); < 80 → `"fail"` (remediation/await) |
| `topic_check` | `advance_topic` | All topics done → `"certify"`; more left → `"continue"` (END) |

### HITL (Human-in-the-Loop) Interrupt

The graph compiles with `interrupt_before=["certifier_node"]`. When all topics pass, the graph **pauses** before certification. A supervisor must call `/approve` or `/reject`:

- **Approve** → `graph.ainvoke(None)` → Certifier runs → Certificate issued
- **Reject** → `graph.aupdate_state(...)` → Score reset, trainee routes back to Explainer

### Key Bug Fixes in Workflow

| Bug | Fix |
|:---|:---|
| Stale quiz_score leaking across topics | `advance_topic` explicitly resets `quiz_score = None` |
| Duplicate completed_topics entries | Guard in `assessor_node` checks before appending |
| Quiz answers misclassified as "learn" | Router's assessor context guard short-circuits classification |

---

## 📥 RAG Ingestion Pipeline

**File**: `src/ingestion/pipeline.py` (309 lines)

### Pipeline Stages

```
PDF/Markdown Upload
    → Text Extraction (pypdf for PDF, native read for Markdown)
    → Chunking (RecursiveCharacterTextSplitter, 1000 chars, 200 overlap)
    → Embedding (gemini-embedding-001 via Google Generative AI)
    → Store in ChromaDB with metadata (filename, page, chunk_index)
```

### Configuration

| Parameter | Value |
|:---|:---|
| Chunk Size | 1,000 characters |
| Chunk Overlap | 200 characters |
| Embedding Model | `models/gemini-embedding-001` |
| Collection Name | `internal_policies` |
| Max File Size | 50 MB |
| Supported Formats | `.pdf`, `.md` |

### Knowledge Base: 17 SOP Documents

The system ships with 17 pre-built enterprise SOPs covering 5 role tracks:

| Category | Documents |
|:---|:---|
| **HR** | Code of Conduct, Leave Policy |
| **Security** | InfoSec & Data Protection, Access Control |
| **Compliance** | AML/KYC Policy, Data Privacy (GDPR) |
| **Engineering** | Secure Coding Guidelines, Incident Response |
| **Finance** | Expense Reimbursement |
| **IT** | IT Assets & Acceptable Use |
| **Corporate** | Company Vision & Culture |
| **General** | Admin & IT Onboarding |
| **Role Tracks** | Software Engineer, Compliance Officer, Financial Analyst, IT Administrator, General Staff |

---

## ⚡ API Layer (FastAPI + SSE Streaming)

### Endpoints

| Method | Endpoint | Description |
|:---|:---|:---|
| `GET` | `/health` | Health check (status, environment, version) |
| `POST` | `/api/v1/sessions` | Create onboarding session → Planner generates syllabus |
| `GET` | `/api/v1/sessions/{id}/status` | Get session progress (topics, scores, certification) |
| `POST` | `/api/v1/sessions/{id}/chat` | SSE-streamed chat (main interaction) |
| `POST` | `/api/v1/sessions/{id}/chat/sync` | Non-streaming chat fallback |
| `POST` | `/api/v1/sessions/{id}/approve` | Supervisor approves certification (HITL) |
| `POST` | `/api/v1/sessions/{id}/reject` | Supervisor rejects → remediation loop |
| `POST` | `/api/v1/sessions/{id}/feedback` | Submit user feedback to Langfuse |
| `POST` | `/api/v1/documents/ingest` | Upload & process SOP document |

### SSE Event Protocol

The streaming chat endpoint emits these event types:

```
event: agent_start    → {"agent": "explainer_node", "trace_id": "..."}
event: token          → {"content": "The security policy..."}
event: agent_end      → {"agent": "explainer_node"}
event: state_update   → {"current_topic": "...", "quiz_score": 85, ...}
event: requires_approval → {"message": "Awaiting supervisor...", "pending_node": [...]}
event: error          → {"detail": "Error message"}
event: done           → {}
```

### Architecture Decisions

- **Singleton Graph**: Compiled once during FastAPI lifespan startup via `init_graph()`, stored as module-level variable, injected via `Depends(get_graph_instance)`.
- **Dual Checkpointer**: SQLite (`SqliteSaver`) for development (zero-config), PostgreSQL (`AsyncPostgresSaver` with `psycopg` connection pool) for production.
- **Windows Compatibility**: `asyncio.WindowsSelectorEventLoopPolicy()` set at multiple entry points to fix Psycopg's ProactorEventLoop incompatibility.
- **Langfuse Integration**: Every graph invocation injects `CallbackHandler` with metadata (`session_id`, `user_id`, `trace_name`, environment tags).

---

## 🖥️ Frontend (React 19 + Vite)

### Tech Stack

| Package | Version | Purpose |
|:---|:---|:---|
| React | 19.2 | UI framework |
| Vite | 8.0 | Build tool & dev server |
| react-markdown + remark-gfm | 10.1 | Markdown rendering in chat bubbles |
| lucide-react | 1.14 | Icon library |
| @langfuse/tracing | 5.3 | Client-side observability (OpenTelemetry) |

### Component Architecture

| Component | File | Responsibility |
|:---|:---|:---|
| `App.jsx` | Root | Centralized state management, event handlers |
| `SetupScreen` | View 1 | Employee name/role input form |
| `ChatWindow` | View 2 | Message list, SSE streaming, markdown rendering, feedback buttons |
| `Sidebar` | View 2 | Syllabus progress, topic checklist, certification status |
| `SupervisorModal` | View 3 | HITL approve/reject interface with feedback textarea |

### API Client Layer

- **`api/client.js`**: Typed fetch wrappers for all backend endpoints.
- **`api/sseParser.js`**: Custom POST-based SSE parser (browser's native `EventSource` only supports GET). Handles `\r\n` normalization for Windows and multi-line data accumulation per SSE spec.

### Key Frontend Bug Fixes

| Bug | Fix |
|:---|:---|
| Stale closure in `done` handler overwrites approval state | `useRef` (`approvalFlagRef`) instead of closure-captured state |
| Multi-line SSE data chunks parsed incorrectly | Accumulate `data:` lines before JSON.parse |

---

## 📈 Observability & Evaluation

### Langfuse Integration

- **Backend**: `CallbackHandler` injected into every `graph.ainvoke()` / `graph.astream()` call with session metadata.
- **Frontend**: `@langfuse/tracing` with OpenTelemetry SDK for client-side span tracking.
- **User Feedback Loop**: Thumbs up/down → `POST /feedback` → `langfuse.score()` linked to trace.
- **PII Masking**: Regex-based email redaction via `observability.py`.

### Automated Evaluation Pipeline

**File**: `scripts/run_evaluation.py` (265 lines)

Runs the Explainer Agent against a **25-question gold-standard dataset** (`data/evaluation_dataset.json`) spanning HR, Security, Compliance, Engineering, and Finance categories.

**LLM-as-a-Judge** scores each response on two dimensions:
- **Faithfulness** (0.0–1.0): Does the response match the ground truth?
- **Relevancy** (0.0–1.0): Does the response directly answer the question?

Results are saved to `data/eval_results.json` with per-question breakdowns.

---

## 🛠️ Tech Stack

| Category | Technology | Version | Description |
|:---|:---|:---|:---|
| **Runtime** | Python | 3.12+ | Async-native with modern type hints |
| **Orchestration** | LangGraph | 1.1.10 | Cyclic, stateful multi-agent workflow engine |
| **LLM** | Google Gemini 3 Flash Preview | — | High-speed inference, structured output |
| **Embeddings** | Gemini Embedding 001 | — | Semantic vectorization for RAG |
| **Vector DB** | ChromaDB | 1.5.9 | Persistent vector storage with MMR search |
| **API Framework** | FastAPI | 0.136 | Async HTTP server with SSE streaming |
| **Streaming** | sse-starlette | 3.4+ | Server-Sent Events for real-time tokens |
| **Validation** | Pydantic | 2.13 | Request/response schema validation |
| **Configuration** | pydantic-settings | 2.14 | `.env` file management with typed settings |
| **LangChain** | langchain-core | 1.3.3 | Agent primitives, message types, tools |
| **State Persistence** | SQLite / PostgreSQL | — | Dev: file-based; Prod: connection pool |
| **Observability** | Langfuse | 4.6.1 | Tracing, cost tracking, user feedback |
| **Frontend** | React 19 + Vite 8 | — | Modern SPA with SSE streaming |
| **Package Manager** | uv | latest | Fast Python dependency resolution |
| **Linting** | Ruff | 0.15.12 | Lint + format (pycodestyle, isort, bugbear) |
| **Type Checking** | Mypy | 2.0 | Strict mode with typed overrides |
| **Testing** | Pytest | 9.0 | Async test support via pytest-asyncio |
| **Container** | Docker + docker-compose | — | Multi-service deployment |

---

## 📁 Project Structure

```
LangGraph-OnboardingAgent/
├── src/
│   ├── agents/                    # AI Agent implementations
│   │   ├── router.py              # Intent classifier (learn/quiz/status)
│   │   ├── planner.py             # Curriculum syllabus generator
│   │   ├── explainer.py           # RAG-powered tutor (ReAct agent)
│   │   ├── assessor.py            # Quiz generator + LLM grader
│   │   ├── certifier.py           # Certificate issuer (terminal node)
│   │   ├── status.py              # Progress summary renderer
│   │   └── tools.py               # Shared tools (retrieve, rubric, grade)
│   ├── api/                       # FastAPI REST layer
│   │   ├── server.py              # App factory, lifespan, CORS, health
│   │   ├── chat.py                # SSE streaming + sync chat endpoints
│   │   ├── sessions.py            # Session create + status endpoints
│   │   ├── supervisor.py          # HITL approve/reject endpoints
│   │   ├── routers.py             # Document ingestion endpoint
│   │   └── dependencies.py        # Graph singleton + DI providers
│   ├── core/                      # Shared infrastructure
│   │   ├── config.py              # Pydantic Settings (env-based)
│   │   ├── database.py            # Checkpointer + ChromaDB factories
│   │   ├── llm.py                 # Gemini LLM factory
│   │   └── observability.py       # Langfuse handler + PII masking
│   ├── graph/
│   │   └── workflow.py            # LangGraph state machine assembly
│   ├── ingestion/
│   │   └── pipeline.py            # RAG pipeline (load→chunk→embed→store)
│   └── schemas/
│       ├── state.py               # OnboardingState TypedDict
│       ├── requests.py            # Pydantic request models
│       └── responses.py           # Pydantic response models
├── frontend/
│   └── src/
│       ├── App.jsx                # Root component + state management
│       ├── components/            # SetupScreen, ChatWindow, Sidebar, SupervisorModal
│       └── api/                   # client.js, sseParser.js
├── data/
│   ├── sops/                      # 17 enterprise SOP documents (Markdown)
│   ├── evaluation_dataset.json    # 25-question gold-standard test set
│   └── eval_results.json          # LLM-as-a-Judge evaluation results
├── scripts/
│   ├── ingest_sops.py             # Batch SOP ingestion into ChromaDB
│   ├── run_evaluation.py          # Automated faithfulness/relevancy eval
│   ├── stress_test_api.py         # Multi-user API stress test
│   └── check_models.py            # Model availability checker
├── tests/                         # Pytest test suite (6 test files)
├── docs/                          # Architecture, PRD, Milestones, Tech Stack
├── Dockerfile                     # Python 3.12-slim + uv
├── docker-compose.yml             # API + PostgreSQL services
├── pyproject.toml                 # Dependencies + tool config
└── .env.example                   # Environment variable template
```

---

## 🚀 Getting Started

### Prerequisites

- **Python 3.12+**
- **Node.js 20+** (for frontend)
- **Google Gemini API Key** ([Get one here](https://ai.google.dev/))
- **uv** package manager (recommended) or pip

### 1. Clone & Configure

```bash
git clone https://github.com/WillyHanafi1/Enterprise-AI-Onboarding-Compliance-Accelerator-Agentic-LMS-.git
cd Enterprise-AI-Onboarding-Compliance-Accelerator-Agentic-LMS-

# Create environment file
cp .env.example .env
# Edit .env and add your GEMINI_API_KEY
```

### 2. Backend Setup

```bash
# Install dependencies with uv (recommended)
uv sync

# Or with pip
pip install .
```

### 3. Ingest SOP Documents

```bash
# Ingest the 17 pre-built SOP documents into ChromaDB
python scripts/ingest_sops.py
```

### 4. Start the API Server

```bash
# Development mode with hot reload
uv run uvicorn src.api.server:app --reload --port 8000

# Or directly
python -m src.api.server
```

API docs available at: `http://localhost:8000/api/v1/docs`

### 5. Frontend Setup

```bash
cd frontend
npm install
npm run dev
```

Frontend available at: `http://localhost:5173`

### Environment Variables

```env
# === Required ===
GEMINI_API_KEY="your_google_api_key_here"

# === Optional: Langfuse Observability ===
LANGFUSE_PUBLIC_KEY="pk-lf-..."
LANGFUSE_SECRET_KEY="sk-lf-..."
LANGFUSE_HOST="https://cloud.langfuse.com"

# === Optional: Production Database ===
DATABASE_URL="postgresql://user:password@localhost:5432/lms_db"
ENVIRONMENT="development"   # "production" for PostgreSQL checkpointer
```

---

## 🧪 Testing

### Test Suite (6 files, ~53KB)

```bash
# Run all tests
uv run pytest

# Run specific test modules
uv run pytest tests/test_graph.py      # Workflow integration tests
uv run pytest tests/test_agents.py     # Agent unit tests
uv run pytest tests/test_api.py        # API endpoint tests
uv run pytest tests/test_ingestion.py  # RAG pipeline tests
uv run pytest tests/test_observability.py  # Langfuse integration tests
```

### Evaluation Pipeline

```bash
# Run LLM-as-a-Judge evaluation (25 questions)
python scripts/run_evaluation.py
# Results saved to data/eval_results.json
```

### API Stress Test

```bash
# Simulate 5 concurrent users
python scripts/stress_test_api.py
```

---

## 🐳 Deployment

### Docker

```bash
# Build and run with Docker Compose
docker-compose up --build

# Services:
#   - api:      localhost:8000 (FastAPI + LangGraph)
#   - postgres: localhost:5432 (State persistence)
```

### Production Checklist

- [ ] Set `ENVIRONMENT=production` in `.env`
- [ ] Configure `DATABASE_URL` for PostgreSQL
- [ ] Set Langfuse API keys for observability
- [ ] Restrict CORS origins in `server.py`
- [ ] Disable Swagger docs (`docs_url=None`)
- [ ] Ingest production SOP documents

---

## 🔮 Roadmap

| Phase | Feature | Status |
|:---|:---|:---|
| ✅ | RAG Ingestion Pipeline | Complete |
| ✅ | Multi-Agent Graph (Planner, Explainer, Assessor, Certifier) | Complete |
| ✅ | FastAPI + SSE Streaming | Complete |
| ✅ | HITL Supervisor Approve/Reject | Complete |
| ✅ | React Frontend with real-time streaming | Complete |
| ✅ | Langfuse Observability + User Feedback | Complete |
| ✅ | Automated Evaluation Pipeline | Complete |
| 🔜 | Live CRM Connectors (Salesforce/HubSpot) | Planned |
| 🔜 | Action Tools (email drafting, Jira tasks, e-sign) | Planned |
| 🔜 | Role-Based Access Control (RBAC) | Planned |
| 🔜 | Multi-tenant deployment | Planned |

---

### 👨‍💻 Author

**Willy Hanafi**
*AI Engineer & Agentic Systems Specialist*

---

*Built with ❤️ using LangGraph, Google Gemini, FastAPI, and React.*
