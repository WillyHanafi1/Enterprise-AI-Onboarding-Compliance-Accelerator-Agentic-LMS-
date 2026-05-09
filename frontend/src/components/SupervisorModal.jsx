import { useState } from 'react';
import { ShieldAlert, CheckCircle2, XCircle, Loader2 } from 'lucide-react';
import styles from './SupervisorModal.module.css';

/**
 * SupervisorModal — HITL approval/rejection overlay (View 3 in wireframe).
 *
 * Shown when agentState === 'requires_approval'.
 * Collects optional feedback and calls onApprove or onReject.
 */
export default function SupervisorModal({
  session,
  quizScore,
  completedTopics,
  syllabus,
  onApprove,
  onReject,
}) {
  const [feedback, setFeedback] = useState('');
  const [loading, setLoading] = useState(false);

  async function handleApprove() {
    setLoading(true);
    try {
      await onApprove(feedback || undefined);
    } catch {
      setLoading(false);
    }
  }

  async function handleReject() {
    setLoading(true);
    try {
      await onReject(feedback || undefined);
    } catch {
      setLoading(false);
    }
  }

  return (
    <div className={styles.overlay}>
      <div className={styles.modal}>
        {/* Header */}
        <div className={styles.header}>
          <div className={styles.headerIcon}>
            <ShieldAlert size={22} />
          </div>
          <div className={styles.headerText}>
            <h2>Supervisor Review Required</h2>
            <p>Certification pending your approval</p>
          </div>
        </div>

        {/* Trainee Summary */}
        <div className={styles.summary}>
          <div className={styles.summaryRow}>
            <span className={styles.summaryLabel}>Trainee</span>
            <span className={styles.summaryValue}>{session.employee_name}</span>
          </div>
          <div className={styles.summaryRow}>
            <span className={styles.summaryLabel}>Role</span>
            <span className={styles.summaryValue}>{session.employee_role}</span>
          </div>
          <div className={styles.summaryRow}>
            <span className={styles.summaryLabel}>Final Score</span>
            <span className={styles.summaryValueHighlight}>{quizScore} / 100</span>
          </div>
          <div className={styles.summaryRow}>
            <span className={styles.summaryLabel}>Topics Passed</span>
            <span className={styles.summaryValue}>
              {completedTopics.length} / {syllabus.length}
            </span>
          </div>
        </div>

        {/* Feedback Input */}
        <div className={styles.feedbackGroup}>
          <label htmlFor="supervisor-feedback" className={styles.feedbackLabel}>
            Feedback (optional)
          </label>
          <textarea
            id="supervisor-feedback"
            className={styles.feedbackInput}
            placeholder="Add your review notes here..."
            value={feedback}
            onChange={(e) => setFeedback(e.target.value)}
            disabled={loading}
          />
        </div>

        {/* Action Buttons */}
        <div className={styles.actions}>
          <button
            className={styles.btnApprove}
            onClick={handleApprove}
            disabled={loading}
          >
            {loading ? (
              <Loader2 size={16} className="spin" />
            ) : (
              <CheckCircle2 size={16} />
            )}
            Approve
          </button>
          <button
            className={styles.btnReject}
            onClick={handleReject}
            disabled={loading}
          >
            {loading ? (
              <Loader2 size={16} className="spin" />
            ) : (
              <XCircle size={16} />
            )}
            Reject
          </button>
        </div>
      </div>
    </div>
  );
}
