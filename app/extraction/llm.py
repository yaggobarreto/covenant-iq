"""Factory for the chat model the extraction chains bind structured output to.

Kept as a single seam so tests never construct a real model: every chain
function below takes an optional `llm` argument, and the API layer is the
only caller that lets this factory build a real one.
"""

from __future__ import annotations

from functools import lru_cache

from app.config import settings


class MissingAPIKeyError(RuntimeError):
    pass


@lru_cache
def get_chat_model(temperature: float = 0.0):
    if settings.llm_provider != "openai":
        raise ValueError(f"Unsupported LLM provider: {settings.llm_provider!r}")
    if not settings.openai_api_key:
        raise MissingAPIKeyError(
            "OPENAI_API_KEY is not set. Extraction needs a real LLM call; "
            "set it in your environment or .env file. The test suite does not "
            "need this — it injects a fake model instead."
        )
    from langchain_openai import ChatOpenAI

    return ChatOpenAI(model=settings.llm_model, api_key=settings.openai_api_key, temperature=temperature)
