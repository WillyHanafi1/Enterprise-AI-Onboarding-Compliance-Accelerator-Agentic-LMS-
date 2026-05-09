"""
FastAPI Dependency Injection.

Provides shared resources to route handlers via FastAPI's Depends() mechanism.
This keeps route handlers clean and resources easily mockable in tests.

Dependencies:
- Settings: Application configuration
- Graph: Compiled LangGraph instance (singleton)
- Checkpointer: State persistence backend
"""

import asyncio
import logging
import sys

# Fix for Psycopg + Windows asyncio — MUST be set before any psycopg import
if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

from src.core.config import Settings, get_settings

logger = logging.getLogger(__name__)

# Module-level singleton for the compiled graph.
# Initialized during app lifespan startup via `init_graph()`.
_graph_instance = None
_checkpointer_instance = None


async def init_graph():
    """
    Initialize the graph singleton and checkpointer.

    Called once during FastAPI lifespan startup. The graph is compiled
    with the checkpointer and stored as a module-level singleton.

    Must be called before any endpoint that depends on `get_graph_instance()`.
    """
    global _graph_instance, _checkpointer_instance

    from src.core.database import get_checkpointer
    from src.graph.workflow import build_graph

    _checkpointer_instance = get_checkpointer()

    # Initialize Postgres tables and pool if needed
    if hasattr(_checkpointer_instance, "setup"):
        import psycopg
        from src.core.config import get_settings
        settings = get_settings()

        # Open the pool first
        if hasattr(_checkpointer_instance, "conn") and hasattr(_checkpointer_instance.conn, "open"):
            try:
                await _checkpointer_instance.conn.open()
                logger.info("Postgres connection pool opened.")
            except Exception as e:
                logger.error("Failed to open Postgres connection pool: %s", e)
                raise

        # setup() needs to run outside a transaction for CREATE INDEX CONCURRENTLY.
        # We create a temporary saver with a direct autocommit connection for setup.
        from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
        async with await psycopg.AsyncConnection.connect(settings.DATABASE_URL, autocommit=True) as conn:
            temp_saver = AsyncPostgresSaver(conn)
            await temp_saver.setup()
        logger.info("Postgres checkpointer setup complete via temporary autocommit connection.")

    _graph_instance = build_graph(checkpointer=_checkpointer_instance)
    logger.info("Graph singleton initialized with checkpointer.")


async def shutdown_graph():
    """
    Clean up graph resources on application shutdown.

    BUG-5 FIX: Rewrote the close logic to check type BEFORE calling,
    preventing the walrus-operator bug that eagerly called .close()
    before determining if it returns a coroutine.
    """
    global _graph_instance, _checkpointer_instance

    if _checkpointer_instance is not None:
        try:
            if hasattr(_checkpointer_instance, "conn"):
                conn = _checkpointer_instance.conn
                if hasattr(conn, "close"):
                    close_fn = conn.close
                    if asyncio.iscoroutinefunction(close_fn):
                        await close_fn()
                    else:
                        close_fn()
                    logger.info("Checkpointer connection closed.")
        except Exception as e:
            logger.warning("Error closing checkpointer connection: %s", e)

    _graph_instance = None
    _checkpointer_instance = None


def get_graph_instance():
    """
    Dependency that provides the compiled graph instance.

    Raises RuntimeError if the graph has not been initialized yet.

    Usage in routes:
        @router.post("/example")
        async def example(graph = Depends(get_graph_instance)):
            ...
    """
    if _graph_instance is None:
        raise RuntimeError(
            "Graph not initialized. Ensure init_graph() was called during startup."
        )
    return _graph_instance


def get_current_settings() -> Settings:
    """
    Dependency that provides the application settings.

    Usage in routes:
        @router.get("/example")
        async def example(settings: Settings = Depends(get_current_settings)):
            ...
    """
    return get_settings()
