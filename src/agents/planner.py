import logging

from langchain_core.messages import AIMessage, SystemMessage
from pydantic import BaseModel, Field

from src.core.llm import get_llm
from src.schemas.state import OnboardingState

logger = logging.getLogger(__name__)


class SyllabusOutput(BaseModel):
    """Structured output for the curriculum planner."""
    syllabus: list[str] = Field(
        description="An ordered list of training topics the employee must complete."
    )


def planner_node(state: OnboardingState) -> dict:
    """
    Curriculum Planner Agent.
    Generates a personalized onboarding syllabus based on the employee's role.

    After generating the syllabus, sets the current_topic to the first topic
    and produces a welcome message for the trainee.

    Args:
        state: The current onboarding state.

    Returns:
        dict: The state updates (syllabus, current_topic, messages, current_agent).
    """
    role = state.get("employee_role", "General Employee")
    name = state.get("employee_name", "there")

    logger.info("Running Curriculum Planner for role: %s", role)

    system_prompt = f"""You are the Curriculum Planner for an Enterprise AI Onboarding system.
Your job is to generate an ordered list of training topics for a new employee.

Employee Role: {role}

Instructions:
1. Create a logical progression of topics.
2. Start with general company policies (e.g., "Security Policy", "Code of Conduct").
3. Progress to role-specific training.
4. Keep the list concise but comprehensive (3-5 topics).
5. Output ONLY the list of topics.
"""

    # Use structured output to guarantee a list of strings
    llm = get_llm(temperature=0.2)
    structured_llm = llm.with_structured_output(SyllabusOutput)

    from langchain_core.messages import SystemMessage, HumanMessage
    messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(content="Please generate the syllabus.")
    ]

    try:
        response = structured_llm.invoke(messages)
        syllabus = response.syllabus
    except Exception as e:
        logger.error("Failed to generate syllabus: %s", e)
        # Fallback syllabus
        syllabus = ["General Onboarding", "Security Awareness", "Role-specific Training"]

    # Set the first topic as current
    current_topic = syllabus[0] if syllabus else "General Onboarding"

    # Generate a welcome message with the learning plan
    topic_list = "\n".join(f"  {i+1}. {t}" for i, t in enumerate(syllabus))
    welcome_message = (
        f"👋 Welcome, {name}! I'm your AI Onboarding Assistant.\n\n"
        f"Based on your role as **{role}**, I've prepared the following learning plan:\n\n"
        f"{topic_list}\n\n"
        f"We'll start with **{current_topic}**.\n\n"
        f"You can:\n"
        f"  • Ask me to **explain** any topic\n"
        f"  • Say **\"quiz me\"** when you're ready for an assessment\n"
        f"  • Say **\"status\"** to check your progress\n\n"
        f"Let's begin! What would you like to know about {current_topic}?"
    )

    return {
        "syllabus": syllabus,
        "current_topic": current_topic,
        "messages": [AIMessage(content=welcome_message)],
        "current_agent": "planner_node",
    }
