"""Tests for the retry-on-validation wrapper and LLMValidationError."""

from __future__ import annotations

import pytest

from app.llm import (
    CORRECTIVE_SYSTEM_MESSAGE,
    LLMError,
    LLMValidationError,
    RetryingLLMClient,
)
from app.llm.schemas import ChatResponse


class _FakeClient:
    """Minimal ``LLMClient``-shaped double for retry tests.

    ``responses`` is a list of either ChatResponse instances or exceptions
    raised in order. The fake records every call so tests can inspect how
    many times the inner client was invoked and with what arguments.
    """

    def __init__(self, responses: list) -> None:
        self._responses = list(responses)
        self.calls: list[dict] = []
        self.model = "fake"
        self.extra_body: dict = {}
        self.api_key = None

    async def complete(self, messages, *, reasoning_effort="low") -> str:  # noqa: D401
        raise NotImplementedError

    async def complete_structured(self, messages, response_model, *, reasoning_effort="low"):
        self.calls.append({"messages": list(messages), "reasoning_effort": reasoning_effort})
        if not self._responses:
            raise AssertionError("FakeClient: no more scripted responses")
        item = self._responses.pop(0)
        if isinstance(item, BaseException):
            raise item
        return item


# Avoid importing BaseModel at module level in a way that conflicts; inline:


def test_validation_error_subclass():
    """LLMValidationError is an LLMError subclass carrying raw_response."""
    err = LLMValidationError("bad", raw_response="not json")
    assert isinstance(err, LLMError)
    assert err.raw_response == "not json"


@pytest.mark.asyncio
async def test_retry_succeeds_on_second_attempt():
    """A retry wrapper converts a single validation failure into a success."""
    good = ChatResponse(message="ok", trades=[], watchlist_changes=[])
    inner = _FakeClient(
        [
            LLMValidationError("bad json", raw_response="not json"),
            good,
        ]
    )
    wrapper = RetryingLLMClient(inner)

    result = await wrapper.complete_structured(
        [{"role": "user", "content": "hi"}],
        ChatResponse,
    )
    assert result.message == "ok"
    assert len(inner.calls) == 2


@pytest.mark.asyncio
async def test_retry_fails_after_two_validation_errors():
    """Two consecutive validation failures surface as LLMValidationError."""
    inner = _FakeClient(
        [
            LLMValidationError("first bad", raw_response="bad 1"),
            LLMValidationError("second bad", raw_response="bad 2"),
        ]
    )
    wrapper = RetryingLLMClient(inner)

    with pytest.raises(LLMValidationError) as excinfo:
        await wrapper.complete_structured(
            [{"role": "user", "content": "hi"}], ChatResponse
        )
    assert excinfo.value.raw_response == "bad 2"
    assert len(inner.calls) == 2


@pytest.mark.asyncio
async def test_retry_does_not_retry_on_network_error():
    """A plain LLMError (network failure) is NOT retried; it propagates."""
    inner = _FakeClient([LLMError("network down")])
    wrapper = RetryingLLMClient(inner)

    with pytest.raises(LLMError) as excinfo:
        await wrapper.complete_structured(
            [{"role": "user", "content": "hi"}], ChatResponse
        )
    assert "network down" in str(excinfo.value)
    assert len(inner.calls) == 1


@pytest.mark.asyncio
async def test_retry_appends_corrective_message():
    """The retry call appends CORRECTIVE_SYSTEM_MESSAGE to the messages list."""
    good = ChatResponse(message="ok")
    inner = _FakeClient(
        [
            LLMValidationError("first bad", raw_response="bad"),
            good,
        ]
    )
    wrapper = RetryingLLMClient(inner)

    first_messages = [{"role": "user", "content": "hi"}]
    await wrapper.complete_structured(first_messages, ChatResponse)

    second_messages = inner.calls[1]["messages"]
    assert second_messages == first_messages + [CORRECTIVE_SYSTEM_MESSAGE]


@pytest.mark.asyncio
async def test_retry_structured_completion_helper():
    """The module-level helper retries when the inner client raises."""
    good = ChatResponse(message="ok")
    inner = _FakeClient(
        [
            LLMValidationError("bad", raw_response="bad"),
            good,
        ]
    )
    from app.llm.retry import retry_structured_completion

    result = await retry_structured_completion(
        inner,
        [{"role": "user", "content": "hi"}],
        ChatResponse,
    )
    assert result.message == "ok"
    assert len(inner.calls) == 2
