"""
Certifier Agent — Terminal Node.

Issues a compliance certificate after all conditions are met:
    1. All syllabus topics have been completed
    2. All assessments passed (score >= 80)
    3. Supervisor approval via HITL (Phase 5)

In Phase 4, the Certifier runs automatically after all topics pass.
The HITL interrupt_before gate will be added in Phase 5.
"""

import logging
from datetime import UTC, datetime

from langchain_core.messages import AIMessage

from src.schemas.state import OnboardingState

logger = logging.getLogger(__name__)


def certifier_node(state: OnboardingState) -> dict:
    """
    Certifier Terminal Node.

    Generates the final compliance certificate and marks the
    onboarding session as certified.

    The certificate includes:
    - Employee name and role
    - List of completed topics with scores
    - Certification timestamp
    - Overall pass/fail summary

    Args:
        state: The current onboarding state.

    Returns:
        dict: State updates marking certification complete.
    """
    employee_name = state.get("employee_name", "Employee")
    employee_role = state.get("employee_role", "General")
    completed_topics = state.get("completed_topics", [])
    assessment_history = state.get("assessment_history", [])

    logger.info(
        "Issuing certification for %s (%s). Topics completed: %d",
        employee_name,
        employee_role,
        len(completed_topics),
    )

    # Build assessment summary
    assessment_lines = []
    for record in assessment_history:
        if record.get("passed"):
            assessment_lines.append(
                f"  ✅ {record['topic']}: {record['score']}/100"
            )

    assessment_summary = "\n".join(assessment_lines) if assessment_lines else "  No records."

    timestamp = datetime.now(UTC).strftime("%Y-%m-%d %H:%M UTC")

    certificate_message = f"""
🎓 ═══════════════════════════════════════════════
   COMPLIANCE CERTIFICATION — ISSUED
═══════════════════════════════════════════════════

Employee:  {employee_name}
Role:      {employee_role}
Date:      {timestamp}

Topics Completed:
{assessment_summary}

Status: ✅ CERTIFIED

All required onboarding modules have been completed
and assessed successfully. This employee is cleared
to begin their role-specific duties.

═══════════════════════════════════════════════════
"""

    return {
        "messages": [AIMessage(content=certificate_message.strip())],
        "is_certified": True,
        "current_agent": "certifier_node",
    }
