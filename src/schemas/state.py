import operator
from typing import Annotated, Any, TypedDict

from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages


class OnboardingState(TypedDict):
    """
    The central state object that flows through all nodes in the graph.
    Every agent reads from and writes to this shared state.
    """

    # === Conversation Memory ===
    messages: Annotated[list[BaseMessage], add_messages]

    # === Employee Context ===
    employee_role: str                   # e.g., "Software Engineer", "Sales"
    employee_name: str                   # For personalized interactions

    # === Curriculum Tracking ===
    syllabus: list[str]                  # Ordered list of topics to cover
    current_topic: str                   # Active topic being studied
    # Use operator.add to append elements to the list across graph steps
    completed_topics: Annotated[list[str], operator.add]

    # === Assessment Tracking ===
    quiz_score: int                      # Latest score (0-100)
    failed_attempts: int                 # Consecutive failures on current topic
    assessment_history: Annotated[list[dict[str, Any]], operator.add]

    # === Workflow Control ===
    is_certified: bool                   # True if passed & supervisor approved
    requires_human_review: bool          # Flag to trigger HITL interrupt
    current_agent: str | None         # Which agent is currently active
