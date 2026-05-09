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


class SessionCreateRequest(BaseModel):
    """Request body for creating a new onboarding session."""

    employee_name: str = Field(..., min_length=1, max_length=100)
    employee_role: str = Field(..., min_length=1, max_length=100)


class SupervisorActionRequest(BaseModel):
    """Request body for supervisor approve/reject actions."""

    feedback: str | None = Field(
        None,
        max_length=2000,
        description="Optional supervisor feedback or reason for rejection.",
    )
