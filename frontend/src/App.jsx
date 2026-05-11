import { useState, useCallback, useRef } from 'react';
import { startActiveObservation } from '@langfuse/tracing';

import SetupScreen from './components/SetupScreen';
import Sidebar from './components/Sidebar';
import ChatWindow from './components/ChatWindow';
import SupervisorModal from './components/SupervisorModal';

import { createSession, sendChatMessage, approveSession, rejectSession } from './api/client';
import { parseSSEStream } from './api/sseParser';

import './App.css';

/**
 * App — Root component with centralized state management.
 *
 * State architecture matches FRONTEND_PRD.md.resolved Section 1.2.
 */
export default function App() {
  // === Session State ===
  const [session, setSession] = useState(null);

  // === Chat State ===
  const [messages, setMessages] = useState([]);

  // === Agent Lifecycle ===
  const [agentState, setAgentState] = useState('idle');
  const [activeAgent, setActiveAgent] = useState(null);

  // === Curriculum Progress ===
  const [syllabus, setSyllabus] = useState([]);
  const [completedTopics, setCompletedTopics] = useState([]);
  const [currentTopic, setCurrentTopic] = useState('');

  // === Assessment ===
  const [quizScore, setQuizScore] = useState(0);
  const [isCertified, setIsCertified] = useState(false);

  // === Supervisor HITL ===
  const [requiresApproval, setRequiresApproval] = useState(false);

  // BUG-9 FIX: Ref to track approval state for the done handler
  // This avoids the stale closure problem where `agentState` is captured at render time
  const approvalFlagRef = useRef(false);

  // === UI State ===
  const [error, setError] = useState('');

  // ─── Helper: add a message to chat ───
  const addMessage = useCallback((role, content, agent = null, traceId = null) => {
    setMessages((prev) => [
      ...prev,
      { role, content, agent, traceId, timestamp: new Date() },
    ]);
  }, []);

  // ─── Helper: update the last assistant message (for streaming) ───
  const appendToLastAssistant = useCallback((content) => {
    setMessages((prev) => {
      const updated = [...prev];
      const lastIdx = updated.length - 1;
      if (lastIdx >= 0 && updated[lastIdx].role === 'assistant') {
        updated[lastIdx] = {
          ...updated[lastIdx],
          content: updated[lastIdx].content + content,
        };
      }
      return updated;
    });
  }, []);

  // ═══════════════════════════════════════
  //  1. Session Creation (POST /sessions)
  // ═══════════════════════════════════════
  async function handleStartSession(name, role) {
    const data = await createSession(name, role);

    setSession({
      session_id: data.session_id,
      employee_name: name,
      employee_role: role,
    });
    setSyllabus(data.syllabus || []);

    // Add the welcome message from the Planner agent
    if (data.welcome_message) {
      addMessage('assistant', data.welcome_message, 'planner_node');
    }
  }

  // ═══════════════════════════════════════
  //  2. Chat with SSE Streaming
  // ═══════════════════════════════════════
  async function handleSendMessage(text) {
    if (!session) return;

    // Add user message to UI immediately
    addMessage('user', text);
    setAgentState('typing');
    setError('');

    try {
      await startActiveObservation('send-message', async (span) => {
        span.update({ input: { text } });
        
        const response = await sendChatMessage(session.session_id, text);

        // Edge case: backend returns JSON instead of SSE
        // (when already certified or awaiting approval)
        const contentType = response.headers.get('Content-Type') || '';

        if (contentType.includes('application/json')) {
          const data = await response.json();
          addMessage('system', data.message, data.agent);
          if (data.requires_approval) {
            setAgentState('requires_approval');
            setRequiresApproval(true);
          } else {
            setAgentState('idle');
          }
          span.update({ output: data });
          return;
        }

        // Normal SSE streaming
        let currentAgentName = null;

        await parseSSEStream(response, {
          agent_start: (data) => {
            currentAgentName = data.agent;
            setActiveAgent(data.agent);
            setAgentState('typing');
            // Create an empty assistant bubble for streaming into
            // Include trace_id for feedback loop
            addMessage('assistant', '', data.agent, data.trace_id);
          },

          token: (data) => {
            appendToLastAssistant(data.content || '');
          },

          agent_end: () => {
            setAgentState('idle');
          },

          state_update: (data) => {
            if (data.current_topic !== undefined) setCurrentTopic(data.current_topic);
            if (data.quiz_score !== undefined) setQuizScore(data.quiz_score);
            if (data.completed_topics !== undefined) setCompletedTopics(data.completed_topics);
            if (data.is_certified) {
              setIsCertified(true);
              setAgentState('idle');
            }
          },

          requires_approval: (data) => {
            approvalFlagRef.current = true;
            setAgentState('requires_approval');
            setRequiresApproval(true);
            if (data.message) {
              addMessage('system', data.message);
            }
          },

          error: (data) => {
            setError(data.detail || 'An error occurred');
            setAgentState('idle');
            span.update({ level: 'ERROR', statusMessage: data.detail });
          },

          done: () => {
            // BUG-9 FIX: Use ref instead of stale closure
            if (!approvalFlagRef.current) {
              setAgentState('idle');
            }
            setActiveAgent(null);
            approvalFlagRef.current = false;
            span.update({ output: 'stream finished' });
          },
        });
      });
    } catch (err) {
      setError(err.message || 'Failed to send message');
      setAgentState('idle');
    }
  }

  // ═══════════════════════════════════════
  //  3. Supervisor Approve
  // ═══════════════════════════════════════
  async function handleApprove(feedback) {
    try {
      await startActiveObservation('supervisor-approve', async (span) => {
        span.update({ input: { feedback } });
        const data = await approveSession(session.session_id, feedback);
        setRequiresApproval(false);
        setIsCertified(data.is_certified);
        addMessage('assistant', data.message, 'certifier_node');
        setAgentState('idle');
        span.update({ output: data });
      });
    } catch (err) {
      setError(err.message || 'Approval failed');
    }
  }

  // ═══════════════════════════════════════
  //  4. Supervisor Reject
  // ═══════════════════════════════════════
  async function handleReject(feedback) {
    try {
      await startActiveObservation('supervisor-reject', async (span) => {
        span.update({ input: { feedback } });
        const data = await rejectSession(session.session_id, feedback);
        setRequiresApproval(false);
        addMessage('system', data.message);
        setAgentState('idle');
        setQuizScore(0);
        span.update({ output: data });
      });
    } catch (err) {
      setError(err.message || 'Rejection failed');
    }
  }

  // ═══════════════════════════════════════
  //  5. Feedback Loop
  // ═══════════════════════════════════════
  async function handleFeedback(traceId, score, comment = '') {
    if (!session || !traceId) return;
    try {
      await submitFeedback(session.session_id, {
        trace_id: traceId,
        score,
        comment,
      });
    } catch (err) {
      console.error('Feedback failed:', err);
    }
  }

  // ═══════════════════════════════════════
  //  Render
  // ═══════════════════════════════════════

  // View 1: Setup Screen (no session yet)
  if (!session) {
    return <SetupScreen onStartSession={handleStartSession} />;
  }

  // View 2–4: Dashboard
  return (
    <div className="dashboard">
      <Sidebar
        session={session}
        syllabus={syllabus}
        completedTopics={completedTopics}
        currentTopic={currentTopic}
        quizScore={quizScore}
        isCertified={isCertified}
        agentState={agentState}
      />

      <ChatWindow
        messages={messages}
        agentState={agentState}
        activeAgent={activeAgent}
        isCertified={isCertified}
        requiresApproval={requiresApproval}
        onSendMessage={handleSendMessage}
        onFeedback={handleFeedback}
      />

      {/* HITL Supervisor Modal (View 3) */}
      {requiresApproval && (
        <SupervisorModal
          session={session}
          quizScore={quizScore}
          completedTopics={completedTopics}
          syllabus={syllabus}
          onApprove={handleApprove}
          onReject={handleReject}
        />
      )}

      {/* Error Toast */}
      {error && (
        <div className="toast" onClick={() => setError('')}>
          ⚠️ {error}
        </div>
      )}
    </div>
  );
}
