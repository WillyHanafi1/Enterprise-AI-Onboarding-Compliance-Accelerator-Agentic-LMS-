import {
  Zap, User, CheckCircle2, BookOpen, Lock,
  BarChart3, BookOpenCheck, Activity, Award,
} from 'lucide-react';
import styles from './Sidebar.module.css';

/**
 * Sidebar — Left panel with ProfileCard, SyllabusTracker, and ScorePanel.
 */
export default function Sidebar({
  session,
  syllabus,
  completedTopics,
  currentTopic,
  quizScore,
  isCertified,
  agentState,
}) {
  const topicsComplete = completedTopics.length;
  const topicsTotal = syllabus.length;

  function getTopicStatus(topic) {
    if (completedTopics.includes(topic)) return 'completed';
    if (topic === currentTopic) return 'active';
    return 'locked';
  }

  function getStatusText() {
    if (isCertified) return '🎓 CERTIFIED';
    if (agentState === 'requires_approval') return '⏳ REVIEW';
    return '📖 Training';
  }

  return (
    <aside className={styles.sidebar}>
      {/* Brand */}
      <div className={styles.brand}>
        <Zap size={22} className={styles.brandIcon} />
        <span className={styles.brandName}>NexusPay LMS</span>
      </div>

      {/* Profile Card */}
      <div className={styles.profileCard}>
        <div className={styles.profileName}>
          <User size={16} />
          {session.employee_name}
        </div>
        <div className={styles.profileRole}>{session.employee_role}</div>
        {isCertified && (
          <div className={styles.certifiedBadge}>
            <Award size={12} /> CERTIFIED
          </div>
        )}
      </div>

      {/* Syllabus Tracker */}
      <div className={styles.syllabusSection}>
        <div className={styles.sectionTitle}>Syllabus</div>
        <ul className={styles.topicList}>
          {syllabus.map((topic) => {
            const status = getTopicStatus(topic);
            const itemClass = [
              styles.topicItem,
              status === 'completed' ? styles.topicCompleted : '',
              status === 'active' ? styles.topicActive : '',
              status === 'locked' ? styles.topicLocked : '',
            ]
              .filter(Boolean)
              .join(' ');

            return (
              <li key={topic} className={itemClass}>
                <span className={styles.topicIcon}>
                  {status === 'completed' && <CheckCircle2 size={16} />}
                  {status === 'active' && <BookOpen size={16} />}
                  {status === 'locked' && <Lock size={14} />}
                </span>
                <span className={styles.topicName} title={topic}>
                  {topic}
                </span>
              </li>
            );
          })}
        </ul>
      </div>

      {/* Metrics / Score Panel */}
      <div className={styles.metricsSection}>
        <div className={styles.sectionTitle}>Metrics</div>

        <div className={styles.metricRow}>
          <BarChart3 size={14} className={styles.metricIcon} />
          <span>Score</span>
          <span className={styles.metricValue}>{quizScore} / 100</span>
        </div>

        <div className={styles.metricRow}>
          <BookOpenCheck size={14} className={styles.metricIcon} />
          <span>Topics</span>
          <span className={styles.metricValue}>
            {topicsComplete} / {topicsTotal}
          </span>
        </div>

        <div className={styles.metricRow}>
          <Activity size={14} className={styles.metricIcon} />
          <span>Status</span>
          <span className={styles.metricValue}>{getStatusText()}</span>
        </div>

        {/* Progress Bar — BUG-8 FIX: Shows topic completion %, not quiz score */}
        <div className={styles.scoreBarContainer}>
          <div className={styles.scoreBarTrack}>
            <div
              className={styles.scoreBarFill}
              style={{ width: `${topicsTotal > 0 ? Math.round((topicsComplete / topicsTotal) * 100) : 0}%` }}
            />
          </div>
          <div className={styles.scoreLabel}>
            <span>Progress</span>
            <span>{topicsTotal > 0 ? Math.round((topicsComplete / topicsTotal) * 100) : 0}%</span>
          </div>
        </div>
      </div>
    </aside>
  );
}
