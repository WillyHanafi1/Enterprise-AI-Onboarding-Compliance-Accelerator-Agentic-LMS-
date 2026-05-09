"""
LangGraph Workflow Assembly.

This is the core orchestration module that wires all agents into
a complete LangGraph state machine. It implements the graph design
from ARCHITECTURE.md §4:

    __start__ → planner_node → END (await user)
                                 ↓ (user sends message)
                            route_intent (conditional)
                           /        |          \\
                     explainer   assessor    status
                        ↓           ↓           ↓
                       END      grade_check    END
                               /          \\
                         fail→explainer    pass→advance_topic
                                                  ↓
                                            topic_check
                                           /          \\
                                    more→END    all_done→certifier→END

Key Design Decisions:
    1. Multi-turn conversation: Each node returns to END, waiting for
       the next user message. The graph is re-invoked with the same
       thread_id, resuming from the persisted checkpoint.
    2. Conditional edges: grade_check and topic_check are pure functions
       that inspect state — no LLM calls, zero latency.
    3. Checkpointer: SQLite for dev, PostgreSQL for prod. Enables
       session persistence across server restarts.
"""

import logging
from typing import Literal

from langgraph.graph import END, StateGraph

from src.agents.assessor import assessor_node
from src.agents.certifier import certifier_node
from src.agents.explainer import get_explainer_agent
from src.agents.planner import planner_node
from src.agents.router import route_intent
from src.agents.status import status_node
from src.core.database import get_checkpointer
from src.schemas.state import OnboardingState

logger = logging.getLogger(__name__)


# ============================================================
# Conditional Edge Functions
# ============================================================


def grade_check(state: OnboardingState) -> Literal["pass", "fail"]:
    """
    Conditional edge after Assessor.

    Routes based on the latest quiz score:
        - score >= 80 → "pass" (advance to next topic)
        - score < 80  → "fail" (remediation via Explainer)

    If no score was recorded (e.g., Assessor only asked a question),
    routes to END to await the user's answer.

    Args:
        state: The current onboarding state.

    Returns:
        "pass" or "fail" routing key.
    """
    score = state.get("quiz_score", 0)
    topic = state.get("current_topic", "unknown")

    # Check if the assessor actually graded something.
    # If quiz_score is still 0 and no assessment_history for current topic,
    # it means the assessor only asked a question — route to END.
    assessment_history = state.get("assessment_history", [])
    current_topic_graded = any(
        record.get("topic") == topic for record in assessment_history
    )

    if not current_topic_graded:
        # Assessor asked a question but hasn't graded yet (user hasn't answered).
        # Returning "fail" here routes to END, which is correct: the conversation
        # pauses and waits for the user's next message. On the next turn, the
        # router will send the user's answer back to the assessor for grading.
        logger.info("No grade recorded yet for topic '%s'. Awaiting user answer.", topic)
        return "fail"

    if score >= 80:
        logger.info("Grade check PASS: score=%d for topic '%s'", score, topic)
        return "pass"
    else:
        logger.info("Grade check FAIL: score=%d for topic '%s'. Routing to remediation.", score, topic)
        return "fail"


def topic_check(state: OnboardingState) -> Literal["continue", "certify"]:
    """
    Conditional edge after advancing to the next topic.

    Checks if all syllabus topics have been completed:
        - All done   → "certify" (proceed to Certifier)
        - More left  → "continue" (return to END, await user)

    Args:
        state: The current onboarding state.

    Returns:
        "certify" or "continue" routing key.
    """
    syllabus = state.get("syllabus", [])
    completed = state.get("completed_topics", [])

    remaining = [t for t in syllabus if t not in completed]

    if not remaining:
        logger.info("All %d topics completed. Routing to Certifier.", len(syllabus))
        return "certify"
    else:
        logger.info(
            "Topic check: %d/%d completed. %d remaining.",
            len(completed),
            len(syllabus),
            len(remaining),
        )
        return "continue"


# ============================================================
# Advance Topic Node
# ============================================================


def advance_topic(state: OnboardingState) -> dict:
    """
    Advances to the next uncompleted topic in the syllabus.

    Called after a successful assessment (score >= 80).
    Finds the next topic that hasn't been completed yet and
    updates current_topic in the state.

    Args:
        state: The current onboarding state.

    Returns:
        dict: State updates with the new current_topic.
    """
    syllabus = state.get("syllabus", [])
    completed = state.get("completed_topics", [])

    # Find the next uncompleted topic
    next_topic = None
    for topic in syllabus:
        if topic not in completed:
            next_topic = topic
            break

    if next_topic:
        logger.info("Advancing to next topic: '%s'", next_topic)
    else:
        logger.info("All topics completed — no more topics to advance to.")

    return {
        "current_topic": next_topic or state.get("current_topic", ""),
        "current_agent": "advance_topic",
    }


# ============================================================
# Graph Builder
# ============================================================


def build_graph(checkpointer=None):
    """
    Builds and compiles the full LangGraph onboarding workflow.

    The graph implements a multi-turn conversational flow where
    each node processes a step and returns to END, waiting for
    the next user message via a new invoke() call with the same
    thread_id.

    Node Inventory:
        - planner_node:   Generates syllabus (runs once at session start)
        - explainer_node: RAG-based tutoring
        - assessor_node:  Quiz generation + LLM-as-a-judge grading
        - status_node:    Progress summary
        - advance_topic:  Moves to next syllabus topic
        - certifier_node: Issues final certificate

    Conditional Edges:
        - route_intent:  Classifies user intent (learn/quiz/status)
        - grade_check:   Routes based on assessment score
        - topic_check:   Checks if all topics are complete

    Args:
        checkpointer: Optional LangGraph checkpointer for state
                      persistence. If None, state is ephemeral.

    Returns:
        A compiled LangGraph CompiledStateGraph ready for invoke().
    """
    builder = StateGraph(OnboardingState)

    # === Add Nodes ===
    builder.add_node("planner_node", planner_node)
    builder.add_node("explainer_node", get_explainer_agent())
    builder.add_node("assessor_node", assessor_node)
    builder.add_node("status_node", status_node)
    builder.add_node("advance_topic", advance_topic)
    builder.add_node("certifier_node", certifier_node)

    # === Entry Point ===
    # Use a conditional entry point. If no syllabus exists, go to planner.
    # Otherwise, use the router to classify the new user message.
    def route_start(state: OnboardingState) -> str:
        if not state.get("syllabus"):
            return "planner_node"
        
        from src.agents.router import route_intent
        intent = route_intent(state)
        node_map = {
            "learn": "explainer_node",
            "quiz": "assessor_node",
            "status": "status_node",
        }
        return node_map.get(intent, "explainer_node")

    builder.set_conditional_entry_point(
        route_start,
        {
            "planner_node": "planner_node",
            "explainer_node": "explainer_node",
            "assessor_node": "assessor_node",
            "status_node": "status_node",
        }
    )

    # === Edges: Planner → END ===
    # After planning, wait for user's first message
    builder.add_edge("planner_node", END)

    # === Edges: Explainer → END ===
    # After explaining, wait for next user message
    builder.add_edge("explainer_node", END)

    # === Edges: Status → END ===
    # After showing status, wait for next user message
    builder.add_edge("status_node", END)

    # === Edges: Certifier → END ===
    # Terminal — session is complete
    builder.add_edge("certifier_node", END)

    # === Conditional Edge: Assessor → grade_check ===
    builder.add_conditional_edges(
        "assessor_node",
        grade_check,
        {
            "pass": "advance_topic",
            "fail": END,  # fail → END: either needs remediation or awaiting user answer
        },
    )

    # === Conditional Edge: advance_topic → topic_check ===
    builder.add_conditional_edges(
        "advance_topic",
        topic_check,
        {
            "continue": END,     # More topics → wait for user
            "certify": "certifier_node",  # All done → issue certificate
        },
    )

    # === Compile ===
    # interrupt_before: HITL gate — graph pauses before certifier_node.
    # Supervisor must approve before certification is issued.
    # The checkpointer persists the interrupted state, allowing
    # the supervisor to review and resume days later.
    graph = builder.compile(
        checkpointer=checkpointer,
        interrupt_before=["certifier_node"],
    )

    logger.info("Graph compiled successfully with %d nodes.", len(builder.nodes))
    return graph


def get_graph():
    """
    Returns a compiled graph with the default checkpointer.

    This is the primary entry point for creating a production-ready
    graph instance with state persistence.

    Returns:
        A compiled LangGraph CompiledStateGraph with SQLite checkpointer.
    """
    checkpointer = get_checkpointer()
    return build_graph(checkpointer=checkpointer)


def get_graph_with_router():
    """
    Returns the compiled graph AND the route_intent function.

    This is used by the API layer which needs both:
    1. The graph for invoke() calls
    2. The router for determining which node to start from
       on subsequent user messages (after planner has run)

    The router is not embedded as a node because LangGraph's
    multi-turn pattern requires the graph to END between turns.
    The API layer calls route_intent() to decide which node
    to invoke next.

    Returns:
        tuple: (compiled_graph, route_intent_function)
    """
    graph = get_graph()
    return graph, route_intent
