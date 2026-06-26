# Market Data Backend Code Review

Review date: 2026-06-26
Branch: `codex/marketdata-review-fixes`
Scope: `backend/app/market`, `backend/tests/market`, and market-data readiness notes in `planning/MARKET_DATA_SUMMARY.md`.

## Findings

1. **Medium: Explicit Unix timestamp `0.0` is silently replaced with wall-clock time.**  
   `backend/app/market/cache.py:23-38` accepts an optional timestamp, but line 30 uses `timestamp or time.time()`. That treats any falsey timestamp as missing, including `0.0`. The current Massive client passes exchange timestamps through this path, so a valid epoch timestamp would be mutated instead of preserved. The cache should distinguish `None` from a valid numeric timestamp.

2. **Medium: Simulator ticker handling is not normalized while Massive ticker handling is.**  
   `backend/app/market/massive_client.py:54-85` normalizes tickers to uppercase and strips whitespace, but `backend/app/market/simulator.py:67-69`, `backend/app/market/simulator.py:120-134`, and `backend/app/market/simulator.py:219-255` use input strings as-is. That means `"aapl"` and `" AAPL "` become unknown simulator tickers with random seed prices, wrong correlation grouping, and cache keys that differ from the Massive source. The simulator path is the default no-key backend, so downstream watchlist and trading code can see inconsistent behavior depending on whether `MASSIVE_API_KEY` is set.

3. **Medium: `start()` can be called twice and leak an active background task.**  
   `backend/app/market/simulator.py:219-230` and `backend/app/market/massive_client.py:47-59` create a new task every time `start()` is called. A second call overwrites `_task`, making the first loop unreachable for cancellation through `stop()`. The interface says double start is undefined, but backend app lifespan hooks and tests are easier to reason about if the data source fails fast instead of leaving duplicate pollers running.

4. **Low: Pytest configuration emits a deprecation warning on every async test.**  
   `backend/tests/conftest.py:5-10` overrides `event_loop_policy`, and the installed `pytest-asyncio` reports that fixture override as deprecated. The suite still passes, but the warning is repeated 79 times and will eventually become a maintenance issue. Removing the redundant default policy fixture should keep the suite quiet.

## Verification

Baseline checks were run from a local ignored virtual environment because `uv` was not available in PATH in this shell:

- `backend/.venv/bin/ruff check .` passed.
- `backend/.venv/bin/pytest -q` passed: 79 tests.
- `backend/.venv/bin/pytest --cov=app --cov-report=term-missing -q` passed: 79 tests, 96% total coverage.

The installed `massive` package was also inspected locally. `RESTClient.get_snapshot_all(market_type=..., tickers=...)` and `SnapshotMarketType.STOCKS` match the current client code, so the real-data API call shape is compatible with the pinned dependency environment.

## Recommended Fixes

1. Replace `timestamp or time.time()` with an explicit `timestamp is None` check and add coverage for `timestamp=0.0`.
2. Add one shared ticker-normalization helper for market data sources, apply it to simulator initialization, add/remove/get paths, and cover lowercase/whitespace inputs in tests.
3. Guard both data source `start()` implementations so a second active start raises a clear `RuntimeError`, with tests proving no duplicate loop is created.
4. Remove the deprecated `event_loop_policy` fixture and rerun the suite to confirm warnings are gone.

