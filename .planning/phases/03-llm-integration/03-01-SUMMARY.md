---
phase: 03-llm-integration
plan: 01
subsystem: llm-integration
tags: [litellm, openrouter, cerebras, chat, structured-output, pydantic, fastapi]

# Dependency graph
requires:
  - phase: 02-backend-api-sse-streaming
    provides: REST API scaffolding, repos (User/Position/Trade/Watchlist/Chat), PriceCache, ChatRepository, FastAPI lifespan
provides:
  - LiteLLM-backed LLMClient routing through OpenRouter to Cerebras
  - Pydantic structured-output schemas (ChatResponse, TradeAction, WatchlistChange)
  - Portfolio context builder (cash + positions + watchlist + recent trades)
  - POST /api/chat endpoint with persistence, mock/real client selection, and executor hook
affects:
  - 03-02 plan: executor module + retry logic will plug into the execute_actions hook in chat.py
  - 04-frontend phase: frontend will POST to /api/chat

# Tech tracking
tech-stack:
  added:
    - litellm>=1.50.0
    - pydantic>=2.0 (explicit pin)
  patterns:
    - Lazy `__getattr__` router imports in app/api/__init__.py extend to chat_router
    - Module-guarded executor import (try/except ImportError) to coexist with Plan 03-02
    - asyncio.to_thread wrapping synchronous litellm.completion to avoid blocking the FastAPI event loop
    - Pydantic v2 ConfigDict(extra="forbid") on all request/response models

key-files:
  created:
    - backend/app/llm/__init__.py
    - backend/app/llm/schemas.py
    - backend/app/llm/prompts.py
    - backend/app/llm/context.py
    - backend/app/llm/client.py
    - backend/app/api/chat.py
    - backend/tests/llm/__init__.py
    - backend/tests/llm/test_client.py
    - backend/tests/llm/test_context.py
    - backend/tests/api/test_chat.py
  modified:
    - backend/pyproject.toml (added litellm + pydantic deps)
    - backend/uv.lock (regenerated)
    - backend/app/api/__init__.py (added chat_router export)
    - backend/app/api/deps.py (added get_chat_repo)
    - backend/app/api/schemas.py (added ChatRequest, ChatActionResult, ChatEndpointResponse)
    - backend/app/main.py (mounted chat_router; alphabetical order)

key-decisions:
  - "Use LiteLLM with OpenRouter + Cerebras provider routing per cerebras-inference skill (model openrouter/openai/gpt-oss-120b, extra_body={'provider':{'order':['cerebras']}})"
  - "Wrap litellm.completion in asyncio.to_thread to keep FastAPI event loop responsive"
  - "Expose ?model_override=mock|real query param for manual debugging without env mutation"
  - "Guard executor import with try/except ImportError so Plan 03-01 ships without requiring Plan 03-02's executor module"
  - "ChatRequest enforces message min_length=1 max_length=2000 plus whitespace-only rejection at validator layer"
  - "All monetary values stay in dollars (float) at the API boundary; the LLM context dict never exposes cents"

patterns-established:
  - "Pattern: Lazy executor wiring — Plan N writes a guarded import for Plan N+1's module so plans can land incrementally without breaking the test suite."
  - "Pattern: Spy on MockLLMClient.complete to assert what the LLM receives without hitting the network — captures the messages list for context-injection assertions."
  - "Pattern: ChatResponse.trades/watchlist_changes default to empty lists so the LLM can propose zero actions without violating the schema."

requirements-completed:
  - LLM-01
  - LLM-02
  - LLM-03
  - LLM-04
  - API-07

coverage:
  - id: D1
    description: "LiteLLM client with structured-output support routes through OpenRouter to Cerebras inference"
    requirement: LLM-01
    verification:
      - kind: unit
        ref: backend/tests/llm/test_client.py#test_client_complete_passes_response_format_when_provided
        status: pass
      - kind: unit
        ref: backend/tests/llm/test_client.py#test_client_complete_structured_raises_on_malformed_json
        status: pass
      - kind: unit
        ref: backend/tests/llm/test_client.py#test_client_complete_raises_llm_error_on_sdk_failure
        status: pass
    human_judgment: false
  - id: D2
    description: "Structured Pydantic schemas (ChatResponse, TradeAction, WatchlistChange) match PLAN.md section 9"
    requirement: LLM-02
    verification:
      - kind: unit
        ref: backend/tests/llm/test_client.py#test_mock_client_complete_structured_parses
        status: pass
    human_judgment: false
  - id: D3
    description: "Portfolio context builder exposes cash, positions with P&L, watchlist with live prices, total value, recent trades"
    requirement: LLM-03
    verification:
      - kind: unit
        ref: backend/tests/llm/test_context.py#test_build_portfolio_context_includes_required_keys
        status: pass
      - kind: unit
        ref: backend/tests/llm/test_context.py#test_build_portfolio_context_attaches_current_price
        status: pass
      - kind: unit
        ref: backend/tests/llm/test_context.py#test_build_portfolio_context_includes_recent_trades
        status: pass
      - kind: unit
        ref: backend/tests/llm/test_context.py#test_build_portfolio_context_watchlist_attaches_price
        status: pass
      - kind: unit
        ref: backend/tests/llm/test_context.py#test_build_portfolio_context_total_value_includes_cash_and_positions
        status: pass
    human_judgment: false
  - id: D4
    description: "POST /api/chat persists user + assistant messages into chat_messages table with actions JSON"
    requirement: LLM-04
    verification:
      - kind: integration
        ref: backend/tests/api/test_chat.py#test_chat_happy_path_with_mock
        status: pass
      - kind: integration
        ref: backend/tests/api/test_chat.py#test_chat_persists_user_and_assistant_messages
        status: pass
      - kind: integration
        ref: backend/tests/api/test_chat.py#test_chat_history_loaded_across_requests
        status: pass
    human_judgment: false
  - id: D5
    description: "POST /api/chat endpoint mounted and returns 200 with structured response (message, trades, watchlist_changes, actions_executed)"
    requirement: API-07
    verification:
      - kind: integration
        ref: backend/tests/api/test_chat.py#test_chat_endpoint_registered
        status: pass
      - kind: integration
        ref: backend/tests/api/test_chat.py#test_chat_response_matches_schema
        status: pass
      - kind: integration
        ref: backend/tests/api/test_chat.py#test_chat_loads_portfolio_context_into_messages
        status: pass
      - kind: integration
        ref: backend/tests/api/test_chat.py#test_chat_rejects_empty_message
        status: pass
      - kind: integration
        ref: backend/tests/api/test_chat.py#test_chat_rejects_whitespace_only_message
        status: pass
      - kind: integration
        ref: backend/tests/api/test_chat.py#test_chat_model_override_query_param
        status: pass
      - kind: integration
        ref: backend/tests/api/test_chat.py#test_chat_returns_503_on_llm_error
        status: pass
    human_judgment: false
  - id: D6
    description: "LLM_MOCK=true returns deterministic mock responses without a network call to OpenRouter"
    requirement: LLM-04
    verification:
      - kind: unit
        ref: backend/tests/llm/test_client.py#test_create_returns_mock_when_env_true
        status: pass
      - kind: unit
        ref: backend/tests/llm/test_client.py#test_create_returns_mock_when_env_yes
        status: pass
      - kind: unit
        ref: backend/tests/llm/test_client.py#test_create_returns_real_client_when_mock_off
        status: pass
      - kind: unit
        ref: backend/tests/llm/test_client.py#test_mock_client_complete_returns_json
        status: pass
    human_judgment: false

# Metrics
duration: 10min
completed: 2026-06-27
status: complete
---

# Phase 3 Plan 1: LLM Client + Chat Endpoint Summary

**LiteLLM-backed LLM client with OpenRouter/Cerebras structured outputs, Pydantic ChatResponse schema, and POST /api/chat endpoint that persists user+assistant messages and loads portfolio context for every request**

## Performance

- **Duration:** 10 min (576s)
- **Started:** 2026-06-27T12:51:52Z
- **Completed:** 2026-06-27T13:01:28Z
- **Tasks:** 2 (both auto/TDD)
- **Files modified:** 16

## Accomplishments

- Built the complete `app/llm/` package: `schemas.py` (Pydantic models), `prompts.py` (SYSTEM_PROMPT + message builder), `context.py` (portfolio context assembly), `client.py` (LLMClient + MockLLMClient + factory).
- Added `litellm>=1.50.0` and pinned `pydantic>=2.0` to `pyproject.toml`; regenerated `uv.lock`. Installed litellm 1.90.0.
- Wired POST `/api/chat` end-to-end: loads portfolio context, builds messages (system prompt + serialized context + recent history + new user), calls LLM, persists both user and assistant rows with actions JSON, and returns the parsed response.
- Added `?model_override=mock|real` query param for manual debugging, 503 on LLM errors, 422 on empty/whitespace messages.
- Wrote the executor hook guarded by `try/except ImportError` so Plan 03-02 can land `app/llm/executor.py` without breaking this plan's tests; in the meantime `actions_executed` is empty by design.
- 24 new pytest cases pass (9 LLM client + 5 LLM context + 10 chat endpoint). Full suite of 166 tests passes (no regressions).

## Task Commits

Each task was committed atomically:

1. **Task 1: Add litellm dependency and build the llm package (schemas, prompts, context, client)** - `236efac` (feat)
2. **Task 2: Build POST /api/chat endpoint, mount in main.py, wire LLM call + persistence + executor hook** - `550f8b4` (feat)

## Files Created/Modified

### Created
- `backend/app/llm/__init__.py` - Public API re-exports
- `backend/app/llm/schemas.py` - TradeAction, WatchlistChange, ChatResponse (extra="forbid")
- `backend/app/llm/prompts.py` - SYSTEM_PROMPT + build_messages(user, history, context)
- `backend/app/llm/context.py` - build_portfolio_context (cash, positions, watchlist, recent trades, total value)
- `backend/app/llm/client.py` - LLMClient (asyncio.to_thread-wrapped litellm.completion), MockLLMClient, create_llm_client factory, LLMError
- `backend/app/api/chat.py` - POST /api/chat handler with persistence, context building, and executor hook
- `backend/tests/llm/__init__.py` - Package marker
- `backend/tests/llm/test_client.py` - 9 tests (factory, mock client, SDK errors, malformed JSON, empty content, response_format forwarding)
- `backend/tests/llm/test_context.py` - 5 tests (required keys, current_price attachment, recent_trades, watchlist prices, total value math)
- `backend/tests/api/test_chat.py` - 10 tests (happy path, persistence, context injection, query-param override, history loading, error paths, schema round-trip)

### Modified
- `backend/pyproject.toml` - Added `litellm>=1.50.0` and `pydantic>=2.0` to dependencies
- `backend/uv.lock` - Regenerated by `uv sync`
- `backend/app/api/__init__.py` - Added `chat_router` to `__all__` and `__getattr__`
- `backend/app/api/deps.py` - Added `get_chat_repo` dependency provider
- `backend/app/api/schemas.py` - Added ChatRequest, ChatActionResult, ChatEndpointResponse
- `backend/app/main.py` - Imported chat_router and mounted it (alphabetical: chat, portfolio, system, watchlist)

## Decisions Made

- **Lazy router imports in `app/api/__init__.py` extend cleanly to chat_router.** The existing `__getattr__` pattern handles the new module without any structural change, so chat's imports stay lazy and avoid circular-import risk with deps.py.
- **Guarded executor import inside the chat handler.** `try: from app.llm.executor import execute_actions` falls back to `actions_executed = []` when the module is absent. This lets 03-01 ship and tests pass before 03-02 lands the executor. Plan 03-02 will replace this guard with a real call.
- **`asyncio.to_thread` around `litellm.completion`.** The LiteLLM SDK is synchronous; wrapping it keeps the FastAPI event loop responsive while the LLM call blocks. This addresses STRIDE threat T-03-04 (DoS via event-loop stall).
- **`model_override` query param.** Without it, manual testing would require mutating the env and reloading the app. The pattern (`?model_override=mock|real`) is regex-restricted to two values so it cannot be abused as an open parameter.
- **All amounts in dollars (float) at the API boundary.** The LLM context builder converts from cents (via from_cents on UserRepository.get) and the response keeps dollars. No cents ever cross into the chat surface.

## Deviations from Plan

None - plan executed exactly as written. The only delta is cosmetic: ruff auto-fix applied trailing newlines and removed an unused `patch` import from `test_client.py` and `field` from `main.py` (the latter is a pre-existing issue exposed by the lint pass). The `field` removal is part of the commit because ruff modified the file; this is a no-op semantic change.

## Issues Encountered

- Initial ruff pass surfaced 13 lint issues across new files: 11 missing trailing newlines (W292), 1 unused `patch` import in test_client.py, 1 unused `field` import in main.py. Resolved with `ruff check --fix`; behavior unaffected.

## User Setup Required

None - no external service configuration required. The `OPENROUTER_API_KEY` is already configured in the project's `.env` file (per the `cerebras-inference` skill and CLAUDE.md). `LLM_MOCK=true` is the recommended setting for tests and local development; production deployments omit it to route through the real Cerebras provider.

## Next Phase Readiness

- The chat surface is fully functional with mock LLM; the real OpenRouter route is wired and tested for the happy path and error paths.
- Plan 03-02 will land `app/llm/executor.py` providing `execute_actions(response, position_repo, trade_repo, watchlist_repo, user_repo, price_cache) -> list[dict]`. The handler already calls this function inside the guarded import block; removing the `try/except ImportError` and the empty fallback is a one-line change in `app/api/chat.py`.
- Plan 03-02 will also add a one-shot retry on `LLMError` raised by `complete_structured` (T-03-03 mitigation) — this is owned by 03-02 and does not require changes to the client or context module.
- Frontend integration in Phase 4 will POST to `/api/chat` and render the response; the response shape (`message`, `trades`, `watchlist_changes`, `actions_executed`) is stable and documented.

---

*Phase: 03-llm-integration*
*Completed: 2026-06-27*
