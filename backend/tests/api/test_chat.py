"""Tests for the ``POST /api/chat`` endpoint.

These tests run with ``LLM_MOCK=true`` so the LLM call is deterministic.
Plan 03-02 activates the executor; here we assert the parsing, persistence,
and response-shape contract only.
"""

from __future__ import annotations

import pytest

from app.db.repositories import ChatRepository
from app.llm import MockLLMClient


@pytest.fixture(autouse=True)
def _force_mock_llm(monkeypatch):
    """Force LLM_MOCK=true for every test in this module."""
    monkeypatch.setenv("LLM_MOCK", "true")


@pytest.mark.asyncio
async def test_chat_happy_path_with_mock(seeded_client):
    """POST /api/chat returns 200 with the mock LLM's message echoed back."""
    response = seeded_client.post(
        "/api/chat", json={"message": "What's my portfolio?"}
    )
    assert response.status_code == 200, response.text
    body = response.json()

    assert body["message"].startswith("Mock response to:")
    assert "What's my portfolio?" in body["message"]
    assert body["trades"] == []
    assert body["watchlist_changes"] == []
    # Executor not yet wired (Plan 03-02) — actions_executed must be empty.
    assert body["actions_executed"] == []


@pytest.mark.asyncio
async def test_chat_persists_user_and_assistant_messages(seeded_client):
    """After one chat call, chat_messages contains 2 rows: user, assistant."""
    response = seeded_client.post("/api/chat", json={"message": "ping"})
    assert response.status_code == 200

    repo = ChatRepository()
    rows = await repo.list_all()
    assert len(rows) == 2
    assert rows[0]["role"] == "user"
    assert rows[0]["content"] == "ping"
    assert rows[0]["actions"] is None

    assert rows[1]["role"] == "assistant"
    assert rows[1]["content"].startswith("Mock response to:")
    assert rows[1]["actions"] is not None
    assert "trades" in rows[1]["actions"]
    assert "watchlist_changes" in rows[1]["actions"]
    assert "actions_executed" in rows[1]["actions"]


@pytest.mark.asyncio
async def test_chat_loads_portfolio_context_into_messages(seeded_client, monkeypatch):
    """The messages list sent to the LLM embeds the portfolio context as JSON."""
    # Buy one share of AAPL so the portfolio has a position to summarize.
    buy = seeded_client.post(
        "/api/portfolio/trade", json={"ticker": "AAPL", "quantity": 1, "side": "buy"}
    )
    assert buy.status_code == 200, buy.text

    captured: dict = {}

    real_complete = MockLLMClient.complete

    async def spy_complete(self, messages, *, reasoning_effort="low"):
        captured["messages"] = messages
        return await real_complete(self, messages, reasoning_effort=reasoning_effort)

    monkeypatch.setattr(MockLLMClient, "complete", spy_complete)

    response = seeded_client.post("/api/chat", json={"message": "summary please"})
    assert response.status_code == 200

    messages = captured["messages"]
    # First system message is the persona prompt; second carries portfolio context.
    assert messages[0]["role"] == "system"
    assert "FinAlly" in messages[0]["content"]
    assert messages[1]["role"] == "system"
    context_payload = messages[1]["content"]
    assert "cash_balance_dollars" in context_payload
    assert "total_value_dollars" in context_payload
    assert "positions" in context_payload


@pytest.mark.asyncio
async def test_chat_rejects_empty_message(client):
    """POST /api/chat with empty message returns 422."""
    response = client.post("/api/chat", json={"message": ""})
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_chat_rejects_whitespace_only_message(client):
    """POST /api/chat with whitespace-only message returns 422."""
    response = client.post("/api/chat", json={"message": "   \n\t  "})
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_chat_model_override_query_param(seeded_client, monkeypatch):
    """``?model_override=mock`` forces MockLLMClient even when LLM_MOCK is unset.

    We unset ``LLM_MOCK`` so the factory would otherwise return a real
    ``LLMClient``. Without ``OPENROUTER_API_KEY`` a real call would 503.
    With the override, the mock client is used and the call succeeds.
    """
    monkeypatch.delenv("LLM_MOCK", raising=False)
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)

    response = seeded_client.post(
        "/api/chat?model_override=mock", json={"message": "hi"}
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["message"].startswith("Mock response to:")


@pytest.mark.asyncio
async def test_chat_history_loaded_across_requests(seeded_client, monkeypatch):
    """Two chat calls load prior history into the second call's messages."""
    captured: list = []
    real_complete = MockLLMClient.complete

    async def spy_complete(self, messages, *, reasoning_effort="low"):
        captured.append(list(messages))
        return await real_complete(self, messages, reasoning_effort=reasoning_effort)

    monkeypatch.setattr(MockLLMClient, "complete", spy_complete)

    # First call
    r1 = seeded_client.post("/api/chat", json={"message": "first"})
    assert r1.status_code == 200

    # Second call — prior history should now be in the messages list.
    r2 = seeded_client.post("/api/chat", json={"message": "second"})
    assert r2.status_code == 200

    # chat_messages table now has 4 rows (2 user + 2 assistant).
    repo = ChatRepository()
    all_rows = await repo.list_all()
    assert len(all_rows) == 4
    recent_rows = await repo.list_recent(limit=10)
    assert len(recent_rows) == 4

    # Inspect the second call's messages list.
    second_messages = captured[1]
    roles = [m["role"] for m in second_messages]
    # Expect: system, system(context), user(first), assistant(first), user(second)
    assert roles[0] == "system"
    assert "FinAlly" in second_messages[0]["content"]
    assert roles[1] == "system"
    assert "cash_balance_dollars" in second_messages[1]["content"]
    assert "user" in roles
    assert "assistant" in roles
    # Final user message is the latest input
    assert second_messages[-1]["role"] == "user"
    assert second_messages[-1]["content"] == "second"


@pytest.mark.asyncio
async def test_chat_returns_503_on_llm_error(seeded_client, monkeypatch):
    """When the LLM client raises LLMError, the endpoint returns 503."""
    from app.llm import LLMError

    async def boom(self, messages, *, reasoning_effort="low"):
        raise LLMError("network down")

    monkeypatch.setattr(MockLLMClient, "complete", boom)

    response = seeded_client.post("/api/chat", json={"message": "hi"})
    assert response.status_code == 503
    assert "LLM call failed" in response.json()["detail"]


@pytest.mark.asyncio
async def test_chat_endpoint_registered(seeded_client):
    """POST /api/chat is mounted in the FastAPI app (not 404)."""
    response = seeded_client.post("/api/chat", json={"message": "ping"})
    assert response.status_code != 404


@pytest.mark.asyncio
async def test_chat_response_matches_schema(seeded_client):
    """Response body round-trips through ChatEndpointResponse without errors."""
    from app.api.schemas import ChatEndpointResponse

    response = seeded_client.post("/api/chat", json={"message": "ping"})
    assert response.status_code == 200
    body = response.json()

    # Validate via Pydantic — extra="forbid" is enforced on the input side;
    # response side allows extra fields in JSON but our shape is well-defined.
    parsed = ChatEndpointResponse.model_validate(body)
    assert parsed.message.startswith("Mock response to:")
    assert isinstance(parsed.trades, list)
    assert isinstance(parsed.watchlist_changes, list)
    assert isinstance(parsed.actions_executed, list)
