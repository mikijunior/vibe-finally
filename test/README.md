# FinAlly E2E Tests

Playwright tests covering the critical user flows: watchlist CRUD, trade
execution, portfolio display, AI chat (with `LLM_MOCK=true`), and SSE
reconnection.

## Running locally

Build the app image and run the suite against a fresh container:

```bash
docker compose -f test/docker-compose.test.yml up --abort-on-container-exit --exit-code-from playwright
```

The `playwright` service uses `mcr.microsoft.com/playwright:v1.49.0-jammy`,
which has Chromium preinstalled. The app service runs with `LLM_MOCK=true`
and `TESTING=1`, so tests are deterministic and don't require an
`OPENROUTER_API_KEY`.

## What's tested

| Spec | What it verifies |
|------|------------------|
| `watchlist.spec.ts` | 10 default tickers render; prices change over time; inline add/remove works |
| `trade.spec.ts` | Buy reduces cash + opens position; sell closes position; insufficient cash surfaces inline error |
| `portfolio.spec.ts` | Heatmap renders colored rectangles after a position; P&L chart canvas paints |
| `chat.spec.ts` | Mocked LLM response renders assistant message + inline trade chip |
| `sse-resilience.spec.ts` | Status dot reflects EventSource readyState; route abort flips it to a non-connected state |

## Fixtures

`e2e/fixtures.ts` exports an extended `test` with:

- `api` — an `APIRequestContext` against `baseURL`
- `resetWatchlist` — auto-fixture that resets the watchlist to the 10
  default tickers before each test (uses backend `TESTING=1` endpoints)

## CI

`.github/workflows/e2e.yml` runs the same `docker compose` invocation on
every PR and push to `main`. The Playwright HTML report is uploaded as an
artifact on failure.

## Notes

- The Playwright container does NOT download browsers at runtime — the
  image is pre-baked with Chromium so the suite starts fast.
- The `TESTING=1` env var unlocks `GET /cache/state`, `POST
  /watchlist/test-add/{ticker}`, and `POST /watchlist/test-remove/{ticker}`
  in `backend/app/main.py`. These endpoints are guarded and only respond
  when the env var is set — they let tests reset state without touching
  the SQLite file directly.
- Run `npm install` inside `test/` only if you're iterating on the
  specs outside Docker; the Playwright Docker image has its own
  `@playwright/test` install.
