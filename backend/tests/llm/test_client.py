"""Tests for the LLM client factory and structured-output behavior."""

from __future__ import annotations

from unittest.mock import MagicMock

import litellm

from app.llm import (
    ChatResponse,
    LLMClient,
    LLMError,
    MockLLMClient,
    create_llm_client,
)


def test_create_returns_real_client_when_mock_off(monkeypatch):
    """With LLM_MOCK unset, create_llm_client returns a real LLMClient."""
    monkeypatch.delenv("LLM_MOCK", raising=False)
    client = create_llm_client()
    assert isinstance(client, LLMClient)
    assert not isinstance(client, MockLLMClient)


def test_create_returns_mock_when_env_true(monkeypatch):
    """LLM_MOCK=true routes to MockLLMClient."""
    monkeypatch.setenv("LLM_MOCK", "true")
    client = create_llm_client()
    assert isinstance(client, MockLLMClient)


def test_create_returns_mock_when_env_yes(monkeypatch):
    """LLM_MOCK=yes (alternate truthy value) routes to MockLLMClient."""
    monkeypatch.setenv("LLM_MOCK", "yes")
    client = create_llm_client()
    assert isinstance(client, MockLLMClient)


async def test_mock_client_complete_returns_json():
    """MockLLMClient.complete returns a JSON string containing the user message."""
    client = MockLLMClient()
    result = await client.complete([{"role": "user", "content": "hi"}])
    assert isinstance(result, str)
    assert result.startswith('{"message"')
    assert "Mock response to: hi" in result


async def test_mock_client_complete_structured_parses():
    """MockLLMClient.complete_structured returns a valid ChatResponse."""
    client = MockLLMClient()
    response = await client.complete_structured(
        [{"role": "user", "content": "hello"}],
        ChatResponse,
    )
    assert isinstance(response, ChatResponse)
    assert "Mock response to: hello" in response.message
    assert response.trades == []
    assert response.watchlist_changes == []


async def test_client_complete_raises_llm_error_on_sdk_failure(monkeypatch):
    """When litellm.completion raises, LLMClient.complete wraps it as LLMError."""

    def _raise(*args, **kwargs):
        raise litellm.APIError("network down", llm_provider="openrouter", model="x")

    monkeypatch.setattr(litellm, "completion", _raise)

    client = LLMClient()
    try:
        await client.complete([{"role": "user", "content": "x"}])
    except LLMError as exc:
        assert "litellm.completion failed" in str(exc)
        return
    raise AssertionError("Expected LLMError but no exception was raised")


async def test_client_complete_structured_raises_on_malformed_json(monkeypatch):
    """When litellm.completion returns non-JSON content, complete_structured raises LLMError."""
    fake_response = MagicMock()
    fake_response.choices = [MagicMock()]
    fake_response.choices[0].message.content = "not valid json"

    def _fake_complete(*args, **kwargs):
        return fake_response

    monkeypatch.setattr(litellm, "completion", _fake_complete)

    client = LLMClient()
    try:
        await client.complete_structured(
            [{"role": "user", "content": "x"}],
            ChatResponse,
        )
    except LLMError as exc:
        assert exc.raw_response == "not valid json"
        return
    raise AssertionError("Expected LLMError on malformed JSON but no exception was raised")


async def test_client_complete_raises_on_empty_content(monkeypatch):
    """Empty string content from litellm.completion raises LLMError."""
    fake_response = MagicMock()
    fake_response.choices = [MagicMock()]
    fake_response.choices[0].message.content = ""

    def _fake_complete(*args, **kwargs):
        return fake_response

    monkeypatch.setattr(litellm, "completion", _fake_complete)

    client = LLMClient()
    try:
        await client.complete([{"role": "user", "content": "x"}])
    except LLMError as exc:
        assert "empty" in str(exc).lower()
        return
    raise AssertionError("Expected LLMError on empty content")


async def test_client_complete_passes_response_format_when_provided(monkeypatch):
    """LLMClient.complete forwards kwargs to litellm.completion."""
    captured: dict = {}

    def _fake_complete(*args, **kwargs):
        captured.update(kwargs)
        fake = MagicMock()
        fake.choices = [MagicMock()]
        fake.choices[0].message.content = "ok"
        return fake

    monkeypatch.setattr(litellm, "completion", _fake_complete)

    client = LLMClient()
    await client.complete(
        [{"role": "user", "content": "x"}],
        reasoning_effort="low",
    )

    assert captured["model"] == "openrouter/openai/gpt-oss-120b"
    assert captured["reasoning_effort"] == "low"
    assert captured["extra_body"] == {"provider": {"order": ["cerebras"]}}
    assert captured["api_key"] is None or isinstance(captured["api_key"], (str, type(None)))
