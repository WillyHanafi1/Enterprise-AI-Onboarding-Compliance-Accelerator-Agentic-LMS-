# Product Requirements Document (PRD)
## Enterprise AI Onboarding & Compliance Accelerator (Agentic LMS)

| Field | Detail |
|---|---|
| **Document Status** | Draft v2 |
| **Author** | Willy Hanafi |
| **Created** | May 2026 |
| **Project Type** | Multi-Agent AI System |
| **Core Framework** | LangGraph, LangChain, FastAPI |

---

## 1. Executive Summary

The **Enterprise AI Onboarding & Compliance Accelerator** is an autonomous, multi-agent Learning Management System (LMS) designed for corporate environments. It aims to modernize how new employees learn internal Standard Operating Procedures (SOPs) and pass rigorous compliance standards (e.g., SOC2, ISO27001, internal security protocols).

By utilizing an agentic workflow, the system creates personalized learning paths, dynamically quizzes employees, evaluates answers using LLM-as-a-judge, and ensures data privacy by utilizing enterprise-grade LLM APIs with zero-data-retention policies.

## 2. Problem Statement

| # | Problem | Business Impact |
|---|---|---|
| P1 | **High Cost of Onboarding** — Training new hires requires significant time from senior employees and managers. | Thousands of dollars in lost productivity per hire. |
| P2 | **Static Learning** — Traditional LMS platforms rely on boring, static videos and multiple-choice quizzes that do not adapt to the employee's actual understanding. | Low knowledge retention, repeated training cycles. |
| P3 | **Data Security Risks** — Uploading highly confidential corporate SOPs to public LLMs (like OpenAI/ChatGPT) violates enterprise data governance policies. | Potential data breach, regulatory non-compliance. |
| P4 | **Compliance Penalties** — Failing to properly train employees on security and compliance. | Multi-million dollar fines (SOC2, GDPR, ISO27001). |

## 3. Target Audience (User Personas)

### Persona 1: The Trainee (New Employee)
- **Role:** New hire in any department (Engineering, Sales, Legal, etc.)
- **Goal:** Understand complex company policies quickly and get certified to start working.
- **Pain Point:** Information overload from reading dozens of PDF documents without guidance.
- **Interaction:** Chat-based interface to learn, ask questions, and take assessments.

### Persona 2: The Supervisor (HR / Department Manager)
- **Role:** Manager responsible for approving the onboarding completion.
- **Goal:** Ensure the trainee truly understands critical policies before being certified.
- **Pain Point:** Currently has to manually review and quiz each new hire, taking hours per person.
- **Interaction:** Dashboard/API to review trainee transcripts and approve or reject certification.

## 4. Scope

### 4.1 In-Scope (MVP)
- Secure ingestion and retrieval of internal PDF/Markdown SOP documents.
- AI-driven curriculum generation based on employee role.
- Interactive tutoring with hallucination-free explanations grounded in SOPs.
- Automated assessment using open-ended questions and LLM-as-a-judge evaluation.
- Human-in-the-loop approval gate before certification.
- Real-time streaming of agent reasoning via SSE.
- Observability and tracing via Langfuse.

### 4.2 Out-of-Scope (Not in MVP)
- Frontend web UI (MVP is API-first; frontend can be added later).
- Multi-language support (MVP is English-only).
- Video or multimedia content generation.
- Integration with existing enterprise LMS platforms (e.g., SAP SuccessFactors, Workday).
- Mobile application.
- Multi-tenant architecture (MVP serves a single organization).

## 5. Core Features (MVP)

### F1. Secure Document Ingestion (RAG Pipeline)
- System can securely load and chunk internal PDF/Markdown documents (e.g., Security SOPs).
- Uses enterprise-grade vector embeddings to ensure data security.
- **Acceptance Criteria:** Given a 50-page PDF, the system chunks it and returns relevant passages with >85% contextual precision when queried.

### F2. Dynamic Curriculum Planner (Agent 1 — Planner)
- Analyzes the uploaded SOPs and automatically generates a step-by-step syllabus based on the employee's role.
- Outputs a structured learning plan with topic ordering and estimated completion time.
- **Acceptance Criteria:** Given an employee role (e.g., "Software Engineer"), the system generates a syllabus covering all relevant SOP sections in logical order.

### F3. Interactive Explainer (Agent 2 — Tutor)
- Acts as a tutor. Explains concepts step-by-step and answers trainee questions using strictly the context from the SOPs (preventing hallucination).
- Tracks which topics have been covered and updates the curriculum progress.
- **Acceptance Criteria:** Faithfulness score ≥ 95% — the agent must not fabricate information beyond the provided SOP documents.

### F4. LLM-as-a-Judge Assessor (Agent 3 — Evaluator)
- Generates open-ended questions (not just A/B/C/D) to test true comprehension.
- Evaluates the trainee's response against a strict grading rubric and provides actionable feedback.
- Uses a separate LLM instance as an impartial judge to grade responses.
- **Acceptance Criteria:** Given a correct answer, the system scores ≥ 80/100. Given a clearly wrong answer, the system scores < 50/100 and provides specific feedback.

### F5. Human-in-the-Loop (HITL) Approval Gate
- The workflow pauses (`interrupt`) before issuing a final compliance certificate, requiring the Supervisor to review the transcript and click "Approve" or "Require Retrain".
- **Acceptance Criteria:** The graph halts execution and persists state to database. Supervisor can resume the workflow via API call days later.

## 6. User Stories

| ID | As a... | I want to... | So that... |
|---|---|---|---|
| US-01 | Trainee | Upload my department's SOP documents | The system can teach me based on actual company policies |
| US-02 | Trainee | Receive a personalized learning plan based on my role | I don't waste time reading irrelevant sections |
| US-03 | Trainee | Ask questions about policies in natural language | I can clarify confusing sections without bothering a senior colleague |
| US-04 | Trainee | Take an assessment when I feel ready | I can prove my understanding and get certified |
| US-05 | Trainee | See real-time status of what the AI is doing | I understand the system is working and not frozen |
| US-06 | Supervisor | Review a trainee's full conversation transcript | I can verify they genuinely understand the material |
| US-07 | Supervisor | Approve or reject a trainee's certification | I maintain quality control over the onboarding process |

## 7. Non-Functional Requirements (NFRs)

| Category | Requirement | Target |
|---|---|---|
| **Security & Privacy** | Must support enterprise-grade API (Gemini) with zero-data-retention compliance. | No data used for model training by external APIs. |
| **Observability** | All agent steps, token usage, and latency must be logged and visualized. | Langfuse integration with full trace visibility. |
| **Performance** | Stream initial token response to the client. | < 2 seconds Time-to-First-Token (TTFT). |
| **Reliability** | Agent memory and conversation history must be persisted. | Sessions can be paused and resumed across server restarts. |
| **Scalability** | Backend must handle concurrent onboarding sessions. | FastAPI async with SSE streaming. |

## 8. Assumptions & Constraints

### Assumptions
- The organization has existing SOP documents in PDF or Markdown format.
- Users have a stable internet connection and access to a Gemini API Key.
- The Supervisor is available to review and approve within a reasonable timeframe.

### Constraints
- MVP is API-first (no frontend web UI in initial release).
- API inference speed is network-dependent.
- Document ingestion is limited to text-based PDFs (scanned image PDFs require OCR preprocessing, which is out-of-scope).

## 9. Risks & Mitigations

| Risk | Severity | Mitigation |
|---|---|---|
| LLM hallucinates information not in the SOPs. | **High** | Implement Corrective RAG, Faithfulness evaluation metric, and strict system prompts that forbid external knowledge. |
| API rate limits are exceeded during concurrent onboarding sessions. | **Medium** | Implement exponential backoff retries and use SSE streaming for better UX. |
| Assessor grades incorrectly (false pass/fail). | **Medium** | Use a separate LLM instance as judge. Include human review (HITL) as final safety net. |
| SOP documents are too long or complex for effective chunking. | **Low** | Implement hierarchical chunking with metadata (section headers, page numbers) for better retrieval precision. |

## 10. Success Metrics (KPIs)

| Metric | Category | Target |
|---|---|---|
| Average onboarding time | Business | Reduce from 14 days → 3 days |
| Faithfulness score | AI Quality (CLEAR) | ≥ 95% |
| Answer Relevancy score | AI Quality (CLEAR) | ≥ 90% |
| Time-to-First-Token (TTFT) | Performance | < 2 seconds |
| Supervisor approval rate (first attempt) | Business | ≥ 80% |

## 11. Future Enhancements (Post-MVP)

- **Frontend Web UI:** React/Next.js dashboard with real-time chat and progress visualization.
- **Multi-language Support:** Serve SOPs and assessments in multiple languages.
- **Analytics Dashboard:** Track organization-wide onboarding metrics (average time, common failure topics).
- **Integration Layer:** Connect with enterprise HR systems (SAP SuccessFactors, Workday, BambooHR).
- **Cross-Framework Delegation:** Delegate specialized tasks to CrewAI agents for advanced research.

---

*Document prepared for Portfolio Development & Architecture Planning.*
