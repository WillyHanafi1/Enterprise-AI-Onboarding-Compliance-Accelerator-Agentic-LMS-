# 🚀 Enterprise AI Onboarding & Compliance Accelerator (Agentic LMS)

[![Python](https://img.shields.io/badge/Python-3.12%2B-blue?style=for-the-badge&logo=python&logoColor=white)](https://www.python.org/)
[![LangGraph](https://img.shields.io/badge/Orchestration-LangGraph-orange?style=for-the-badge)](https://github.com/langchain-ai/langgraph)
[![Gemini](https://img.shields.io/badge/AI-Google%20Gemini-red?style=for-the-badge&logo=google-gemini&logoColor=white)](https://ai.google.dev/)
[![FastAPI](https://img.shields.io/badge/API-FastAPI-green?style=for-the-badge&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![React](https://img.shields.io/badge/Frontend-React%2019-61DAFB?style=for-the-badge&logo=react&logoColor=black)](https://react.dev/)
[![Langfuse](https://img.shields.io/badge/Observability-Langfuse-black?style=for-the-badge)](https://langfuse.com/)

> **Standardizing Enterprise Onboarding through Agentic Workflows and Flow Engineering.**

The **Enterprise AI Onboarding LMS** is a production-grade multi-agent system designed to transform static company policies into an interactive, high-fidelity learning experience. By leveraging **LangGraph** for orchestration and **Agentic RAG** for knowledge retrieval, it automates the entire employee integration journey—from personalized syllabus planning to human-verified certification.

---

## 🌟 The Vision: From Static to Agentic
Traditional onboarding involves reading hundreds of pages of static PDFs, leading to low engagement and compliance risks. This project reimagines the process as a **conversational journey** where AI agents don't just "show" information, but "teach" and "verify" understanding in real-time.

### The 4C Onboarding Framework
Our system is architected around the industry-standard **4C Framework**:
1.  **Compliance:** Automated teaching of legal and administrative SOPs (AML, GDPR, IT Security).
2.  **Clarification:** Role-specific KPI alignment and technical expectation setting.
3.  **Culture:** Immersive introduction to company vision and core values (SPEED).
4.  **Connection:** Guided integration into team workflows and internal tools.

---

## 🏗️ Multi-Agent Ecosystem
The core of the system is a team of specialized agents working in a stateful, cyclic graph.

| Agent | Responsibility | Key Tech |
| :--- | :--- | :--- |
| **🎯 Curriculum Planner** | Analyzes employee role and creates a prioritized, logical syllabus. | Dynamic Graph State |
| **📚 Explainer (RAG)** | Provides hallucination-free tutoring grounded in company SOPs. | Vector DB + Semantic Search |
| **⚖️ Assessor (Judge)** | Generates case-study questions and grades answers via structured rubrics. | LLM-as-a-Judge |
| **👨‍✈️ Supervisor (HITL)** | Human-in-the-loop gatekeeper who reviews results before certification. | LangGraph Interrupts |
| **🎓 Certifier** | Issues final verifiable credentials and session summaries. | State Persistence |

---

## 🛠️ Advanced Engineering & Flow
### 1. Flow Engineering with LangGraph
Unlike simple linear chains, our system uses a **Directed Acyclic Graph (DAG)** with conditional edges:
- **Remediation Loop:** If a trainee fails a quiz (score < 80), the graph automatically routes them back to the `Explainer Agent` for targeted remediation.
- **State Persistence:** Using SQLite checkpointers, sessions are resumable. A trainee can stop mid-lesson and resume days later without data loss.

### 2. Agentic RAG Pipeline
We don't just dump text into an LLM. Our pipeline includes:
- **Hybrid Ingestion:** Processes high-fidelity Markdown SOPs with enterprise metadata.
- **Semantic Retrieval:** Uses ChromaDB and Gemini Embeddings to find the most relevant policy clauses.
- **Contextual Grounding:** Every explanation is anchored to a specific company document to prevent hallucinations.

### 3. Real-time API & Streaming
The backend is a **FastAPI** server that streams agent reasoning via **Server-Sent Events (SSE)**. This allows the frontend to show:
- *"Searching internal policies..."*
- *"Evaluating your answer against the security rubric..."*
- Real-time token streaming for a seamless chat experience.

---

## 🛠️ Tech Stack

| Category | Technology | Description |
| :--- | :--- | :--- |
| **Core** | ![Python](https://img.shields.io/badge/Python-3.12%2B-blue?style=flat-square&logo=python&logoColor=white) | Async-native runtime for AI orchestration. |
| **Orchestration** | ![LangGraph](https://img.shields.io/badge/LangGraph-1.1.10-orange?style=flat-square) | Cyclic, stateful multi-agent workflow engine. |
| **Brain (LLM)** | ![Gemini](https://img.shields.io/badge/Google%20Gemini-3%20Flash-red?style=flat-square&logo=google-gemini&logoColor=white) | High-speed inference & 1M+ context window. |
| **Vector DB** | ![ChromaDB](https://img.shields.io/badge/ChromaDB-1.5.9-green?style=flat-square) | Semantic storage for enterprise SOP retrieval. |
| **API** | ![FastAPI](https://img.shields.io/badge/FastAPI-0.136-blue?style=flat-square&logo=fastapi&logoColor=white) | High-performance backend with SSE streaming. |
| **Frontend** | ![React](https://img.shields.io/badge/React-19-61DAFB?style=flat-square&logo=react&logoColor=black) | Premium, responsive user & supervisor interface. |
| **Observability**| ![Langfuse](https://img.shields.io/badge/Langfuse-4.6.1-black?style=flat-square) | End-to-end tracing, evaluation, and cost tracking. |

---

## 📈 Observability & Evaluation
Integrated with **Langfuse**, the system provides full transparency into the AI's "thought process":
- **Trace Visualization:** View exactly how a question moved from the Router to the Assessor.
- **Cost & Latency Tracking:** Monitor token usage per agent node.
- **Efficacy Metrics:** Evaluate the **CLEAR** framework (Cost, Latency, Efficacy, Assurance, Reliability).

---

## 🚀 Getting Started

### Prerequisites
- **Python 3.12+**
- **Node.js 20+**
- **Google Gemini API Key**

### 1. Backend Setup
```bash
# Clone the repository
git clone https://github.com/WillyHanafi1/Enterprise-AI-Onboarding-Compliance-Accelerator-Agentic-LMS-.git
cd Enterprise-AI-Onboarding-Compliance-Accelerator-Agentic-LMS-

# Install dependencies (using uv recommended)
pip install .
```

### 2. Ingest Enterprise Data
```bash
# Place your SOPs in data/sops/
python scripts/ingest_sops.py
```

### 3. Frontend Setup
```bash
cd frontend
npm install
npm run dev
```

---

## 🔮 Roadmap: The Operational Co-pilot
The future of this project involves moving beyond learning into **Actionable Operations**:
- **Live Connectors:** Integrate with CRM (Salesforce/HubSpot) to pull real-time project data.
- **Action Tools:** Enable agents to draft emails, send e-signs, and create tasks in Jira.
- **Role-Based Access (RBAC):** Ensure the agent respects enterprise data silos.

---

### 👨‍💻 Author
**Willy Hanafi**
*AI Engineer & Agentic Systems Specialist*

---
*Built with ❤️ using LangGraph, Gemini, and FastAPI.*
