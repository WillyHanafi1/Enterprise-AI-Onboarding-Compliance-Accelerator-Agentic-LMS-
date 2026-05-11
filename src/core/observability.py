import logging
from functools import lru_cache
from langfuse.langchain import CallbackHandler
from src.core.config import get_settings

logger = logging.getLogger(__name__)

import re

def mask_pii(text: str) -> str:
    """Simple regex-based PII masking for emails."""
    if not isinstance(text, str):
        return text
    # Mask emails
    return re.sub(r'[\w\.-]+@[\w\.-]+\.\w+', '[EMAIL_REDACTED]', text)

def get_langfuse_callback() -> CallbackHandler:
    """
    Initializes and returns a Langfuse CallbackHandler.
    Configuration (host, keys) is automatically loaded from environment variables.
    Tracing metadata (session_id, etc.) should be passed via LangChain config['metadata'].
    """
    settings = get_settings()
    
    if not settings.LANGFUSE_PUBLIC_KEY or not settings.LANGFUSE_SECRET_KEY:
        logger.warning("Langfuse API keys not found. Tracing will be disabled.")
        return None

    handler = CallbackHandler(
        public_key=settings.LANGFUSE_PUBLIC_KEY,
    )
    
    return handler
