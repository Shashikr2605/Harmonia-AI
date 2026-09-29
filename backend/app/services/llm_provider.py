from __future__ import annotations

import logging
from typing import Optional, Protocol, runtime_checkable

from app.config import get_settings

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Protocol (structural interface)
# ---------------------------------------------------------------------------


@runtime_checkable
class LLMProvider(Protocol):
    """
    Seam for an LLM completion backend.  Not wired into any endpoint for the
    MVP — it's a hook point for the RAG copilot in a later iteration.
    """

    async def generate(self, prompt: str) -> str:
        ...


# ---------------------------------------------------------------------------
# Implementations
# ---------------------------------------------------------------------------


class MockLLMProvider:
    """
    Returns a canned response.  Used in tests and when no real LLM is
    configured.  The app starts and all MVP endpoints work with this provider
    active — ANTHROPIC_API_KEY is intentionally not required.
    """

    async def generate(self, prompt: str) -> str:  # noqa: ARG002
        return "[MockLLMProvider] LLM not configured — this is a stub response."


class ExternalLLMProvider:
    """
    Wraps the Anthropic Claude API.  Silently falls back to MockLLMProvider
    behaviour if ANTHROPIC_API_KEY is absent or empty, so the app never fails
    to start because of a missing LLM key.
    """

    def __init__(self) -> None:
        settings = get_settings()
        self._api_key: Optional[str] = settings.anthropic_api_key
        if not self._api_key:
            logger.info(
                "ANTHROPIC_API_KEY not set — ExternalLLMProvider will return stub responses"
            )

    async def generate(self, prompt: str) -> str:
        if not self._api_key:
            return "[ExternalLLMProvider] ANTHROPIC_API_KEY not configured."

        # Lazy import so the package is optional at runtime
        try:
            import anthropic  # type: ignore[import]
        except ImportError:
            logger.warning("anthropic package not installed; returning stub response")
            return "[ExternalLLMProvider] anthropic package not installed."

        client = anthropic.AsyncAnthropic(api_key=self._api_key)
        message = await client.messages.create(
            model="claude-opus-4-5",
            max_tokens=1024,
            messages=[{"role": "user", "content": prompt}],
        )
        return message.content[0].text


# ---------------------------------------------------------------------------
# Factory
# ---------------------------------------------------------------------------


def get_llm_provider() -> LLMProvider:
    """
    Returns ExternalLLMProvider if ANTHROPIC_API_KEY is set, MockLLMProvider
    otherwise.  Wire this into endpoints when the RAG copilot is implemented.
    """
    settings = get_settings()
    if settings.anthropic_api_key:
        return ExternalLLMProvider()
    return MockLLMProvider()
