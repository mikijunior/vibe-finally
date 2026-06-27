"""LiteLLM-backed chat client with structured output support.

Provides:
- ``LLMError`` — exception wrapping any LiteLLM or upstream failure.
- ``LLMValidationError`` — subclass of ``LLMError`` raised on Pydantic
  validation failure inside ``complete_structured``.
- ``LLMClient`` — thin async wrapper around ``litellm.completion`` that
  routes through OpenRouter with Cerebras as the inference provider.
- ``MockLLMClient`` — deterministic mock for tests and ``LLM_MOCK=true``
  (implementation lives in ``app.llm.mock``).
- ``create_llm_client`` — factory that picks the right client based on env
  and wraps it in ``RetryingLLMClient`` for automatic one-shot retry on
  validation failure.

The retry wrapper itself lives in ``app.llm.retry``; it is imported lazily
inside ``create_llm_client`` to avoid a circular import.
"""

from __future__ import annotations

import asyncio
import os
from typing import Any, TypeVar

import litellm
from pydantic import BaseModel, ValidationError

T = TypeVar("T", bound=BaseModel)


class LLMError(Exception):
    """Raised when the LLM call fails or returns unusable output.

    Attributes:
        raw_response: The string content returned by the model (if any).
            Useful for diagnostics when the JSON fails to parse.
    """

    def __init__(self, message: str, raw_response: str | None = None) -> None:
        super().__init__(message)
        self.raw_response = raw_response


class LLMValidationError(LLMError):
    """Raised when the LLM response cannot be parsed into the requested schema.

    Subclass of ``LLMError`` so existing ``except LLMError`` handlers keep
    working. ``raw_response`` carries the malformed JSON for diagnostics.
    """


class LLMClient:
    """Async wrapper around ``litellm.completion`` with structured outputs.

    Defaults to the OpenRouter → Cerebras route from the
    ``cerebras-inference`` skill. Use ``LLM_MOCK=true`` to short-circuit
    to a deterministic mock client instead.
    """

    DEFAULT_MODEL = "openrouter/openai/gpt-oss-120b"
    DEFAULT_EXTRA_BODY: dict[str, Any] = {"provider": {"order": ["cerebras"]}}

    def __init__(
        self,
        model: str | None = None,
        extra_body: dict[str, Any] | None = None,
    ) -> None:
        self.model = model or self.DEFAULT_MODEL
        self.extra_body = extra_body if extra_body is not None else dict(self.DEFAULT_EXTRA_BODY)
        self.api_key = os.environ.get("OPENROUTER_API_KEY")

    async def complete(
        self,
        messages: list[dict[str, Any]],
        *,
        reasoning_effort: str = "low",
    ) -> str:
        """Call the LLM and return the raw text content.

        Wraps the synchronous ``litellm.completion`` in ``asyncio.to_thread``
        so the FastAPI event loop is not blocked. Raises ``LLMError`` on any
        SDK exception or empty/None content.
        """
        try:
            response = await asyncio.to_thread(
                litellm.completion,
                model=self.model,
                messages=messages,
                reasoning_effort=reasoning_effort,
                extra_body=self.extra_body,
                api_key=self.api_key,
            )
        except Exception as exc:  # noqa: BLE001 - litellm raises many subtypes
            raise LLMError(f"litellm.completion failed: {exc}") from exc

        try:
            content = response.choices[0].message.content
        except (AttributeError, IndexError, KeyError) as exc:
            raise LLMError("malformed response: no choices[0].message.content") from exc

        if not content:
            raise LLMError("empty response from LLM")

        return content

    async def complete_structured(
        self,
        messages: list[dict[str, Any]],
        response_model: type[T],
        *,
        reasoning_effort: str = "low",
    ) -> T:
        """Call the LLM and parse the response into a Pydantic model.

        Validation errors are wrapped in ``LLMValidationError`` so the
        retry wrapper can distinguish them from network failures.
        """
        content = await self.complete(messages, reasoning_effort=reasoning_effort)
        try:
            return response_model.model_validate_json(content)
        except ValidationError as exc:
            raise LLMValidationError(
                f"malformed structured output: {exc}",
                raw_response=content,
            ) from exc


def _inner_create_llm_client() -> LLMClient:
    """Inner factory: pick ``MockLLMClient`` or ``LLMClient`` based on env."""
    mock_flag = (os.environ.get("LLM_MOCK") or "").strip().lower()
    if mock_flag in {"1", "true", "yes"}:
        # Imported here so the factory stays a single entry point and
        # ``client`` module doesn't import ``mock`` at top level (mock is
        # the simpler, no-dependency implementation).
        from .mock import MockLLMClient

        return MockLLMClient()
    return LLMClient()


def create_llm_client() -> LLMClient:
    """Factory: returns a ``RetryingLLMClient`` wrapping the appropriate inner client.

    ``RetryingLLMClient`` provides a one-shot retry with a corrective system
    message when ``complete_structured`` raises ``LLMValidationError``. Lazy
    import keeps ``client.py`` and ``retry.py`` free of circular dependencies.
    """
    from .retry import RetryingLLMClient

    return RetryingLLMClient(_inner_create_llm_client())


# Re-export ``MockLLMClient`` so Plan 03-01 callers (which imported it from
# this module) continue to work. Implementation lives in ``app.llm.mock``.
from .mock import MockLLMClient  # noqa: E402


__all__ = [
    "LLMClient",
    "LLMError",
    "LLMValidationError",
    "MockLLMClient",
    "create_llm_client",
]