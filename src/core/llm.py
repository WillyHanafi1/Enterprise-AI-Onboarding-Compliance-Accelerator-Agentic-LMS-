"""
LLM Provider Factory & Observability Integration.

This module provides factory functions for creating LLM instances
and Langfuse callback handlers. All functions are lazy-evaluated
to prevent import-time crashes when .env is missing.
"""

from langchain_google_genai import ChatGoogleGenerativeAI
from langfuse.langchain import CallbackHandler

from src.core.config import get_settings


def get_llm(
    model_name: str = "gemini-3-flash-preview",
    temperature: float = 0.0,
    streaming: bool = True,
) -> ChatGoogleGenerativeAI:
    """
    Returns a configured Gemini LLM instance via LangChain.

    Args:
        model_name: The Gemini model identifier.
        temperature: Sampling temperature (0.0 = deterministic).
        streaming: Enable SSE token streaming for real-time UX.

    Returns:
        A ChatGoogleGenerativeAI instance ready for invocation.

    Raises:
        ValidationError: If GEMINI_API_KEY is not set in environment.
    """
    settings = get_settings()
    return ChatGoogleGenerativeAI(
        model=model_name,
        temperature=temperature,
        streaming=streaming,
        google_api_key=settings.GEMINI_API_KEY,
    )


def get_langfuse_callback() -> CallbackHandler:
    """
    Returns a Langfuse callback handler for LLM observability.

    Usage:
        llm.invoke(prompt, config={"callbacks": [get_langfuse_callback()]})

    Returns:
        A configured CallbackHandler instance.
    """
    settings = get_settings()
    return CallbackHandler(
        public_key=settings.LANGFUSE_PUBLIC_KEY
    )
