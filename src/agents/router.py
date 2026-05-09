"""
Router Agent — Intent Classification.

Classifies user messages into one of three intents:
    - "learn"  → Route to Explainer Agent (Tutor)
    - "quiz"   → Route to Assessor Agent (Evaluator)
    - "status" → Route to Progress Summary Node

Uses LLM-based classification with structured output for accuracy
and robustness against varied natural language inputs.
"""

import logging
from typing import Literal

from langchain_core.messages import HumanMessage, SystemMessage
from pydantic import BaseModel, Field

from src.core.llm import get_llm

logger = logging.getLogger(__name__)


class RouterDecision(BaseModel):
    """Structured output schema for the router's classification."""

    intent: Literal["learn", "quiz", "status"] = Field(
        description="The classified intent of the user's message."
    )
    reasoning: str = Field(
        description="Brief explanation of why this intent was chosen."
    )


# System prompt that defines the classification rules
ROUTER_SYSTEM_PROMPT = """You are an intent classifier for an Enterprise AI Onboarding system.
Your ONLY job is to classify the user's message into one of three categories:

1. "learn" — The user wants to learn, ask a question, get an explanation, or discuss a topic.
   Examples: "teach me about X", "what is the policy on Y?", "explain Z", "tell me more", "I don't understand"

2. "quiz" — The user wants to be tested, assessed, or take a quiz.
   Examples: "quiz me", "test me", "I'm ready for the assessment", "evaluate me", "let's do the exam"

3. "status" — The user wants to check their progress, see scores, or view completed topics.
   Examples: "what's my progress?", "how am I doing?", "show my scores", "what topics are left?"

Classify the LAST user message. If unsure, default to "learn".
"""


def route_intent(state: dict) -> str:
    """
    Classifies user intent via LLM structured output.

    This function is used as a conditional edge function in LangGraph.
    It reads the last user message from state and returns a routing key.

    Args:
        state: The current OnboardingState dictionary.

    Returns:
        One of: "learn", "quiz", or "status".
    """
    messages = state.get("messages", [])

    # Find the last human message
    last_human_msg = None
    for msg in reversed(messages):
        if isinstance(msg, HumanMessage):
            last_human_msg = msg
            break

    if not last_human_msg:
        logger.warning("No human message found in state. Defaulting to 'learn'.")
        return "learn"

    logger.info("Routing intent for message: '%s'", last_human_msg.content[:80])

    try:
        llm = get_llm(temperature=0.0)
        structured_llm = llm.with_structured_output(RouterDecision)

        result = structured_llm.invoke([
            SystemMessage(content=ROUTER_SYSTEM_PROMPT),
            HumanMessage(content=last_human_msg.content),
        ])

        logger.info(
            "Router decision: intent=%s, reasoning=%s",
            result.intent,
            result.reasoning[:100],
        )
        return result.intent

    except Exception as e:
        logger.error("Router classification failed: %s. Defaulting to 'learn'.", e)
        return "learn"
