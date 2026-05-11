import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { useRef, useEffect, useState } from 'react';
import { Bot, Send, MessageSquare, FileText, ThumbsUp, ThumbsDown } from 'lucide-react';
import styles from './ChatWindow.module.css';

/* Agent node name → friendly display name */
const AGENT_LABELS = {
  planner_node: '🗺️ Curriculum Planner',
  explainer_node: '📖 Explainer Agent',
  assessor_node: '📝 Assessor Agent',
  certifier_node: '🎓 Certifier Agent',
  status_node: '📊 Status Report',
  system: '⚙️ System',
};

function formatTime(date) {
  return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
}

/**
 * CitationChip — Renders the [Source X: ...] blocks as UI chips.
 */
function CitationChip({ text }) {
  // Regex to match [Source X: Filename, Page Y]
  const match = text.match(/\[Source (\d+): (.*?)\]/);
  if (!match) return null;

  const [, id, details] = match;
  return (
    <div className={styles.sourceChip}>
      <FileText size={12} />
      <span>Source {id}: {details}</span>
    </div>
  );
}

/**
 * ChatWindow — Main chat area with message list, typing indicator, and input.
 */
export default function ChatWindow({
  messages,
  agentState,
  activeAgent,
  isCertified,
  requiresApproval,
  onSendMessage,
}) {
  const [inputValue, setInputValue] = useState('');
  const listRef = useRef(null);
  const textareaRef = useRef(null);

  // Auto-scroll to bottom when messages change
  useEffect(() => {
    if (listRef.current) {
      listRef.current.scrollTop = listRef.current.scrollHeight;
    }
  }, [messages, agentState]);

  const isInputDisabled =
    agentState === 'typing' ||
    agentState === 'evaluating' ||
    agentState === 'requires_approval' ||
    isCertified;

  function handleSend() {
    const msg = inputValue.trim();
    if (!msg || isInputDisabled) return;
    onSendMessage(msg);
    setInputValue('');
    // Re-focus textarea
    if (textareaRef.current) textareaRef.current.focus();
  }

  function handleKeyDown(e) {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  }

  return (
    <div className={styles.chatContainer}>
      {/* Header */}
      <div className={styles.chatHeader}>
        <MessageSquare size={18} className={styles.chatHeaderIcon} />
        <span className={styles.chatHeaderTitle}>Onboarding Chat</span>
        {activeAgent && (
          <span className={styles.chatHeaderAgent}>
            — {AGENT_LABELS[activeAgent] || activeAgent}
          </span>
        )}
      </div>

      {/* Message List */}
      <div className={styles.messageList} ref={listRef}>
        {messages.map((msg, idx) => {
          const bubbleClass = [
            styles.messageBubble,
            msg.role === 'user'
              ? styles.messageUser
              : msg.role === 'system'
                ? styles.messageSystem
                : styles.messageAssistant,
          ].join(' ');

          // Process citations: Separate lines starting with [Source X: ...]
          const lines = msg.content.split('\n');
          const citations = [];
          const remainingLines = [];
          
          lines.forEach(line => {
            const trimmed = line.trim();
            if (trimmed.startsWith('[Source ') && trimmed.endsWith(']')) {
              citations.push(trimmed);
            } else {
              remainingLines.push(line);
            }
          });

          const contentText = remainingLines.join('\n').trim();

          return (
            <div key={idx} className={bubbleClass}>
              {msg.role === 'assistant' && msg.agent && (
                <div className={styles.messageAgent}>
                  <Bot size={14} />
                  {AGENT_LABELS[msg.agent] || msg.agent}
                </div>
              )}

              {/* Render Citations first if any */}
              {citations.map((c, i) => (
                <CitationChip key={i} text={c} />
              ))}

              {/* Render content as Markdown */}
              <div className={styles.markdown}>
                <ReactMarkdown remarkPlugins={[remarkGfm]}>
                  {contentText}
                </ReactMarkdown>
              </div>

              <div className={styles.messageFooter}>
                {msg.timestamp && (
                  <div className={styles.messageTime}>
                    {formatTime(msg.timestamp)}
                  </div>
                )}

                {msg.role === 'assistant' && msg.traceId && (
                  <div className={styles.feedbackButtons}>
                    <button 
                      onClick={() => onFeedback(msg.traceId, 1)} 
                      className={styles.feedbackBtn}
                      title="Helpful"
                    >
                      <ThumbsUp size={12} />
                    </button>
                    <button 
                      onClick={() => onFeedback(msg.traceId, -1)} 
                      className={styles.feedbackBtn}
                      title="Not helpful"
                    >
                      <ThumbsDown size={12} />
                    </button>
                  </div>
                )}
              </div>
            </div>
          );
        })}

        {/* Typing Indicator */}
        {(agentState === 'typing' || agentState === 'evaluating') && (
          <div className={styles.typingIndicator}>
            <span className={styles.typingLabel}>
              {AGENT_LABELS[activeAgent] || 'Agent'} is{' '}
              {agentState === 'evaluating' ? 'evaluating...' : 'thinking...'}
            </span>
            <span className={styles.typingDots}>
              <span className={styles.typingDot} />
              <span className={styles.typingDot} />
              <span className={styles.typingDot} />
            </span>
          </div>
        )}
      </div>

      {/* Input Area */}
      {isCertified ? (
        <div className={styles.disabledMsg}>
          🎓 Session completed. You are certified!
        </div>
      ) : requiresApproval ? (
        <div className={styles.disabledMsg}>
          ⏳ Awaiting supervisor review — input disabled.
        </div>
      ) : (
        <div className={styles.inputArea}>
          <div className={styles.inputRow}>
            <textarea
              ref={textareaRef}
              className={styles.textarea}
              placeholder="Type your message..."
              value={inputValue}
              onChange={(e) => setInputValue(e.target.value)}
              onKeyDown={handleKeyDown}
              disabled={isInputDisabled}
              rows={1}
            />
            <button
              className={styles.sendBtn}
              onClick={handleSend}
              disabled={isInputDisabled || !inputValue.trim()}
              aria-label="Send message"
            >
              <Send size={18} />
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
