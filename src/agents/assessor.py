"""
Assessor Agent — Knowledge Testing & Grading.

This module implements the Assessor (Evaluator) agent that tests
employee knowledge on each onboarding topic. It uses a ReAct agent
pattern with tools for generating rubrics and submitting grades.

BUG-6 FIX: Added deduplication guard for completed_topics.
BUG-12 FIX: Removed duplicate imports.
ISSUE-13 FIX: Cached agent instance at module level.
"""

import logging
from typing import Any

from langchain_core.messages import AIMessage, SystemMessage
from langchain_core.tools import tool
from langgraph.prebuilt import create_react_agent

from src.agents.tools import generate_evaluation_rubric, retrieve_internal_policies
from src.core.llm import get_llm
from src.schemas.state import OnboardingState

logger = logging.getLogger(__name__)

# ISSUE-13 FIX: Module-level agent cache (avoids recreating LLM + sub-graph per invocation)
_assessor_agent = None


@tool
def submit_grade(score: int, feedback: str) -> str:
    """
    Call this tool to officially submit the user's grade for the current topic.
    You MUST call this tool once you have evaluated the user's answer.

    Args:
        score: The integer score from 0 to 100.
        feedback: Constructive feedback explaining the score.
    """
    # This tool is a dummy tool for the LLM to call.
    # The actual state update happens by inspecting the tool calls in the assessor_node.
    return "Grade successfully submitted. Now tell the user their score and feedback."


def get_assessor_agent():
    """
    Creates and returns the Assessor Agent as a compiled sub-graph.

    ISSUE-13 FIX: Agent is cached after first creation.
    """
    global _assessor_agent
    if _assessor_agent is not None:
        return _assessor_agent

    llm = get_llm(temperature=0.2)
    tools = [retrieve_internal_policies, generate_evaluation_rubric, submit_grade]

    def state_modifier(state: dict) -> list:
        topic = state.get("current_topic", "General Onboarding")
        system_prompt = f"""You are the Assessor (Evaluator) for an Enterprise AI Onboarding system.
Your job is to test the user's knowledge on the topic: '{topic}'.

Instructions:
1. If you haven't asked a question yet, ask a practical, case-study style question about '{topic}'.
   (Use retrieve_internal_policies to get context for a good question).
2. If the user has answered your question:
   a. Use `generate_evaluation_rubric` to get the grading criteria.
   b. Evaluate their answer strictly against the rubric.
   c. You MUST call the `submit_grade` tool to record the score (0-100) and feedback.
   d. After calling `submit_grade`, explain to the user why they got that score.
"""
        return [SystemMessage(content=system_prompt)] + state.get("messages", [])

    _assessor_agent = create_react_agent(llm, tools, prompt=state_modifier)
    return _assessor_agent


def assessor_node(state: OnboardingState) -> dict:
    """
    Assessor node wrapper that runs the agent and then processes tool calls
    to update state variables like quiz_score and assessment_history.
    """
    agent = get_assessor_agent()
    try:
        result = agent.invoke(state)
        new_messages = result["messages"][len(state.get("messages", [])):]
    except Exception as e:
        logger.error("Assessor agent failed: %s", e)
        return {"messages": [AIMessage(content="Error during assessment.")]}

    # Inspect messages for the submit_grade tool call
    quiz_score = None
    feedback = ""
    for msg in new_messages:
        if isinstance(msg, AIMessage) and msg.tool_calls:
            for tool_call in msg.tool_calls:
                if tool_call["name"] == "submit_grade":
                    args = tool_call["args"]
                    quiz_score = args.get("score")
                    feedback = args.get("feedback")
                    logger.info("Grade submitted by LLM: score=%s", quiz_score)

    state_updates: dict[str, Any] = {
        "messages": new_messages,
        "current_agent": "assessor_node"
    }

    if quiz_score is not None:
        state_updates["quiz_score"] = quiz_score
        passed = quiz_score >= 80
        new_history = {
            "topic": state.get("current_topic"),
            "score": quiz_score,
            "feedback": feedback,
            "passed": passed
        }
        state_updates["assessment_history"] = [new_history]
        if not passed:
            state_updates["failed_attempts"] = state.get("failed_attempts", 0) + 1
        else:
            state_updates["failed_attempts"] = 0
            # BUG-6 FIX: Guard against duplicate completed_topics entries
            current_topic = state.get("current_topic")
            if current_topic not in state.get("completed_topics", []):
                state_updates["completed_topics"] = [current_topic]
            else:
                logger.info("Topic '%s' already in completed_topics, skipping duplicate.", current_topic)

    return state_updates
