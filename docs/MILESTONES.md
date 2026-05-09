# Project Milestones & Task Breakdown
## Enterprise AI Onboarding & Compliance Accelerator

| Field | Detail |
|---|---|
| **Document Status** | Draft v2 |
| **Last Updated** | May 2026 |
| **Related Docs** | [PRD.md](./PRD.md) · [ARCHITECTURE.md](./ARCHITECTURE.md) · [TECH_STACK.md](./TECH_STACK.md) |

This document breaks the project into incremental phases. Each phase produces a working, testable deliverable before moving to the next. Tasks include acceptance criteria (Definition of Done) to prevent ambiguity.

---

## Phase 1: Project Initialization & Infrastructure

**Goal:** Set up the development environment, project scaffolding, and verify core integrations (LLM, Database).

| # | Task | Definition of Done |
|---|---|---|
| [x] 1.1 | Initialize Python 3.11+ project with `uv` (create `pyproject.toml`). | `uv sync` runs successfully. Virtual environment is created. |
| [x] 1.2 | Create project directory structure (`src/core/`, `src/agents/`, `src/schemas/`, `src/graph/`, `src/api/`, `src/ingestion/`, `tests/`). | All directories exist with `__init__.py` files. |
| [x] 1.3 | Set up FastAPI server with health check endpoint. | `GET /health` returns `{"status": "ok"}`. Swagger UI accessible at `/docs`. |
| [x] 1.4 | Configure Gemini API integration via `langchain-google-genai`. | Python script can send a prompt to Gemini API and receive a streaming response. |
| [x] 1.5 | Set up Langfuse observability. | A test LLM call appears in Langfuse dashboard with trace, latency, and token count. |
| [x] 1.6 | Create `.env.example` and `pydantic-settings` config module. | All config values loaded from environment variables. No hardcoded secrets. |
| [x] 1.7 | Create `Dockerfile` and `docker-compose.yml` skeleton. | `docker compose up` starts FastAPI service (other services can be stubs). |

**Phase 1 Deliverable:** A running FastAPI server that can communicate with Gemini API and log traces to Langfuse.

---

## Phase 2: RAG Pipeline & Document Ingestion

**Goal:** Build the document processing pipeline and verify semantic search quality.

| # | Task | Definition of Done |
|---|---|---|
| [x] 2.1 | Implement PDF/Markdown document loader using PyPDF2 + Unstructured. | A 50-page PDF is loaded and converted to raw text without errors. |
| [x] 2.2 | Implement text chunking with `RecursiveCharacterTextSplitter` (chunk_size=1000, overlap=200). | Document is split into chunks with metadata (source file, page number). |
| [x] 2.3 | Set up ChromaDB and store embedded chunks using Gemini Embeddings. | Chunks are persisted in ChromaDB. Collection is queryable after server restart. |
| [x] 2.4 | Build `retrieve_internal_policies` tool function. | Given a query, returns top-5 relevant chunks with similarity scores > 0.7. |
| [x] 2.5 | Create ingestion API endpoint (`POST /api/v1/documents/ingest`). | Uploading a PDF via API triggers the full ingestion pipeline and returns chunk count. |
| [x] 2.6 | Write integration test for RAG retrieval accuracy. | Test query returns relevant chunks (manual verification on 5 sample queries). |

**Phase 2 Deliverable:** A working RAG pipeline that ingests SOPs and returns accurate, relevant chunks.

---

## Phase 3: Core Agent Development

**Goal:** Build and test each agent in isolation before wiring them into the graph.

| # | Task | Definition of Done |
|---|---|---|
| [x] 3.1 | Define `OnboardingState` TypedDict in `src/schemas/state.py`. | State schema includes all fields from Architecture doc. Type-checks with mypy. |
| [x] 3.2 | Build **Curriculum Planner Agent** (`src/agents/planner.py`). | Given a role + document collection, generates an ordered syllabus (list of topics). |
| [x] 3.3 | Build **Explainer Agent** (`src/agents/explainer.py`). | Given a topic + user question, retrieves SOP context via RAG and explains it. Faithfulness > 95% on 10 test questions. |
| [x] 3.4 | Build **Assessor Agent** (`src/agents/assessor.py`). | Generates open-ended question for a topic. Grades a user response with score and feedback. Correct answers score ≥ 80, wrong answers score < 50. |
| [x] 3.5 | Build `generate_evaluation_rubric` tool function. | Returns a structured rubric string for any given topic. |
| [x] 3.6 | Write unit tests for each agent (Pytest). | All agent tests pass. Each agent tested with at least 3 input scenarios. |

**Phase 3 Deliverable:** Three independently tested agents ready for graph assembly.

---

## Phase 4: LangGraph Orchestration & State Persistence

**Goal:** Wire agents into a LangGraph workflow with conditional routing and persistent memory.

| # | Task | Definition of Done |
|---|---|---|
| 4.1 | Implement Router (conditional edge) for intent classification. | Router correctly classifies "teach me about X" → explainer, "quiz me" → assessor, "what's my progress" → status. |
| 4.2 | Assemble full graph in `src/graph/workflow.py` (Planner → Router → Explainer/Assessor → Grade → HITL → Certifier). | Graph compiles without errors. `graph.get_graph().draw_mermaid()` produces valid diagram. |
| 4.3 | Implement conditional edge: Assessor fail → Explainer remediation loop. | When score < 80, graph routes to Explainer. When score ≥ 80, graph routes to HITL gate. |
| 4.4 | Integrate **Checkpointer** (SQLite for dev). | Conversation state persists across server restarts. Resuming a `thread_id` continues from last checkpoint. |
| 4.5 | Test full graph end-to-end with a simulated conversation. | A complete flow (start → learn → quiz → pass → certify) executes without errors. |

**Phase 4 Deliverable:** A fully connected LangGraph workflow with persistent state and conditional routing.

---

## Phase 5: Human-in-the-Loop & API Streaming

**Goal:** Implement the supervisor approval gate and real-time streaming for production-readiness.

| # | Task | Definition of Done |
|---|---|---|
| 5.1 | Implement `interrupt_before` on the Certifier node. | Graph pauses after Assessor passes. State is saved. No further nodes execute until resumed. |
| 5.2 | Create chat endpoint (`POST /api/v1/sessions/{id}/chat`) with SSE streaming. | Client receives streamed tokens in real-time. Agent status updates visible ("Searching documents...", "Evaluating answer..."). |
| 5.3 | Create session management endpoints (`POST /api/v1/sessions`, `GET /api/v1/sessions/{id}/status`). | Sessions can be created, queried for progress, and resumed. |
| 5.4 | Create supervisor endpoints (`POST /api/v1/sessions/{id}/approve`, `POST /api/v1/sessions/{id}/reject`). | Approving resumes the graph and issues certification. Rejecting routes back to Explainer. |
| 5.5 | Implement error handling for all failure scenarios (see Architecture doc). | API rate limit → 429 backoff. Empty RAG → graceful message. Malformed LLM output → retry. |
| 5.6 | Integration test: full API flow via `httpx` or `pytest` async client. | Complete onboarding flow works end-to-end through the API. |

**Phase 5 Deliverable:** Production-ready API with streaming, HITL, and error handling.

---

## Phase 6: Evaluation, Testing & Portfolio Polish

**Goal:** Validate AI quality, containerize for deployment, and prepare the repository for public presentation.

| # | Task | Definition of Done |
|---|---|---|
| 6.1 | Build evaluation dataset (20+ question-answer pairs with expected scores). | Gold-standard test set covers all SOP topics. |
| 6.2 | Run **Faithfulness** evaluation using LLM-as-a-judge. | Faithfulness score ≥ 95% across the evaluation dataset. |
| 6.3 | Run **Answer Relevancy** evaluation. | Relevancy score ≥ 90% across the evaluation dataset. |
| 6.4 | Finalize `Dockerfile` and `docker-compose.yml` (FastAPI + PostgreSQL + ChromaDB). | `docker compose up` starts all services. API is accessible and functional. |
| 6.5 | Run `Ruff` linter and `mypy` type checker. Fix all issues. | Zero lint errors. Zero type errors. |
| 6.6 | Write comprehensive `README.md` (project overview, architecture diagram, setup instructions, API usage examples, Langfuse screenshots). | README contains: badges, description, architecture diagram, quickstart guide, API reference, and evaluation results. |
| 6.7 | Final Git push to GitHub with clean commit history. | Repository is public. README renders correctly. All CI checks pass. |

**Phase 6 Deliverable:** A polished, publicly presentable portfolio project with quantified AI quality metrics.

---

*Use this document as a daily development checklist. Mark tasks `[x]` as you complete them.*
