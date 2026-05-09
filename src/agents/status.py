"""
Status Node — Progress Summary.

Returns a formatted summary of the trainee's onboarding progress,
including completed topics, current topic, assessment scores,
and overall certification status.
"""

import logging

from langchain_core.messages import AIMessage

from src.schemas.state import OnboardingState

logger = logging.getLogger(__name__)


def status_node(state: OnboardingState) -> dict:
    """
    Progress Summary Node.

    Reads the current state and generates a human-readable progress
    report for the trainee.

    Args:
        state: The current onboarding state.

    Returns:
        dict: State updates with progress summary message.
    """
    employee_name = state.get("employee_name", "Employee")
    syllabus = state.get("syllabus", [])
    current_topic = state.get("current_topic", "N/A")
    completed_topics = state.get("completed_topics", [])
    assessment_history = state.get("assessment_history", [])
    is_certified = state.get("is_certified", False)

    total_topics = len(syllabus)
    completed_count = len(completed_topics)
    progress_pct = (completed_count / total_topics * 100) if total_topics > 0 else 0

    logger.info(
        "Status check for %s: %d/%d topics completed (%.0f%%)",
        employee_name,
        completed_count,
        total_topics,
        progress_pct,
    )

    # Build progress bar
    filled = int(progress_pct // 10)
    bar = "█" * filled + "░" * (10 - filled)

    # Build topic list with status indicators
    topic_lines = []
    for topic in syllabus:
        if topic in completed_topics:
            # Find the score for this topic
            score = "—"
            for record in assessment_history:
                if record.get("topic") == topic and record.get("passed"):
                    score = f"{record['score']}/100"
                    break
            topic_lines.append(f"  ✅ {topic} (Score: {score})")
        elif topic == current_topic:
            topic_lines.append(f"  📖 {topic} ← Current")
        else:
            topic_lines.append(f"  ⬜ {topic}")

    topics_display = "\n".join(topic_lines) if topic_lines else "  No syllabus generated yet."

    # Certification status
    cert_status = "✅ CERTIFIED" if is_certified else "⏳ In Progress"

    summary = f"""
📊 Onboarding Progress — {employee_name}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Progress: [{bar}] {progress_pct:.0f}% ({completed_count}/{total_topics} topics)

Syllabus:
{topics_display}

Current Topic: {current_topic}
Certification:  {cert_status}
"""

    return {
        "messages": [AIMessage(content=summary.strip())],
        "current_agent": "status_node",
    }
