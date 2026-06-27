"""Chat endpoint — loads portfolio context, calls LLM, persists messages, returns structured response.

The endpoint is mounted at ``POST /api/chat`` and is the public surface for
the FinAlly AI assistant. Flow:

    1. Persist the user message into ``chat_messages``.
    2. Load recent chat history (newest first; reverse to oldest first).
    3. Build portfolio context (cash, positions w/ P&L, watchlist, recent trades).
    4. Build the messages list (system prompt + serialized context + history + new user).
    5. Call the LLM via ``RetryingLLMClient.complete_structured`` (Plan 03-02).
       The factory in ``client.create_llm_client`` automatically wraps the
       inner client with ``RetryingLLMClient`` so a malformed first response
       triggers a one-shot retry; a second failure surfaces as 503.
    6. Pass the parsed ``ChatResponse`` to ``execute_actions`` which applies
       each trade and watchlist change through the same validation as
       manual endpoints. Per-action failures are captured and reported.
    7. Persist the assistant message with the actions JSON.
    8. Return the parsed response to the client.
"""

from __future__ import annotations

import logging
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.api.deps import (
    get_chat_repo,
    get_position_repo,
    get_price_cache,
    get_snapshot_repo,
    get_trade_repo,
    get_user_repo,
    get_watchlist_repo,
)
from app.api.schemas import (
    ChatActionResult,
    ChatEndpointResponse,
    ChatRequest,
)
from app.db.repositories import (
    ChatRepository,
    PositionRepository,
    SnapshotRepository,
    TradeRepository,
    UserRepository,
    WatchlistRepository,
)
from app.llm import (
    ChatResponse,
    LLMClient,
    LLMError,
    MockLLMClient,
    build_messages,
    build_portfolio_context,
    create_llm_client,
)
from app.llm.executor import ExecutorRepos, execute_actions
from app.market.cache import PriceCache

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/chat", tags=["chat"])


@router.post("", response_model=ChatEndpointResponse)
async def chat(
    body: ChatRequest,
    user_repo: Annotated[UserRepository, Depends(get_user_repo)],
    position_repo: Annotated[PositionRepository, Depends(get_position_repo)],
    trade_repo: Annotated[TradeRepository, Depends(get_trade_repo)],
    watchlist_repo: Annotated[WatchlistRepository, Depends(get_watchlist_repo)],
    snapshot_repo: Annotated[SnapshotRepository, Depends(get_snapshot_repo)],
    chat_repo: Annotated[ChatRepository, Depends(get_chat_repo)],
    price_cache: Annotated[PriceCache, Depends(get_price_cache)],
    model_override: Annotated[str | None, Query(pattern="^(mock|real)$")] = None,
) -> ChatEndpointResponse:
    """Send a message to the FinAlly AI assistant and return its structured response."""
    # 1. Persist user message immediately (audit trail).
    await chat_repo.insert(role="user", content=body.message, actions=None)

    # 2. Load history (newest first); reverse to oldest first for the LLM.
    history_rows = await chat_repo.list_recent(limit=10)
    history_oldest_first = list(reversed(history_rows))

    # 3. Build portfolio context + messages.
    context = await build_portfolio_context(
        price_cache, user_repo, position_repo, trade_repo, watchlist_repo
    )
    messages = build_messages(body.message, history_oldest_first, context)

    # 4. Choose LLM client. model_override trumps env for manual testing.
    if model_override == "mock":
        client: LLMClient = MockLLMClient()
    elif model_override == "real":
        client = LLMClient()
    else:
        client = create_llm_client()

    # 5. Call the LLM (with one-shot retry on validation failure baked in).
    # Failure -> 503 with the underlying message logged.
    try:
        response: ChatResponse = await client.complete_structured(messages, ChatResponse)
    except LLMError as exc:
        logger.exception("LLM call failed; raw_response=%r", exc.raw_response)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"LLM call failed: {exc}",
        ) from exc

    # 6. Auto-execute trades and watchlist changes through the executor.
    repos = ExecutorRepos(
        user_repo=user_repo,
        position_repo=position_repo,
        trade_repo=trade_repo,
        watchlist_repo=watchlist_repo,
        snapshot_repo=snapshot_repo,
        price_cache=price_cache,
        market_source=None,
    )
    execution_result = await execute_actions(response, repos)
    actions_executed_raw: list[dict[str, Any]] = execution_result.to_list()

    # 7. Persist the assistant message with the actions JSON.
    actions_payload: dict[str, Any] = {
        "trades": [t.model_dump() for t in response.trades],
        "watchlist_changes": [w.model_dump() for w in response.watchlist_changes],
        "actions_executed": actions_executed_raw,
    }
    await chat_repo.insert(
        role="assistant", content=response.message, actions=actions_payload
    )

    # 8. Convert raw action results into typed ChatActionResult objects.
    action_results: list[ChatActionResult] = []
    for entry in actions_executed_raw:
        if entry.get("type") == "trade":
            action_results.append(
                ChatActionResult(
                    type="trade",
                    ticker=entry["ticker"],
                    status=entry["status"],
                    detail=entry.get("detail"),
                    side=entry.get("side"),
                    quantity=entry.get("quantity"),
                )
            )
        elif entry.get("type") == "watchlist":
            action_results.append(
                ChatActionResult(
                    type="watchlist",
                    ticker=entry["ticker"],
                    status=entry["status"],
                    detail=entry.get("detail"),
                    action=entry.get("action"),
                )
            )

    return ChatEndpointResponse(
        message=response.message,
        trades=[t.model_dump() for t in response.trades],
        watchlist_changes=[w.model_dump() for w in response.watchlist_changes],
        actions_executed=action_results,
    )
