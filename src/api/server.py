"""
FastAPI Application Factory.

This module creates the FastAPI application instance with:
- CORS middleware for cross-origin requests
- Lifespan handler for startup/shutdown events
- Health check endpoint for infrastructure monitoring
- Graph initialization and cleanup via lifespan
"""

# Fix for Psycopg + Windows asyncio — MUST be set before any psycopg import
# This is the entry module loaded by uvicorn, so it's the earliest place.
import asyncio
import sys
if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

import logging
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from src.api.chat import router as chat_router
from src.api.dependencies import init_graph, shutdown_graph
from src.api.routers import router as documents_router
from src.api.sessions import router as sessions_router
from src.api.supervisor import router as supervisor_router
from src.core.config import get_settings

logger = logging.getLogger(__name__)


# === Response Models ===


class HealthResponse(BaseModel):
    """Schema for health check endpoint response."""

    status: str
    environment: str
    version: str


# === Lifespan ===


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """
    Manages application startup and shutdown events.

    Startup:
        - Validates critical configuration (API keys present)
        - Initializes graph singleton with checkpointer
        - Logs environment information
    Shutdown:
        - Closes checkpointer connections
        - Cleans up resources
    """
    settings = get_settings()
    logger.info(
        "Starting %s [env=%s, debug=%s]",
        settings.PROJECT_NAME,
        settings.ENVIRONMENT,
        settings.DEBUG,
    )

    # Validate Gemini API key is configured
    if not settings.GEMINI_API_KEY:
        logger.error("GEMINI_API_KEY is not set. LLM calls will fail.")

    # Initialize graph singleton with checkpointer
    try:
        await init_graph()
        logger.info("Graph and checkpointer initialized successfully.")
    except Exception as e:
        logger.error("Failed to initialize graph: %s", e)
        raise

    yield

    # Shutdown: clean up resources
    await shutdown_graph()
    logger.info("Shutting down %s", settings.PROJECT_NAME)


# === App Factory ===


def create_app() -> FastAPI:
    """
    Creates and configures the FastAPI application.

    Returns:
        A fully configured FastAPI instance.
    """
    settings = get_settings()

    app = FastAPI(
        title=settings.PROJECT_NAME,
        description="Enterprise AI Onboarding & Compliance Accelerator — Agentic LMS",
        version="0.1.0",
        openapi_url=f"{settings.API_PREFIX}/openapi.json",
        docs_url=f"{settings.API_PREFIX}/docs",
        redoc_url=f"{settings.API_PREFIX}/redoc",
        lifespan=lifespan,
    )

    # CORS Middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # TODO: restrict in production
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # === Routes ===

    @app.get("/health", response_model=HealthResponse, tags=["Health"])
    async def health_check() -> HealthResponse:
        """Health check endpoint to verify server status."""
        return HealthResponse(
            status="ok",
            environment=settings.ENVIRONMENT,
            version="0.1.0",
        )

    # === Register API Routers ===
    app.include_router(documents_router)
    app.include_router(sessions_router)
    app.include_router(chat_router)
    app.include_router(supervisor_router)

    return app


# Create the app instance — Uvicorn needs a module-level `app` variable
app = create_app()


if __name__ == "__main__":
    import uvicorn

    # Windows + Psycopg requires SelectorEventLoop.
    # This MUST be set before any event loop is created.
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

    settings = get_settings()

    config = uvicorn.Config(
        "src.api.server:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.DEBUG,
        log_level="info",
    )

    if settings.DEBUG and sys.platform == "win32":
        # Reload mode on Windows: uvicorn.run() manages the reloader subprocess.
        # The subprocess re-imports this module, so the top-of-file policy applies.
        uvicorn.run(
            "src.api.server:app",
            host="0.0.0.0",
            port=8000,
            reload=True,
            log_level="info",
        )
    else:
        # Production or non-reload: use asyncio.run() to respect the
        # WindowsSelectorEventLoopPolicy (uvicorn.run() ignores it).
        server = uvicorn.Server(config)
        asyncio.run(server.serve())

