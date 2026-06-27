---
phase: 03-llm-integration
plan: 02
subsystem: llm-integration
tags: [executor, retry, mock-llm, structured-output, pydantic-validation, fastapi, asyncio]

# Dependency graph
requires:
  - phase: 03-llm-integration
    plan: 01
    provides: LLMClient + MockLLMClient + create_llm_client factory + ChatResponse schema + /api/chat endpoint with ImportError-guarded executor hook
  - phase: 02-backend-api-sse-streaming
    provides: User/Position/Trade/Watchlist/Snapshot/Chat repositories, PriceCache, MarketDataSource, FastAPI lifespan
provides:
  - Auto-execution of LLM-suggested trades and watchlist changes via execute_actions
  - Per-action error capture (one bad action never aborts the batch)
  - One-shot retry wrapper (RetryingLLMClient) with corrective system message on LLMValidationError
  - Keyword-routed MockLLMClient (buy/sell/watchlist add/remove + default summary)
  - LLMValidationError subclass of LLMError for distinguishing Pydantic vs network failures
affects:
  - 04-frontend phase: frontend will hit /api/chat and receive real action outcomes
  - phase-03 UAT: end-to-end chat will exercise real trades via mock LLM

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "ExecutorRepos dataclass bundles all repos + price_cache + market_source for the executor — avoids parameter sprawl"
    - "MockLLMClient.complete_structured wraps Pydantic ValidationError as LLMValidationError (mirrors LLMClient) so the retry wrapper treats both clients uniformly"
    - "RetryingLLMClient wraps the inner client via lazy import in client.create_llm_client to avoid circular imports with retry.py"
    - "Per-action try/except inside execute_actions — internal errors are captured with status='failed' and detail='internal error: ...'"
    - "Inline snapshot insertion on every executor trade — keeps portfolio_snapshots consistent with manual /api/portfolio/trade"

key-files:
  created:
    - backend/app/llm/executor.py
    - backend/app/llm/mock.py
    - backend/app/llm/retry.py
    - backend/tests/llm/test_executor.py
    - backend/tests/llm/test_mock.py
    - backend/tests/llm/test_retry.py
  modified:
    - backend/app/llm/client.py
    - backend/app/llm/__init__.py
    - backend/app/api/chat.py
    - backend/tests/api/test_chat.py
    - backend/tests/llm/test_client.py

key-decisions:
  - "Use an ExecutorRepos dataclass to bundle dependencies instead of a long parameter list — keeps execute_actions easy to test and extend"
  - "Move MockLLMClient into its own module (app.llm.mock) and have client.py re-export it — preserves the import path Plan 03-01 callers depend on"
  - "Make MockLLMClient.complete_structured raise LLMValidationError on bad JSON — otherwise the retry wrapper would have to special-case MockLLMClient"
  - "Wrap create_llm_client output in RetryingLLMClient at the factory level — every caller automatically gets retry, no per-call wiring"
  - "One-shot retry with a corrective system message, no exponential backoff — limits API budget exposure (threat T-03-10)"
  - "Only LLMValidationError triggers retry; plain LLMError (network) propagates immediately — addresses threat T-03-DoS by retry budget"
  - "Per-action failures captured as TradeActionResult/WatchlistActionResult with status='failed' and a human-readable detail — chat_messages.actions JSON carries the failure detail for audit"

patterns-established:
  - "Pattern: Executor dataclass bundle — group all dependencies (repos + cache + source) into one object passed to execute_actions; the handler builds it from request-scoped Depends() providers"
  - "Pattern: Per-action partial failure — execute_actions wraps each trade/watchlist in try/except so a single bad action never aborts the batch"
  - "Pattern: Lazy retry wrapper import in factory — client.create_llm_client returns RetryingLLMClient(inner), with retry imported lazily to keep client.py free of cycles"
  - "Pattern: Keyword-routed mock for tests — MockLLMClient.complete uses regex to produce deterministic ChatResponse JSON from simple buy/sell/add/remove phrases, default summary for everything else"

requirements-completed:
  - LLM-05
  - LLM-06
  - LLM-07

coverage:
  - id: D1
    description: "execute_actions auto-applies trades via the same validation as /api/portfolio/trade (insufficient cash/shares fails per-action)"
    requirement: LLM-05
    verification:
      - kind: unit
        ref: backend/tests/llm/test_executor.py#test_executor_buy_success
        status: pass
      - kind: unit
        ref: backend/tests/llm/test_executor.py#test_executor_buy_insufficient_cash
        status: pass
      - kind: unit
        ref: backend/tests/llm/test_executor.py#test_executor_sell_without_position
        status: pass
      - kind: unit
        ref: backend/tests/llm/test_executor.py#test_executor_no_live_price
        status: pass
    human_judgment: false
  - id: D2
    description: "execute_actions auto-applies watchlist changes (add/remove) via the same validation as /api/watchlist"
    requirement: LLM-05
    verification:
      - kind: unit
        ref: backend/tests/llm/test_executor.py#test_executor_watchlist_add_success
        status: pass
      - kind: unit
        ref: backend/tests/llm/test_executor.py#test_executor_watchlist_remove_missing
        status: pass
    human_judgment: false
  - id: D3
    description: "Per-action failures are captured without aborting the batch (one bad trade does not block a subsequent watchlist add)"
    requirement: LLM-05
    verification:
      - kind: unit
        ref: backend/tests/llm/test_executor.py#test_executor_partial_failure_does_not_abort
        status: pass
      - kind: integration
        ref: backend/tests/api/test_chat.py#test_chat_per_action_failure_does_not_500
        status: pass
    human_judgment: false
  - id: D4
    description: "Malformed structured output triggers a one-shot retry with a corrective system message; second failure surfaces as 503"
    requirement: LLM-06
    verification:
      - kind: unit
        ref: backend/tests/llm/test_retry.py#test_retry_succeeds_on_second_attempt
        status: pass
      - kind: unit
        ref: backend/tests/llm/test_retry.py#test_retry_fails_after_two_validation_errors
        status: pass
      - kind: unit
        ref: backend/tests/llm/test_retry.py#test_retry_appends_corrective_message
        status: pass
      - kind: unit
        ref: backend/tests/llm/test_retry.py#test_retry_does_not_retry_on_network_error
        status: pass
      - kind: integration
        ref: backend/tests/api/test_chat.py#test_chat_retries_on_malformed_then_succeeds
        status: pass
      - kind: integration
        ref: backend/tests/api/test_chat.py#test_chat_returns_503_after_retry_exhaustion
        status: pass
    human_judgment: false
  - id: D5
    description: "LLMValidationError subclass of LLMError distinguishes Pydantic validation failures from network errors"
    requirement: LLM-06
    verification:
      - kind: unit
        ref: backend/tests/llm/test_retry.py#test_validation_error_subclass
        status: pass
    human_judgment: false
  - id: D6
    description: "MockLLMClient with deterministic keyword routing (buy/sell/watchlist add/remove + default summary) — no network calls"
    requirement: LLM-07
    verification:
      - kind: unit
        ref: backend/tests/llm/test_mock.py#test_mock_buy_keyword
        status: pass
      - kind: unit
        ref: backend/tests/llm/test_mock.py#test_mock_sell_keyword
        status: pass
      - kind: unit
        ref: backend/tests/llm/test_mock.py#test_mock_watchlist_add_keyword
        status: pass
      - kind: unit
        ref: backend/tests/llm/test_mock.py#test_mock_watchlist_remove_keyword
        status: pass
      - kind: unit
        ref: backend/tests/llm/test_mock.py#test_mock_default_response
        status: pass
      - kind: unit
        ref: backend/tests/llm/test_mock.py#test_mock_handles_lowercase_ticker
        status: pass
      - kind: unit
        ref: backend/tests/llm/test_mock.py#test_mock_parses_fractional_quantity
        status: pass
      - kind: unit
        ref: backend/tests/llm/test_mock.py#test_mock_no_user_message
        status: pass
    human_judgment: false
  - id: D7
    description: "Chat endpoint with LLM_MOCK=true end-to-end executes LLM-suggested trade and watchlist actions, persists assistant message with actions_executed JSON, returns 200 with per-action statuses"
    requirement: LLM-05
    verification:
      - kind: integration
        ref: backend/tests/api/test_chat.py#test_chat_executes_trade_with_mock
        status: pass
      - kind: integration
        ref: backend/tests/api/test_chat.py#test_chat_watchlist_add_with_mock
        status: pass
      - kind: integration
        ref: backend/tests/api/test_chat.py#test_chat_persists_actions_executed
        status: pass
    human_judgment: false

# Metrics
duration: 15min
completed: 2026-06-27
status: complete
---

# Phase 3 Plan 2: Executor + Retry Wrapper Summary

**Auto-executing LLM-suggested trades and watchlist changes via the same validation as the manual REST endpoints, plus one-shot retry on malformed structured output and keyword-routed MockLLMClient for tests**

## Performance

- **Duration:** 15 min (started 2026-06-27T13:04:26Z)
- **Tasks:** 2 (both auto/TDD)
- **Files modified:** 11

## Accomplishments

- Built the executor (`backend/app/llm/executor.py`) that re-applies the exact validation logic from `app/api/portfolio.py` and `app/api/watchlist.py` — buys validate cash via `to_cents`, sells validate share count, watchlist adds/remove go through the same `WatchlistRepository` paths. Per-action failures are captured in `TradeActionResult` / `WatchlistActionResult` with `status="failed"` and a human-readable detail; the batch never aborts.
- Built the keyword-routed `MockLLMClient` (`backend/app/llm/mock.py`) with regex matchers for `buy <qty> [shares of] <TICKER>`, `sell <qty> [shares of] <TICKER>`, `(add|watch) <TICKER>`, `(remove|drop) <TICKER>`, and a default summary fallback. Pure Python — no `litellm` import, no network calls.
- Built `RetryingLLMClient` (`backend/app/llm/retry.py`) that wraps an inner `LLMClient` and retries `complete_structured` exactly once on `LLMValidationError`, appending a corrective system message. Plain `LLMError` (network) is NOT retried — addresses threat T-03-DoS.
- Added `LLMValidationError` subclass of `LLMError` in `client.py`. `LLMClient.complete_structured` and `MockLLMClient.complete_structured` both wrap Pydantic `ValidationError` as `LLMValidationError` so the retry wrapper acts uniformly.
- Wired `create_llm_client()` to return a `RetryingLLMClient` wrapping either `MockLLMClient` or `LLMClient` — every chat call automatically gets retry behavior with no caller-side change.
- Wired `execute_actions` into `/api/chat`: the Plan 03-01 `ImportError` guard is gone, the handler constructs an `ExecutorRepos` from the request-scoped repos + price cache, calls `execute_actions`, persists `actions_executed` into `chat_messages.actions` JSON, and returns typed `ChatActionResult` objects.
- 28 new pytest cases pass (8 executor + 8 mock + 6 retry + 6 chat-end-to-end). Full backend suite: **194 tests pass** (was 166 in Plan 03-01, +28 new, no regressions).

## Task Commits

Each task was committed atomically:

1. **Task 1: Build executor and MockLLMClient with keyword routing** - `409c693` (feat)
2. **Task 2: Retry wrapper, LLMValidationError, wire executor into /api/chat** - `c2a7ed3` (feat)

## Files Created/Modified

### Created
- `backend/app/llm/executor.py` - `execute_actions`, `ExecutorRepos`, `ExecutionResult`, `TradeActionResult`, `WatchlistActionResult`; per-action error capture; inline snapshot on every trade
- `backend/app/llm/mock.py` - `MockLLMClient` with regex-based keyword routing for buy/sell/watchlist add/remove + default summary
- `backend/app/llm/retry.py` - `RetryingLLMClient`, `CORRECTIVE_SYSTEM_MESSAGE`, `retry_structured_completion` helper
- `backend/tests/llm/test_executor.py` - 8 tests (buy success, insufficient cash, sell no position, watchlist add, watchlist remove missing, partial failure, no live price, to_list)
- `backend/tests/llm/test_mock.py` - 8 tests (buy/sell/watchlist add/remove, default, lowercase ticker, no user message, fractional quantity)
- `backend/tests/llm/test_retry.py` - 6 tests (subclass, retry success, retry failure, no retry on network error, corrective message appended, module helper)

### Modified
- `backend/app/llm/client.py` - Added `LLMValidationError`; `LLMClient.complete_structured` raises `LLMValidationError`; `create_llm_client` now returns `RetryingLLMClient`; `MockLLMClient` re-exported from `mock.py`
- `backend/app/llm/__init__.py` - Added public exports: `LLMValidationError`, `RetryingLLMClient`, `CORRECTIVE_SYSTEM_MESSAGE`, `retry_structured_completion`, `execute_actions`, `ExecutionResult`, `ExecutorRepos`, `TradeActionResult`, `WatchlistActionResult`
- `backend/app/api/chat.py` - Replaced Plan 03-01 `ImportError` guard with direct `execute_actions` + `ExecutorRepos` wiring; added `snapshot_repo` dependency; removed `try/except ImportError` block
- `backend/tests/api/test_chat.py` - Updated 4 existing tests for the new mock message format ("Mock portfolio summary for: ..." vs old "Mock response to: ..."); added 6 new tests (executor end-to-end trade, watchlist add end-to-end, per-action failure does not 500, actions_executed persisted, retry succeeds, retry exhausted → 503)
- `backend/tests/llm/test_client.py` - Updated 4 tests for the new `RetryingLLMClient`-wrapped factory output and the new keyword-routed mock default response

## Decisions Made

- **ExecutorRepos dataclass bundles all dependencies.** A long parameter list for `execute_actions` would have been ugly to test and extend. The dataclass is built once per request inside the chat handler from the request-scoped `Depends()` providers.
- **MockLLMClient moved to its own module.** Plan 03-01 had a stub class in `client.py`; the full implementation moved to `mock.py`. `client.py` re-exports it to preserve the import path callers depend on (`from app.llm import MockLLMClient`).
- **MockLLMClient.complete_structured wraps `ValidationError` as `LLMValidationError`.** Otherwise the retry wrapper would have to special-case the mock client. Now both clients raise the same exception, so the retry logic is identical.
- **`RetryingLLMClient` wrapped at the factory level.** No per-call wiring — every chat call automatically gets the one-shot retry. Lazy import inside `create_llm_client` keeps `client.py` and `retry.py` free of circular imports.
- **No exponential backoff, no retry on plain `LLMError`.** Network errors are propagated unchanged; only `LLMValidationError` triggers the one-shot retry. This addresses threat T-03-DoS (burning API budget on retry storms).
- **Inline snapshot on every executor trade.** Matches the manual `/api/portfolio/trade` behavior so the P&L chart stays accurate after auto-executed trades.
- **Per-action failures captured with `status="failed"` + detail.** The chat response carries the failure detail inline; `chat_messages.actions` JSON persists the same. The user always sees what happened.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 2 - Missing Critical] MockLLMClient.complete_structured now wraps Pydantic ValidationError as LLMValidationError**
- **Found during:** Task 2 (running test_chat_retries_on_malformed_then_succeeds)
- **Issue:** The Plan 03-01 stub MockLLMClient.complete_structured called `model_validate_json` directly without wrapping ValidationError. With the new retry wrapper in place, a bad-JSON mock response would raise raw `pydantic.ValidationError` instead of `LLMValidationError`, and `RetryingLLMClient` would not catch it (it only catches `LLMValidationError`). This was a correctness requirement for LLM-06.
- **Fix:** Mirrored the `LLMClient.complete_structured` behavior in `mock.py` — wrap `ValidationError` as `LLMValidationError` so the retry wrapper treats both clients uniformly.
- **Files modified:** `backend/app/llm/mock.py`
- **Verification:** `tests/llm/test_retry.py` and `tests/api/test_chat.py::test_chat_retries_on_malformed_then_succeeds` / `test_chat_returns_503_after_retry_exhaustion` all pass.
- **Committed in:** `c2a7ed3` (Task 2 commit)

**2. [Rule 1 - Bug] test_client.py factory assertions updated for the new RetryingLLMClient wrapper**
- **Found during:** Task 2 (running test_client.py after the factory change)
- **Issue:** The old tests asserted `create_llm_client()` returns a `MockLLMClient` or `LLMClient` directly. After wrapping in `RetryingLLMClient`, the top-level type changed. The behavior is identical — the inner client is still mock or real — but the assertions needed to inspect `client._inner`.
- **Fix:** Updated assertions to `isinstance(client, RetryingLLMClient)` and `isinstance(client._inner, MockLLMClient)` / `LLMClient` as appropriate.
- **Files modified:** `backend/tests/llm/test_client.py`
- **Verification:** All 9 test_client.py cases pass.
- **Committed in:** `c2a7ed3` (Task 2 commit)

**3. [Rule 1 - Bug] test_chat.py / test_client.py mock message assertions updated for the new keyword-routed format**
- **Found during:** Task 2 (running tests after the mock format change)
- **Issue:** The Plan 03-01 mock returned `"Mock response to: <msg>"`. The Plan 03-02 keyword-routed mock returns `"Mock portfolio summary for: <msg>"` (and `"Mock buy N TICKER"` etc. for matched keywords). The existing tests assumed the old format.
- **Fix:** Updated 4 existing assertions in `test_chat.py` and 2 in `test_client.py` to use `"Mock portfolio summary"` substring instead of `"Mock response to:"`.
- **Files modified:** `backend/tests/api/test_chat.py`, `backend/tests/llm/test_client.py`
- **Verification:** All updated tests pass; behavior unchanged (the tests verify the mock returned something matching the expected format, not the exact wording).
- **Committed in:** `c2a7ed3` (Task 2 commit)

---

**Total deviations:** 3 auto-fixed (1 missing critical, 2 bug fixes from behavior changes)
**Impact on plan:** All auto-fixes necessary for correctness or to match the new mock format. No scope creep.

## Issues Encountered

- Initial test run after Task 2 surfaced 6 failing tests in `test_client.py` and `test_chat.py` because the mock message format and factory wrapper changed. Resolved by updating assertions (documented as deviations Rule 1).
- Initial test run for the retry chat tests surfaced a `pydantic.ValidationError` instead of `LLMValidationError` because `MockLLMClient.complete_structured` did not wrap the validation error. Resolved by mirroring `LLMClient.complete_structured` behavior in `mock.py` (documented as deviation Rule 2).
- Ruff auto-fix applied 20 trailing-newline + import-cleanup issues across the new files; cosmetic only.

## User Setup Required

None - no external service configuration required. The retry wrapper activates automatically when `create_llm_client()` is called, regardless of `LLM_MOCK` setting. Tests run with `LLM_MOCK=true`; production deployments omit it and the same retry semantics apply to the real OpenRouter/Cerebras route.

## Threat Mitigations Applied

| Threat ID | Disposition | How this plan mitigates |
|-----------|-------------|-------------------------|
| T-03-07 | mitigate | Executor re-runs the SAME validation as `/api/portfolio/trade` (cash cents comparison, share count check). No new validation path. Failed trades return `status="failed"`, not a write. |
| T-03-08 | mitigate | `_execute_one_watchlist_change` delegates to `WatchlistRepository.add/remove/exists` which uppercases and normalizes; `WatchlistChange` schema validates ticker via Pydantic. No raw ticker passes through to DB. |
| T-03-09 | mitigate | Every executor action (success OR failure) is appended to `result.actions` and persisted to `chat_messages.actions` JSON. The user sees the failure detail inline. No silent drops. |
| T-03-10 | mitigate | Retry is ONE shot. No exponential backoff, no retry on network errors — only on `LLMValidationError`. `RetryingLLMClient.complete_structured` cannot loop indefinitely. |
| T-03-11 | mitigate | `MockLLMClient` does not import `litellm`. Its `complete` method is a pure-Python regex path. `test_create_returns_mock_when_env_true` proves the factory returns `RetryingLLMClient` wrapping a `MockLLMClient` inner without any network call. |
| T-03-12 | mitigate | `_execute_one_watchlist_change` wraps `market_source.add_ticker` / `remove_ticker` in try/except + logger.warning. A failing MarketDataSource does NOT prevent the DB write from completing. |

## Next Phase Readiness

- Phase 03 is now complete: the executor + retry + mock + chat wiring delivers the fully agentic chat experience described in PLAN.md section 9. The AI can move money, manage the watchlist, and recover from its own bad JSON.
- Phase 04 (Frontend) can POST to `/api/chat` with `LLM_MOCK=true` for development and rendering work, then flip to `LLM_MOCK=false` (default) for production. The response shape is stable: `message`, `trades`, `watchlist_changes`, `actions_executed` (each with `type`, `ticker`, `status`, `detail`, plus `side`/`quantity` for trades and `action` for watchlist).
- E2E test phase can mock the chat endpoint or run with `LLM_MOCK=true` for deterministic trade-execution assertions.
- Backend test suite is healthy: 194 tests pass, ruff is clean.

## Self-Check: PASSED

- Files created (executor, mock, retry + tests): all 6 confirmed on disk.
- Commits verified: `409c693` (Task 1) and `c2a7ed3` (Task 2) exist in `git log`.
- 28 new pytest cases pass; full backend suite (194 tests) passes; ruff clean on the modified paths.

---
*Phase: 03-llm-integration*
*Completed: 2026-06-27*