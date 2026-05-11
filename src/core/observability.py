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

def get_langfuse_callback(trace_name: str = "onboarding-chat", session_id: str = None, user_id: str = None) -> CallbackHandler:
    """
    Initializes and returns a Langfuse CallbackHandler with professional enhancements.
    """
    settings = get_settings()
    
    if not settings.LANGFUSE_PUBLIC_KEY or not settings.LANGFUSE_SECRET_KEY:
        logger.warning("Langfuse API keys not found. Tracing will be disabled.")
        return None

    handler = CallbackHandler(
        public_key=settings.LANGFUSE_PUBLIC_KEY,
        secret_key=settings.LANGFUSE_SECRET_KEY,
        host=settings.LANGFUSE_HOST,
        trace_name=trace_name,
        session_id=session_id,
        user_id=user_id,
        version=settings.VERSION,
        tags=[settings.ENVIRONMENT],
        masking=mask_pii  # Professional best practice: PII Masking
    )
    
    return handler
