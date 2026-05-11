"""
Chat Endpoint with SSE Streaming.

Handles the main conversational interaction:
    - POST /sessions/{id}/chat → Send message, receive SSE-streamed response

Uses Server-Sent Events (SSE) for real-time token streaming.
The response includes agent status events, streamed tokens,
state updates, and HITL interrupt notifications.

SSE Event Types:
    - agent_start:       Agent node begins execution
    - token:             Streamed content token
    - state_update:      State changes after node execution
    - requires_approval: HITL interrupt — supervisor action needed
    - error:             Error during processing
    - done:              Stream complete
"""

import json
import logging
from collections.abc import AsyncIterator

from fastapi import APIRouter, Depends, HTTPException
from langchain_core.messages import AIMessage, AIMessageChunk, HumanMessage
from sse_starlette.sse import EventSourceResponse

from src.api.dependencies import get_graph_instance
from src.core.config import get_settings
from src.core.observability import get_langfuse_callback
from src.schemas.requests import ChatRequest, FeedbackRequest
from src.schemas.responses import ChatResponse

logger = logging.getLogger(__name__)
settings = get_settings()

router = APIRouter(prefix=settings.API_PREFIX, tags=["Chat"])


async def _get_session_state(graph, session_id: str) -> dict:
    """
    Retrieve the current session state from checkpointer.

    Raises HTTPException 404 if session doesn't exist.

    BUG-2+4 FIX: Made async, uses aget_state for AsyncPostgresSaver compatibility.
    """
    config = {"configurable": {"thread_id": session_id}}
    snapshot = await graph.aget_state(config)

    if not snapshot or not snapshot.values:
        raise HTTPException(
            status_code=404,
            detail=f"Session '{session_id}' not found. Create one first via POST /sessions.",
        )

    return snapshot.values


async def _stream_graph_response(
    graph, session_id: str, input_dict: dict = None, user_id: str = None
) -> AsyncIterator[dict]:
    """
    Async generator that streams graph execution events as SSE data.

    This handles the multi-turn pattern:
    1. Yield agent_start (determined by graph routing, not pre-computed)
    2. Invoke the graph with input_dict and collect the response
    3. Yield SSE events: tokens → state_update → done/requires_approval

    BUG-3 FIX: Removed target_node param. The graph's own conditional entry
    point handles routing — we no longer pre-compute intent externally.
    The agent_start event now reports the actual node from the stream metadata.

    Args:
        graph: Compiled LangGraph instance.
        session_id: The thread_id for state persistence.
        input_dict: The input to pass to graph.stream()

    Yields:
        dict: SSE event objects with 'event' and 'data' keys.
    """
    config = {"configurable": {"thread_id": session_id}}

    # Track which agent actually runs (determined by graph routing)
    detected_agent = None

    try:
        final_state = None
        # Initialize Langfuse Callback
        langfuse_handler = get_langfuse_callback(
            trace_name="chat-stream",
            session_id=session_id,
            user_id=user_id
        )
        callbacks = [langfuse_handler] if langfuse_handler else []

        # Using stream_mode=["messages", "values"] allows us to see internal messages from sub-agents
        async for event_type, event_data in graph.astream(
            input_dict, 
            config, 
            stream_mode=["messages", "values"],
            config={"callbacks": callbacks}
        ):
            if event_type == "messages":
                chunk, metadata = event_data

                # Detect the actual agent node from stream metadata
                node_name = metadata.get("langgraph_node", "unknown")

                # Skip chunks from the router or internal nodes that shouldn't stream
                if node_name in ["__start__", "route_start"]:
                    continue

                # Emit agent_start on first real node detection
                if detected_agent is None and node_name != "unknown":
                    detected_agent = node_name
                    # Get trace_id from langfuse_handler if available
                    trace_id = getattr(langfuse_handler, "trace_id", None)
                    yield {
                        "event": "agent_start",
                        "data": json.dumps({
                            "agent": detected_agent,
                            "trace_id": trace_id
                        }),
                    }

                # Only stream AIMessageChunk (streaming) or AIMessage (full response from a node)
                if not isinstance(chunk, (AIMessageChunk, AIMessage)):
                    continue

                # Skip chunks that are tool calls (we don't want to show JSON/tool names to user)
                if getattr(chunk, "tool_calls", None) or getattr(chunk, "tool_call_chunks", None):
                    continue

                if hasattr(chunk, "content") and chunk.content:
                    content = ""
                    # Gemini content blocks
                    if isinstance(chunk.content, list):
                        content = "".join([
                            block.get("text", "")
                            for block in chunk.content
                            if isinstance(block, dict) and block.get("type") == "text"
                        ])
                    elif isinstance(chunk.content, str):
                        content = chunk.content

                    if content:
                        yield {
                            "event": "token",
                            "data": json.dumps({"content": content}),
                        }

            elif event_type == "values":
                final_state = event_data

        # Emit agent end event
        yield {
            "event": "agent_end",
            "data": json.dumps({"agent": detected_agent or "unknown"}),
        }

        # Check for state updates
        if final_state:
            state_update = {
                "current_topic": final_state.get("current_topic", ""),
                "quiz_score": final_state.get("quiz_score", 0),
                "completed_topics": final_state.get("completed_topics", []),
                "is_certified": final_state.get("is_certified", False),
            }
            yield {
                "event": "state_update",
                "data": json.dumps(state_update),
            }

        # Check for HITL interrupt
        # BUG-2 FIX: Use aget_state for async checkpointer
        snapshot = await graph.aget_state(config)
        if snapshot.next:
            # Graph is paused — likely at certifier_node (HITL)
            yield {
                "event": "requires_approval",
                "data": json.dumps({
                    "message": "All assessments passed! Awaiting supervisor approval for certification.",
                    "pending_node": list(snapshot.next),
                }),
            }

    except Exception as e:
        logger.exception("Error streaming response for session '%s'", session_id)
        yield {
            "event": "error",
            "data": json.dumps({"detail": str(e)}),
        }

    # Always emit done
    yield {
        "event": "done",
        "data": json.dumps({}),
    }


@router.post(
    "/sessions/{session_id}/chat",
    summary="Send a chat message (SSE streaming)",
    description=(
        "Send a user message in an onboarding session. "
        "The response is streamed via Server-Sent Events (SSE) with "
        "real-time tokens and agent status updates."
    ),
    responses={
        200: {
            "description": "SSE stream of chat events",
            "content": {"text/event-stream": {}},
        },
        404: {"description": "Session not found"},
    },
)
async def chat(
    session_id: str,
    request: ChatRequest,
    graph=Depends(get_graph_instance),  # noqa: B008
):
    """
    Main chat endpoint with SSE streaming.

    Flow:
        1. Validate session exists
        2. Add user message to state
        3. Stream graph execution via SSE (graph handles routing internally)

    BUG-3 FIX: Removed the redundant manual route_intent() call.
    The graph's conditional entry point (route_start) handles routing.
    """
    config = {"configurable": {"thread_id": session_id}}

    # Validate session exists (BUG-2 FIX: now async)
    state = await _get_session_state(graph, session_id)

    # Check if session is already certified
    if state.get("is_certified", False):
        return ChatResponse(
            session_id=session_id,
            agent="system",
            message="This session is already certified. No further interactions needed.",
            requires_approval=False,
        )

    # Check if waiting for supervisor approval (HITL interrupt)
    # BUG-2 FIX: Use aget_state
    snapshot = await graph.aget_state(config)
    if snapshot.next:
        return ChatResponse(
            session_id=session_id,
            agent="system",
            message=(
                "This session is awaiting supervisor approval. "
                "A supervisor must approve or reject before continuing."
            ),
            requires_approval=True,
        )

    # Add user message to state
    user_msg = HumanMessage(content=request.message)

    logger.info(
        "Session '%s': user='%s'",
        session_id,
        request.message[:50],
    )

    # Stream the response via SSE, passing the user message as input
    # BUG-3 FIX: No longer pre-computing intent or target_node
    # Pass user_id if available in request (assuming ChatRequest has it or we can derive it)
    user_id = getattr(request, "user_id", None)
    
    return EventSourceResponse(
        _stream_graph_response(graph, session_id, {"messages": [user_msg]}, user_id=user_id),
        media_type="text/event-stream",
    )


@router.post(
    "/sessions/{session_id}/chat/sync",
    response_model=ChatResponse,
    summary="Send a chat message (synchronous)",
    description=(
        "Non-streaming version of the chat endpoint. "
        "Useful for testing and simple integrations."
    ),
)
async def chat_sync(
    session_id: str,
    request: ChatRequest,
    graph=Depends(get_graph_instance),  # noqa: B008
) -> ChatResponse:
    """
    Synchronous chat endpoint (non-streaming fallback).

    Same logic as the SSE endpoint but returns a single JSON response.
    BUG-2 FIX: All graph calls are now async.
    BUG-3 FIX: Router is handled by the graph's conditional entry point.
    """
    config = {"configurable": {"thread_id": session_id}}

    # Validate session exists (BUG-2 FIX: now async)
    state = await _get_session_state(graph, session_id)

    # Check if session is already certified
    if state.get("is_certified", False):
        return ChatResponse(
            session_id=session_id,
            agent="system",
            message="This session is already certified.",
        )

    # Check for HITL interrupt (BUG-2 FIX: async)
    snapshot = await graph.aget_state(config)
    if snapshot.next:
        return ChatResponse(
            session_id=session_id,
            agent="system",
            message="Awaiting supervisor approval.",
            requires_approval=True,
        )

    # Add user message to state
    user_msg = HumanMessage(content=request.message)

    try:
        # Initialize Langfuse Callback
        user_id = getattr(request, "user_id", None)
        langfuse_handler = get_langfuse_callback(
            trace_name="chat-sync",
            session_id=session_id,
            user_id=user_id
        )
        callbacks = [langfuse_handler] if langfuse_handler else []

        # BUG-2 FIX: Use ainvoke for async checkpointer
        result = await graph.ainvoke(
            {"messages": [user_msg]}, 
            {**config, "callbacks": callbacks}
        )
    except Exception as e:
        logger.exception("Chat invoke failed for session '%s'", session_id)
        raise HTTPException(
            status_code=500,
            detail=f"Chat processing failed: {e!s}",
        ) from e

    # Extract the last AI message
    ai_message = ""
    for msg in reversed(result.get("messages", [])):
        if isinstance(msg, AIMessage) and msg.content:
            # Handle both string and list content (Gemini multi-modal blocks)
            if isinstance(msg.content, list):
                ai_message = "".join([
                    block.get("text", "")
                    for block in msg.content
                    if isinstance(block, dict) and block.get("type") == "text"
                ])
            else:
                ai_message = msg.content
            break

    # Detect which agent ran from the state
    target_node = result.get("current_agent", "explainer_node")

    # Check for HITL interrupt after processing (BUG-2 FIX: async)
    snapshot = await graph.aget_state(config)
    requires_approval = bool(snapshot.next)

    return ChatResponse(
        session_id=session_id,
        agent=target_node,
        message=ai_message,
        requires_approval=requires_approval,
    )


@router.post(
    "/sessions/{session_id}/feedback",
    summary="Submit user feedback for a trace",
    description="Submit a score and optional comment for a specific interaction.",
)
async def submit_feedback(
    session_id: str,
    request: FeedbackRequest,
):
    """
    Submits feedback to Langfuse.
    
    If trace_id is not provided, it will be hard to link, but Langfuse
    can sometimes link via session_id if configured. Best is to pass trace_id from frontend.
    """
    settings = get_settings()
    if not settings.LANGFUSE_PUBLIC_KEY or not settings.LANGFUSE_SECRET_KEY:
        return {"status": "skipped", "message": "Langfuse not configured"}

    try:
        from langfuse import Langfuse
        langfuse = Langfuse(
            public_key=settings.LANGFUSE_PUBLIC_KEY,
            secret_key=settings.LANGFUSE_SECRET_KEY,
            host=settings.LANGFUSE_HOST
        )
        
        langfuse.score(
            trace_id=request.trace_id,
            name=request.name,
            value=request.score,
            comment=request.comment
        )
        return {"status": "success"}
    except Exception as e:
        logger.error(f"Failed to submit feedback to Langfuse: {e}")
        return {"status": "error", "detail": str(e)}
