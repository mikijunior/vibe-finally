"""LiteLLM-backed chat client with structured output support.

Provides:
- ``LLMError`` — exception wrapping any LiteLLM or upstream failure.
- ``LLMClient`` — thin async wrapper around ``litellm.completion`` that
  routes through OpenRouter with Cerebras as the inference provider.
- ``MockLLMClient`` — deterministic mock for tests and ``LLM_MOCK=true``.
- ``create_llm_client`` — factory that picks the right client based on env.

Retry logic for malformed structured output lives in Plan 03-02; this client
is intentionally simple so the executor wiring is the only variable.
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

        Validation errors are wrapped in ``LLMError`` so the caller can decide
        whether to retry (Plan 03-02) or surface to the user.
        """
        content = await self.complete(messages, reasoning_effort=reasoning_effort)
        try:
            return response_model.model_validate_json(content)
        except ValidationError as exc:
            raise LLMError(f"malformed structured output: {exc}", raw_response=content) from exc


class MockLLMClient(LLMClient):
    """Deterministic mock client for tests and ``LLM_MOCK=true``.

    Returns a hard-coded JSON echo of the user's last message. The mock does
    not make any network calls and never raises.
    """

    async def complete(
        self,
        messages: list[dict[str, Any]],
        *,
        reasoning_effort: str = "low",
    ) -> str:
        last_user = ""
        for msg in reversed(messages):
            if msg.get("role") == "user":
                last_user = msg.get("content") or ""
                break
        return (
            '{"message": "Mock response to: ' + last_user + '", '
            '"trades": [], "watchlist_changes": []}'
        )

    async def complete_structured(
        self,
        messages: list[dict[str, Any]],
        response_model: type[T],
        *,
        reasoning_effort: str = "low",
    ) -> T:
        content = await self.complete(messages, reasoning_effort=reasoning_effort)
        return response_model.model_validate_json(content)


def create_llm_client() -> LLMClient:
    """Factory: returns ``MockLLMClient`` when ``LLM_MOCK`` is truthy.

    Recognized truthy values: ``1``, ``true``, ``yes`` (case-insensitive).
    Otherwise returns a real ``LLMClient`` (requires ``OPENROUTER_API_KEY``
    in the environment for successful API calls).
    """
    mock_flag = (os.environ.get("LLM_MOCK") or "").strip().lower()
    if mock_flag in {"1", "true", "yes"}:
        return MockLLMClient()
    return LLMClient()