"""
Session Management Endpoints.

Handles onboarding session lifecycle:
    - POST /sessions         → Create a new onboarding session
    - GET  /sessions/{id}/status → Get session progress and state
"""

import logging
import uuid

from fastapi import APIRouter, Depends, HTTPException
from langchain_core.messages import HumanMessage

from src.api.dependencies import get_graph_instance
from src.core.config import get_settings
from src.core.observability import get_langfuse_callback
from src.schemas.requests import SessionCreateRequest
from src.schemas.responses import SessionCreateResponse, SessionStatusResponse

logger = logging.getLogger(__name__)
settings = get_settings()

router = APIRouter(prefix=settings.API_PREFIX, tags=["Sessions"])


@router.post(
    "/sessions",
    response_model=SessionCreateResponse,
    summary="Create a new onboarding session",
    description=(
        "Creates a new onboarding session for an employee. "
        "The Curriculum Planner agent generates a personalized syllabus "
        "and returns a welcome message with the learning plan."
    ),
)
async def create_session(
    request: SessionCreateRequest,
    graph=Depends(get_graph_instance),  # noqa: B008
) -> SessionCreateResponse:
    """
    Creates a new onboarding session.

    Flow:
        1. Generate a unique session_id (UUID)
        2. Invoke the graph with initial state → Planner runs
        3. Return session_id + welcome message + syllabus
    """
    session_id = str(uuid.uuid4())

    logger.info(
        "Creating session '%s' for %s (%s)",
        session_id,
        request.employee_name,
        request.employee_role,
    )

    config = {"configurable": {"thread_id": session_id}}

    initial_state = {
        "messages": [],
        "employee_role": request.employee_role,
        "employee_name": request.employee_name,
        "syllabus": [],
        "current_topic": "",
        "completed_topics": [],
        "quiz_score": 0,
        "failed_attempts": 0,
        "assessment_history": [],
        "is_certified": False,
        "requires_human_review": False,
        "current_agent": None,
    }

    try:
        # Initialize Langfuse Callback
        langfuse_handler = get_langfuse_callback()
        callbacks = [langfuse_handler] if langfuse_handler else []

        # Add tracing metadata to config for Langfuse (standard LangChain metadata keys)
        config["metadata"] = {
            "langfuse_trace_name": "session-creation",
            "langfuse_session_id": session_id,
            "langfuse_user_id": request.user_id,
            "langfuse_tags": [settings.ENVIRONMENT],
            "version": settings.VERSION
        }

        # BUG-2 FIX: Use ainvoke for async checkpointer compatibility
        result = await graph.ainvoke(
            initial_state, 
            {**config, "callbacks": callbacks}
        )
    except Exception as e:
        logger.exception("Failed to create session '%s'", session_id)
        raise HTTPException(
            status_code=500,
            detail=f"Session creation failed: {e!s}",
        ) from e

    # Extract welcome message from the last AI message
    welcome_message = ""
    for msg in reversed(result.get("messages", [])):
        if hasattr(msg, "content") and not isinstance(msg, HumanMessage):
            # Handle both string and list content (Gemini multi-modal blocks)
            if isinstance(msg.content, list):
                welcome_message = "".join([
                    block.get("text", "")
                    for block in msg.content
                    if isinstance(block, dict) and block.get("type") == "text"
                ])
            else:
                welcome_message = msg.content
            break

    return SessionCreateResponse(
        session_id=session_id,
        welcome_message=welcome_message,
        syllabus=result.get("syllabus", []),
    )


@router.get(
    "/sessions/{session_id}/status",
    response_model=SessionStatusResponse,
    summary="Get session progress",
    description=(
        "Returns the current state of an onboarding session, including "
        "completed topics, current topic, assessment scores, and certification status."
    ),
)
async def get_session_status(
    session_id: str,
    graph=Depends(get_graph_instance),  # noqa: B008
) -> SessionStatusResponse:
    """
    Retrieves the current state of a session from the checkpointer.
    """
    config = {"configurable": {"thread_id": session_id}}

    try:
        # BUG-2 FIX: Use aget_state for async checkpointer compatibility
        snapshot = await graph.aget_state(config)
    except Exception as e:
        logger.exception("Failed to get state for session '%s'", session_id)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve session state: {e!s}",
        ) from e

    if not snapshot or not snapshot.values:
        raise HTTPException(
            status_code=404,
            detail=f"Session '{session_id}' not found.",
        )

    state = snapshot.values

    return SessionStatusResponse(
        session_id=session_id,
        employee_name=state.get("employee_name", ""),
        employee_role=state.get("employee_role", ""),
        current_topic=state.get("current_topic"),
        completed_topics=state.get("completed_topics", []),
        syllabus=state.get("syllabus", []),
        quiz_score=state.get("quiz_score"),
        is_certified=state.get("is_certified", False),
        requires_human_review=state.get("requires_human_review", False),
        current_agent=state.get("current_agent"),
    )
