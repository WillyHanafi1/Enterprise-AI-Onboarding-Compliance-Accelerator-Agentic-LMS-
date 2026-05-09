"""
Database & Vector Store Initialization.

This module provides factory functions for:
- LangGraph Checkpointer (SQLite for dev, PostgreSQL for prod)
- ChromaDB vector store client

These are initialized lazily and injected via FastAPI dependencies.
"""

import logging
import sqlite3
import sys
import asyncio
from pathlib import Path

# Fix for Psycopg + Windows asyncio (ProactorEventLoop not supported by Psycopg)
if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

import chromadb

from src.core.config import get_settings

logger = logging.getLogger(__name__)

# Default paths
CHROMA_PERSIST_DIR = Path("chroma_db")
CHECKPOINTER_DB_PATH = Path("checkpointer.db")


def get_chroma_client() -> chromadb.ClientAPI:
    """
    Returns a persistent ChromaDB client for vector storage.

    The data is persisted to `./chroma_db/` directory.

    Returns:
        A configured ChromaDB persistent client.
    """
    CHROMA_PERSIST_DIR.mkdir(exist_ok=True)
    client = chromadb.PersistentClient(path=str(CHROMA_PERSIST_DIR))
    logger.info("ChromaDB initialized at %s", CHROMA_PERSIST_DIR)
    return client


def get_checkpointer():
    """
    Returns a LangGraph checkpointer for state persistence.

    - Development: Uses SqliteSaver (zero-config, file-based)
    - Production: Uses AsyncPostgresSaver (requires DATABASE_URL)

    The SqliteSaver requires an explicit sqlite3 connection object.
    The caller is responsible for managing the connection lifecycle,
    typically via a context manager or application lifespan.

    Returns:
        A LangGraph-compatible checkpointer instance.
    """
    settings = get_settings()

    if settings.ENVIRONMENT == "production":
        from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
        from psycopg_pool import AsyncConnectionPool

        # Create a connection pool for the checkpointer
        pool = AsyncConnectionPool(conninfo=settings.DATABASE_URL, min_size=0, max_size=20, open=False)
        return AsyncPostgresSaver(pool)

    # Development: SQLite-based checkpointer
    from langgraph.checkpoint.sqlite import SqliteSaver

    conn = sqlite3.connect(str(CHECKPOINTER_DB_PATH), check_same_thread=False)
    logger.info("Using SQLite checkpointer at %s", CHECKPOINTER_DB_PATH)
    return SqliteSaver(conn)
