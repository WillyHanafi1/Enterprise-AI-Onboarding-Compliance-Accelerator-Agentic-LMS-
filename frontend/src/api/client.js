/**
 * API Client for the Agentic LMS Backend.
 *
 * All endpoints are defined per the API Integration Contract
 * in FRONTEND_PRD.md.resolved (Section 4).
 *
 * Field names match the exact Pydantic schemas:
 *   - SessionCreateRequest: { employee_name, employee_role }
 *   - ChatRequest: { message }
 *   - SupervisorActionRequest: { feedback }
 */

const API_BASE = 'http://localhost:8000/api/v1';

/**
 * 4.1 — Create a new onboarding session.
 * POST /api/v1/sessions
 *
 * @param {string} employeeName
 * @param {string} employeeRole
 * @returns {Promise<{session_id: string, welcome_message: string, syllabus: string[]}>}
 */
export async function createSession(employeeName, employeeRole) {
  const res = await fetch(`${API_BASE}/sessions`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      employee_name: employeeName,
      employee_role: employeeRole,
    }),
  });

  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: 'Session creation failed' }));
    throw new Error(err.detail || `HTTP ${res.status}`);
  }

  return res.json();
}

/**
 * 4.2 — Get session status/progress.
 * GET /api/v1/sessions/{sessionId}/status
 *
 * @param {string} sessionId
 * @returns {Promise<object>}
 */
export async function getSessionStatus(sessionId) {
  const res = await fetch(`${API_BASE}/sessions/${sessionId}/status`);

  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: 'Failed to get status' }));
    throw new Error(err.detail || `HTTP ${res.status}`);
  }

  return res.json();
}

/**
 * 4.3 — Send chat message (SSE streaming).
 * POST /api/v1/sessions/{sessionId}/chat
 *
 * Returns the raw Response so the caller can read the stream.
 * The caller MUST check Content-Type to distinguish SSE vs JSON:
 *   - "text/event-stream" → parse as SSE
 *   - "application/json"  → parse as JSON (edge case: already certified / awaiting approval)
 *
 * @param {string} sessionId
 * @param {string} message
 * @returns {Promise<Response>}
 */
export async function sendChatMessage(sessionId, message) {
  const res = await fetch(`${API_BASE}/sessions/${sessionId}/chat`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ message }),
  });

  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: 'Chat request failed' }));
    throw new Error(err.detail || `HTTP ${res.status}`);
  }

  return res;
}

/**
 * 4.5 — Supervisor approves certification.
 * POST /api/v1/sessions/{sessionId}/approve
 *
 * @param {string} sessionId
 * @param {string} [feedback]
 * @returns {Promise<{session_id: string, action: string, message: string, is_certified: boolean}>}
 */
export async function approveSession(sessionId, feedback) {
  const body = feedback ? { feedback } : {};
  const res = await fetch(`${API_BASE}/sessions/${sessionId}/approve`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  });

  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: 'Approve failed' }));
    throw new Error(err.detail || `HTTP ${res.status}`);
  }

  return res.json();
}

/**
 * 4.6 — Supervisor rejects certification.
 * POST /api/v1/sessions/{sessionId}/reject
 *
 * @param {string} sessionId
 * @param {string} [feedback]
 * @returns {Promise<{session_id: string, action: string, message: string, is_certified: boolean}>}
 */
export async function rejectSession(sessionId, feedback) {
  const body = feedback ? { feedback } : {};
  const res = await fetch(`${API_BASE}/sessions/${sessionId}/reject`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  });

  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: 'Reject failed' }));
    throw new Error(err.detail || `HTTP ${res.status}`);
  }

  return res.json();
}

/**
 * Submit user feedback for a trace.
 * POST /api/v1/sessions/{sessionId}/feedback
 *
 * @param {string} sessionId
 * @param {{trace_id?: string, score: number, comment?: string, name?: string}} feedback
 * @returns {Promise<object>}
 */
export async function submitFeedback(sessionId, feedback) {
  const res = await fetch(`${API_BASE}/sessions/${sessionId}/feedback`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(feedback),
  });

  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: 'Feedback submission failed' }));
    throw new Error(err.detail || `HTTP ${res.status}`);
  }

  return res.json();
}
