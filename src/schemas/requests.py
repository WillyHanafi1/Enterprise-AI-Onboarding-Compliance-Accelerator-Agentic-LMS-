"""
API Request Models.

Defines Pydantic models for validating incoming API requests.
"""

from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    """Request body for the chat endpoint."""

    message: str = Field(
        ..., min_length=1, max_length=5000, description="User message text"
    )
    user_id: str | None = Field(None, description="Optional user ID for tracking")


class SessionCreateRequest(BaseModel):
    """Request body for creating a new onboarding session."""

    employee_name: str = Field(..., min_length=1, max_length=100)
    employee_role: str = Field(..., min_length=1, max_length=100)
    user_id: str | None = Field(None, description="Optional user ID for tracking")


class SupervisorActionRequest(BaseModel):
    """Request body for supervisor approve/reject actions."""

    feedback: str | None = Field(
        None,
        max_length=2000,
        description="Optional supervisor feedback or reason for rejection.",
    )


class FeedbackRequest(BaseModel):
    """Request body for sending user feedback to Langfuse."""

    trace_id: str | None = Field(None, description="The trace ID from Langfuse")
    score: float = Field(..., ge=-1.0, le=1.0, description="Feedback score (e.g., 1 for up, -1 for down)")
    comment: str | None = Field(None, description="Optional text feedback")
    name: str = Field("user-feedback", description="Name of the feedback metric")
