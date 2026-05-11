# Tech Stack Selection
## Enterprise AI Onboarding & Compliance Accelerator

| Field | Detail |
|---|---|
| **Document Status** | Draft v3 (Version Locked) |
| **Last Updated** | May 2026 |
| **Related Docs** | [PRD.md](./PRD.md) · [ARCHITECTURE.md](./ARCHITECTURE.md) |

This document outlines every technology chosen for this project, with version pinning to the latest stable releases, justification, and alternatives considered.

---

## 1. Core Language & Runtime

| Category | Choice | Version | Justification |
|---|---|---|---|
| **Language** | Python | `>=3.12` | Industry standard for AI/ML. Python 3.12 provides major performance optimizations (PEP 709) and better error messages. Required for LangGraph async features. |
| **Package Manager** | `uv` | `latest` | 10-100x faster than pip (written in Rust). Deterministic lockfile (`uv.lock`) prevents dependency conflicts. |
| **Alternative Considered** | Poetry | — | Mature but slower. `uv` is the modern replacement recommended by the Python community. |

## 2. AI Orchestration Framework

| Category | Choice | Version | Justification |
|---|---|---|---|
| **Graph Engine** | `langgraph` | `1.1.10` | Enables cyclic, stateful agent workflows with native `interrupt` support. Version 1.1.x is the highly stable, production-ready release. |
| **LLM Abstraction** | `langchain-core` | `1.3.3` | Provides unified interface for LLM calls. Version 1.3.x marks a fully stable semantic API release without experimental breaking changes. |
| **Alternative Considered** | CrewAI, AutoGen | — | Less control over execution flow. No native state persistence or interrupt mechanism. |

## 3. LLM Inference Engine

| Category | Choice | Version | Justification |
|---|---|---|---|
| **Primary (Production)** | `Google Gemini API` (gemini-3-flash-preview) | API | **State-of-the-art Flash.** High-speed inference and massive context window for RAG operations. |
| **LangChain Integration** | `langchain-google-genai` | `4.2.2` | Official Google integration for LangChain, fully supporting gemini-3-flash streaming, structured outputs, and tool calling. |
| **Alternative Considered** | Ollama, vLLM | — | Discarded due to lack of local hardware resources (GPU/RAM) and to favor the large context window of Gemini. |

## 4. RAG & Vector Database

| Category | Choice | Version | Justification |
|---|---|---|---|
| **Vector Store** | `chromadb` | `1.5.9` | Embedded vector database. Version 1.5.x brings significant stability and query speed improvements for semantic retrieval. |
| **Embedding Model** | `models/gemini-embedding-001` (via Gemini API) | API | High-quality embeddings integrated seamlessly with the Gemini ecosystem. |
| **Document Loader** | `pypdf` + `unstructured` | `pypdf 6.10.2`<br>`unstructured 0.22.27` | `PyPDF2` is officially deprecated; `pypdf` is the modern, maintained stable fork. `unstructured` provides robust fallback for complex layouts. |
| **Text Splitter** | `RecursiveCharacterTextSplitter` | Built-in | Respects paragraph/sentence boundaries. Configurable `chunk_size` and `overlap` for optimal retrieval. |
| **Alternative Considered** | FAISS, Pinecone | — | FAISS lacks metadata filtering. Pinecone is cloud-only (violates data privacy requirement). |

## 5. Backend Server & API

| Category | Choice | Version | Justification |
|---|---|---|---|
| **Web Framework** | `fastapi` | `0.136.1` | Async-native (ASGI). 0.136.x includes the latest Pydantic V2 core optimizations for faster serialization. |
| **ASGI Server** | `uvicorn` | `0.46.0` | High-performance async server. Production-ready. |
| **Data Validation** | `pydantic` | `2.13.4` | Core Rust-based validation. V2 is vastly faster than V1 and provides strict schema parsing for LLM JSON outputs. |
| **Streaming** | Server-Sent Events (SSE) | HTTP standard | Enables real-time streaming of agent thought process. Prevents HTTP timeout for long-running agent computations. |
| **Alternative Considered** | Flask, Django | — | Flask lacks native async. Django is too heavy for an API-only ML service. |

## 6. Database & State Persistence

| Category | Choice | Version | Justification |
|---|---|---|---|
| **Development** | `SQLite` | Built-in | Zero-config. Perfect for local development. LangGraph provides `SqliteSaver` checkpointer. |
| **Production** | `PostgreSQL` | `>=15` | Industry-standard relational DB. LangGraph provides `AsyncPostgresSaver` for async state persistence. |
| **Alternative Considered** | Redis | — | Good for caching but less suitable for durable state persistence required by HITL (supervisor may approve days later). |

## 7. Observability & Telemetry

| Category | Choice | Version | Justification |
|---|---|---|---|
| **Platform** | `langfuse` | `4.6.1` | Purpose-built for LLM observability. Tracks: token usage, latency per node, cost estimation, full agent trace visualization. |
| **Alternative Considered** | LangSmith, Arize Phoenix | — | LangSmith is proprietary (LangChain Inc.). Langfuse is open-source and self-hostable. |

## 8. Code Quality & Testing

| Category | Choice | Version | Justification |
|---|---|---|---|
| **Linter + Formatter** | `ruff` | `0.15.12` | Replaces Flake8 + Black + isort in a single tool. Extremely fast (Rust-based). |
| **Type Checking** | `mypy` | `2.0.0` | Catches type errors at development time. Version 2.0.0 brings huge performance gains. |
| **Testing Framework** | `pytest` | `9.0.3` | Standard Python testing. Supports async tests via `pytest-asyncio`. |
| **Environment Mgt** | `pydantic-settings` | `2.14.1` | Type-safe environment variable management. |

## 9. Frontend Application
| Category | Choice | Version | Justification |
|---|---|---|---|
| **Framework** | `React` + `Vite` | `React 19` / `Vite 6` | High performance, fast HMR, and modern component ecosystem. |
| **Styling** | `Vanilla CSS` + `TailwindCSS` (Optional) | `latest` | High flexibility for premium, custom designs. |
| **State Management** | `TanStack Query` (React Query) | `v5` | Robust caching and server-state management for API responses. |
| **Icons** | `Lucide React` | `latest` | Consistent, lightweight, and modern iconography. |

## 10. Containerization & Deployment

---

*All versions listed are the latest stable releases as of May 2026 and should be strictly pinned in `pyproject.toml` or `uv.lock` to guarantee deterministic builds.*
