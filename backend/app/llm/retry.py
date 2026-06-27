"""Retry-on-validation-failure wrapper for ``LLMClient``.

When ``complete_structured`` raises ``LLMValidationError`` (the LLM returned
JSON that fails Pydantic parsing), this wrapper retries the call ONCE with a
corrective system message appended to the messages list. A second
``LLMValidationError`` is re-raised so the caller can surface the failure.

Network errors (``LLMError`` other than ``LLMValidationError``) are NOT
retried; they propagate unchanged.
"""

from __future__ import annotations

from typing import Any, TypeVar

from pydantic import BaseModel

from .client import LLMClient, LLMValidationError

T = TypeVar("T", bound=BaseModel)


CORRECTIVE_SYSTEM_MESSAGE: dict[str, str] = {
    "role": "system",
    "content": (
        "Your previous response was not valid JSON matching the requested "
        "schema. Respond ONLY with a single valid JSON object — no prose, "
        "no markdown fences."
    ),
}


class RetryingLLMClient(LLMClient):
    """One-shot retry wrapper that activates on ``LLMValidationError`` only.

    The constructor takes an inner ``LLMClient`` and forwards all attributes
    (``model``, ``extra_body``, ``api_key``) from it. Only
    ``complete_structured`` is wrapped; ``complete`` delegates without retry.
    """

    def __init__(self, inner: LLMClient) -> None:
        self._inner = inner
        # Mirror attributes so callers that introspect the client keep working.
        self.model = inner.model
        self.extra_body = inner.extra_body
        self.api_key = getattr(inner, "api_key", None)

    async def complete(
        self,
        messages: list[dict[str, Any]],
        *,
        reasoning_effort: str = "low",
    ) -> str:
        """Delegate to the inner client. No retry on raw completion."""
        return await self._inner.complete(messages, reasoning_effort=reasoning_effort)

    async def complete_structured(
        self,
        messages: list[dict[str, Any]],
        response_model: type[T],
        *,
        reasoning_effort: str = "low",
    ) -> T:
        """Call inner ``complete_structured``; retry once on validation failure."""
        try:
            return await self._inner.complete_structured(
                messages, response_model, reasoning_effort=reasoning_effort
            )
        except LLMValidationError:
            retry_messages = list(messages) + [CORRECTIVE_SYSTEM_MESSAGE]
            try:
                return await self._inner.complete_structured(
                    retry_messages, response_model, reasoning_effort=reasoning_effort
                )
            except LLMValidationError as second_exc:
                raise LLMValidationError(
                    f"structured output malformed after retry: {second_exc}",
                    raw_response=second_exc.raw_response,
                ) from second_exc
            # Non-validation errors propagate unchanged.


async def retry_structured_completion(
    client: LLMClient,
    messages: list[dict[str, Any]],
    response_model: type[T],
    *,
    reasoning_effort: str = "low",
) -> T:
    """Convenience: retry-on-validation for an arbitrary ``LLMClient``.

    Same semantics as ``RetryingLLMClient.complete_structured``. Useful when
    a caller already holds a plain ``LLMClient`` (e.g. a test that injects
    a spy) and wants ad-hoc retry.
    """
    try:
        return await client.complete_structured(
            messages, response_model, reasoning_effort=reasoning_effort
        )
    except LLMValidationError:
        retry_messages = list(messages) + [CORRECTIVE_SYSTEM_MESSAGE]
        try:
            return await client.complete_structured(
                retry_messages, response_model, reasoning_effort=reasoning_effort
            )
        except LLMValidationError as second_exc:
            raise LLMValidationError(
                f"structured output malformed after retry: {second_exc}",
                raw_response=second_exc.raw_response,
            ) from second_exc


__all__ = [
    "RetryingLLMClient",
    "CORRECTIVE_SYSTEM_MESSAGE",
    "retry_structured_completion",
]
