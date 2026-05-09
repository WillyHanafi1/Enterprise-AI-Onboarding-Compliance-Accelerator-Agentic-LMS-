import { useState } from 'react';
import { Zap, ArrowRight, Loader2 } from 'lucide-react';
import styles from './SetupScreen.module.css';

const ROLES = [
  'Software Engineer',
  'Compliance Officer',
  'Financial Analyst',
  'IT Administrator',
  'General Staff',
];

/**
 * SetupScreen — Session creation form (View 1 in wireframe).
 *
 * Collects employee_name and employee_role, then calls onStartSession.
 */
export default function SetupScreen({ onStartSession }) {
  const [name, setName] = useState('');
  const [role, setRole] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const canSubmit = name.trim().length > 0 && role.length > 0 && !loading;

  async function handleSubmit(e) {
    e.preventDefault();
    if (!canSubmit) return;

    setLoading(true);
    setError('');

    try {
      await onStartSession(name.trim(), role);
    } catch (err) {
      setError(err.message || 'Failed to create session. Is the backend running?');
      setLoading(false);
    }
  }

  return (
    <div className={styles.setupOverlay}>
      <form className={styles.setupCard} onSubmit={handleSubmit}>
        <div className={styles.logo}>
          <Zap size={28} className={styles.logoIcon} />
          <span className={styles.logoText}>NexusPay AI</span>
        </div>
        <p className={styles.subtitle}>Enterprise Compliance Onboarding</p>

        <div className={styles.formGroup}>
          <label htmlFor="setup-name" className={styles.label}>
            Full Name
          </label>
          <input
            id="setup-name"
            type="text"
            className={styles.input}
            placeholder="e.g., Willy Hanafi"
            value={name}
            onChange={(e) => setName(e.target.value)}
            maxLength={100}
            autoFocus
          />
        </div>

        <div className={styles.formGroup}>
          <label htmlFor="setup-role" className={styles.label}>
            Job Role
          </label>
          <select
            id="setup-role"
            className={styles.select}
            value={role}
            onChange={(e) => setRole(e.target.value)}
          >
            <option value="">Select your role...</option>
            {ROLES.map((r) => (
              <option key={r} value={r}>
                {r}
              </option>
            ))}
          </select>
        </div>

        <button
          type="submit"
          className={styles.submitBtn}
          disabled={!canSubmit}
        >
          {loading ? (
            <>
              <Loader2 size={18} className="spin" />
              Initializing Session...
            </>
          ) : (
            <>
              Start Onboarding
              <ArrowRight size={18} />
            </>
          )}
        </button>

        {error && <div className={styles.error}>{error}</div>}

        <p className={styles.footer}>Powered by LangGraph &amp; Gemini AI</p>
      </form>
    </div>
  );
}
