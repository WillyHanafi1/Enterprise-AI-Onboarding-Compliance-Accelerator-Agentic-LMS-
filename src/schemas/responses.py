"""
API Response Models.

Defines Pydantic models for structuring API responses.
Ensures consistent, typed JSON output across all endpoints.
"""

from pydantic import BaseModel, Field


class IngestionResponse(BaseModel):
    """Response after successfully ingesting a document."""

    filename: str = Field(..., description="Name of the ingested file")
    pages_loaded: int = Field(..., description="Number of raw pages extracted")
    chunks_created: int = Field(
        ..., description="Number of chunks after splitting"
    )
    chunks_stored: int = Field(
        ..., description="Number of chunks stored in vector DB"
    )


class ErrorResponse(BaseModel):
    """Standard error response."""

    detail: str = Field(..., description="Human-readable error message")


class SessionCreateResponse(BaseModel):
    """Response after creating a new onboarding session."""

    session_id: str = Field(..., description="Unique session/thread identifier")
    welcome_message: str = Field(
        ..., description="Planner's welcome message with syllabus"
    )
    syllabus: list[str] = Field(
        default_factory=list, description="Generated learning plan"
    )


class SessionStatusResponse(BaseModel):
    """Response for session status queries."""

    session_id: str
    employee_name: str
    employee_role: str
    current_topic: str | None = None
    completed_topics: list[str] = Field(default_factory=list)
    syllabus: list[str] = Field(default_factory=list)
    quiz_score: int | None = None
    is_certified: bool = False
    requires_human_review: bool = False
    current_agent: str | None = None


class ChatResponse(BaseModel):
    """Response for non-streaming chat calls (fallback)."""

    session_id: str
    agent: str | None = None
    message: str
    requires_approval: bool = False


class SupervisorActionResponse(BaseModel):
    """Response after supervisor approve/reject action."""

    session_id: str
    action: str = Field(..., description="'approved' or 'rejected'")
    message: str = Field(..., description="Result description")
    is_certified: bool = False
