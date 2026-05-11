"""
Supervisor Endpoints — HITL Approve/Reject.

Handles supervisor actions on paused sessions:
    - POST /sessions/{id}/approve → Resume graph → Certifier issues certificate
    - POST /sessions/{id}/reject  → Route trainee back for remediation

When all assessments pass, the graph pauses before certifier_node
(via interrupt_before). These endpoints allow a supervisor to
review the trainee's results and make a final decision.
"""

import logging

from fastapi import APIRouter, Depends, HTTPException
from langchain_core.messages import AIMessage

from src.api.dependencies import get_graph_instance
from src.core.config import get_settings
from src.core.observability import get_langfuse_callback
from src.schemas.requests import SupervisorActionRequest
from src.schemas.responses import SupervisorActionResponse

logger = logging.getLogger(__name__)
settings = get_settings()

router = APIRouter(prefix=settings.API_PREFIX, tags=["Supervisor"])


@router.post(
    "/sessions/{session_id}/approve",
    response_model=SupervisorActionResponse,
    summary="Approve certification",
    description=(
        "Supervisor approves the trainee's certification. "
        "This resumes the paused graph, allowing the Certifier "
        "node to issue the final compliance certificate."
    ),
)
async def approve_session(
    session_id: str,
    request: SupervisorActionRequest | None = None,
    graph=Depends(get_graph_instance),  # noqa: B008
) -> SupervisorActionResponse:
    """
    Resumes the graph after HITL interrupt → Certifier issues certificate.

    Flow:
        1. Verify session is in interrupted state (waiting at certifier)
        2. Optionally add supervisor feedback to messages
        3. Invoke graph with None → certifier_node runs
        4. Return certification result

    BUG-2 FIX: All graph calls are now async (aget_state, aupdate_state, ainvoke).
    """
    config = {"configurable": {"thread_id": session_id}}

    # Get current state
    try:
        snapshot = await graph.aget_state(config)
    except Exception as e:
        logger.exception("Failed to get state for session '%s'", session_id)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve session: {e!s}",
        ) from e

    if not snapshot or not snapshot.values:
        raise HTTPException(
            status_code=404,
            detail=f"Session '{session_id}' not found.",
        )

    # Verify the graph is actually paused (HITL interrupt)
    if not snapshot.next:
        state = snapshot.values
        if state.get("is_certified", False):
            return SupervisorActionResponse(
                session_id=session_id,
                action="approved",
                message="Session is already certified.",
                is_certified=True,
            )
        raise HTTPException(
            status_code=400,
            detail="Session is not waiting for approval. The trainee may not have passed all assessments yet.",
        )

    logger.info(
        "Supervisor approving session '%s'. Pending nodes: %s",
        session_id,
        list(snapshot.next),
    )

    # Add supervisor feedback if provided
    if request and request.feedback:
        await graph.aupdate_state(
            config,
            {
                "messages": [
                    AIMessage(
                        content=f"[Supervisor Feedback] {request.feedback}"
                    )
                ],
            },
        )

    # Resume the graph → certifier_node runs
    try:
        # Initialize Langfuse Callback
        langfuse_handler = get_langfuse_callback()
        callbacks = [langfuse_handler] if langfuse_handler else []

        # Add tracing metadata to config for Langfuse
        config["metadata"] = {
            "langfuse_trace_name": "supervisor-approval",
            "langfuse_session_id": session_id,
            "langfuse_tags": [settings.ENVIRONMENT],
            "version": settings.VERSION
        }

        result = await graph.ainvoke(None, {**config, "callbacks": callbacks})
    except Exception as e:
        logger.exception("Failed to resume graph for session '%s'", session_id)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to process approval: {e!s}",
        ) from e

    # Extract certification message
    cert_message = ""
    for msg in reversed(result.get("messages", [])):
        if isinstance(msg, AIMessage) and msg.content:
            cert_message = msg.content
            break

    return SupervisorActionResponse(
        session_id=session_id,
        action="approved",
        message=cert_message or "Certification approved.",
        is_certified=result.get("is_certified", False),
    )


@router.post(
    "/sessions/{session_id}/reject",
    response_model=SupervisorActionResponse,
    summary="Reject certification",
    description=(
        "Supervisor rejects the trainee's certification. "
        "The trainee is routed back for additional learning. "
        "The rejection reason is added to the conversation."
    ),
)
async def reject_session(
    session_id: str,
    request: SupervisorActionRequest | None = None,
    graph=Depends(get_graph_instance),  # noqa: B008
) -> SupervisorActionResponse:
    """
    Rejects certification and routes trainee back for remediation.

    Flow:
        1. Verify session is in interrupted state
        2. Add rejection feedback to messages
        3. Reset quiz_score and failed_attempts for current topic
        4. Update state so next interaction routes to explainer

    BUG-2 FIX: All graph calls are now async.
    """
    config = {"configurable": {"thread_id": session_id}}

    # Get current state
    try:
        snapshot = await graph.aget_state(config)
    except Exception as e:
        logger.exception("Failed to get state for session '%s'", session_id)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve session: {e!s}",
        ) from e

    if not snapshot or not snapshot.values:
        raise HTTPException(
            status_code=404,
            detail=f"Session '{session_id}' not found.",
        )

    if not snapshot.next:
        raise HTTPException(
            status_code=400,
            detail="Session is not waiting for approval.",
        )

    state = snapshot.values
    feedback_text = (request.feedback if request and request.feedback
                     else "Supervisor has requested additional review.")

    logger.info(
        "Supervisor rejecting session '%s'. Reason: %s",
        session_id,
        feedback_text[:100],
    )

    # Update state: add rejection message, reset for remediation
    # Route back to explainer by setting state as if we're at __start__
    rejection_msg = AIMessage(
        content=(
            f"⚠️ **Supervisor Feedback**: {feedback_text}\n\n"
            f"Your certification has been deferred. "
            f"Please review the material for **{state.get('current_topic', 'the current topic')}** "
            f"and try again."
        )
    )

    await graph.aupdate_state(
        config,
        {
            "messages": [rejection_msg],
            "requires_human_review": False,
            "quiz_score": 0,
            "failed_attempts": 0,
        },
        as_node="explainer_node",
    )

    return SupervisorActionResponse(
        session_id=session_id,
        action="rejected",
        message=f"Certification rejected. Trainee will receive additional tutoring. Reason: {feedback_text}",
        is_certified=False,
    )
