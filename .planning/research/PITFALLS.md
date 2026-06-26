# Pitfalls Research

**Domain:** AI-Powered Trading Workstation
**Researched:** 2026-06-26
**Confidence:** HIGH

## Critical Pitfalls

### Pitfall 1: Next.js Static Export Incompatibility with API Routes

**What goes wrong:**
With `output: 'export'`, Next.js produces static HTML files only. API Routes (`app/api/*` route handlers) are **not executed** -- they are simply ignored. FastAPI serves the static export from a `/` path prefix, but API calls to `/api/*` return 404 or are never handled.

**Why it happens:**
The PLAN.md specifies Next.js static export AND FastAPI serving API routes on the same port. Static export fundamentally cannot run server-side code. The architecture assumes API routes live in FastAPI, but the Next.js frontend cannot make API calls to a different origin without CORS -- and the PLAN explicitly says "no CORS configuration needed."

**How to avoid:**
- Use Next.js **Pages Router** (not App Router) for this project. Pages Router with static export can still function if all API logic lives in FastAPI and the frontend makes fetch calls to the FastAPI server at the same origin.
- Alternatively, do NOT use `output: 'export'` -- use Next.js standalone output with FastAPI serving it.
- The frontend must be built knowing FastAPI serves everything at port 8000, and Next.js pages are static HTML shells that fetch from `/api/*` (FastAPI) and `/api/stream/*` (SSE).

**Warning signs:**
- `npm run build` produces `.html` files and no `_next/server/pages/api/` directory
- API calls return 404
- `{"detail":"Not Found"}` from FastAPI for POST requests

**Phase to address:** Frontend Infrastructure phase -- must resolve before any API integration work begins.

---

### Pitfall 2: SSE Connection Limit and Memory Leaks

**What goes wrong:**
SSE connections are long-lived. If the server does not properly detect client disconnects, each reconnection attempt leaves a dangling async generator. At scale (or even with a few tab reloads), this exhausts server file descriptors and memory. Additionally, browsers limit SSE connections to **6 per domain** (HTTP/1.1) -- multiple tabs or concurrent connections hit this ceiling.

**Why it happens:**
FastAPI's SSE generator holds onto resources (database connections, cache references) until the client disconnects. The `connection_aborted()` check is required but easy to skip. Without it, generators become orphaned.

**How to avoid:**
- In the SSE endpoint, periodically check `await request.is_disconnected()` or use a connection_aborted guard.
- Send keep-alive comment lines (`: keep-alive\n\n`) every 15-30 seconds to prevent proxy timeout.
- Set proper SSE headers: `X-Accel-Buffering: no`, `Cache-Control: no-cache`, `Content-Type: text/event-stream`.
- For production: ensure HTTP/2 is used so the 6-connection limit is raised to 100.

**Warning signs:**
- Server memory grows monotonically over hours
- `ulimit` errors in container logs
- Client sees "Connection closed" after period of inactivity
- SSE events stop arriving but EventSource shows "connected"

**Phase to address:** Backend SSE Streaming phase -- requires integration testing with actual disconnects.

---

### Pitfall 3: SQLite Write Serialization Blocking SSE

**What goes wrong:**
SQLite allows many simultaneous readers but only **one writer at a time**. If a trade execution or chat message insert holds a write lock, the price SSE stream continues unaffected (reads are fine), but any subsequent write (another trade, chat insert) blocks until the first write completes. With background portfolio snapshot writes every 30 seconds, occasional write contention is possible.

**Why it happens:**
The SQLite database is accessed from multiple contexts: the SSE background task writing price updates to cache (not DB), the trade execution endpoint (DB write), chat insert (DB write), and portfolio snapshot task (DB write every 30s). While reads don't block, writes queue serially.

**How to avoid:**
- Use SQLite's **WAL mode** (`PRAGMA journal_mode=WAL`) -- allows concurrent reads with a single writer without blocking reads.
- Keep transactions short. Open, write, close -- do not hold DB connections across awaits.
- For the portfolio snapshot task: skip if previous snapshot is within 25 seconds (avoid overlap).
- The `PriceCache` in-memory store is already thread-safe and separate from SQLite -- verify this boundary is respected.

**Warning signs:**
- API response times spike during portfolio snapshot writes
- Chat endpoint delays correlated with snapshot timing
- `database is locked` errors in logs

**Phase to address:** Backend Database Integration phase -- should be verified with concurrent load tests.

---

### Pitfall 4: LLM Structured Output Parsing Failures

**What goes wrong:**
The LLM returns malformed JSON (missing quotes, unclosed brackets, wrong types), the structured output schema validation fails, and the entire chat request returns a 500 to the frontend. The user sees a generic error instead of a graceful fallback.

**Why it happens:**
LLM outputs are probabilistic. Even with structured output constraints, the model can occasionally produce invalid JSON. LiteLLM's schema validation may raise exceptions instead of returning a parsed result. Network timeouts, rate limits, or OpenRouter service issues also cause complete failure.

**How to avoid:**
- Wrap the LiteLLM call in a try-catch that handles: `JSONDecodeError`, `ValidationError`, `RateLimitError`, `TimeoutError`, and generic `Exception`.
- On parse failure: retry once with a simpler prompt (no structured schema, just ask for JSON), then fall back to returning `{"message": "Sorry, I couldn't process that. Please try again.", "trades": [], "watchlist_changes": []}`.
- Use LiteLLM's `max_retries` parameter (set to 2).
- Log the raw LLM response on failure for debugging.
- Ensure `LLM_MOCK=true` path is fully functional as an escape hatch.

**Warning signs:**
- 500 errors from `POST /api/chat`
- `ValidationError` or `JSONDecodeError` in backend logs
- Frontend chat panel shows "Error" state indefinitely

**Phase to address:** Backend LLM Integration phase -- must include malformed response test cases.

---

### Pitfall 5: Price Simulator Drift and Bounds Violation

**What goes wrong:**
The GBM simulator runs continuously. Over hours or days, prices can drift to implausibly high values (AAPL at $50,000) or near-zero values, breaking visual charts and confusing users. Random shock events compound this.

**Why it happens:**
Geometric Brownian Motion has no mean reversion. The simulator starts from realistic prices but accumulates drift over many ticks. With 500ms updates, that's 172,800 price changes per day per ticker.

**How to avoid:**
- Implement **price bounds**: clamp prices to ±50% of the seed price (or a configurable range). If a tick would exceed bounds, snap to the boundary and optionally reverse direction.
- Track "events" that cause sudden moves separately from normal GBM ticks.
- Consider a mean-reverting variant (Ornstein-Uhlenbeck process) for the drift component.
- Document the behavior: "simulated prices may diverge from real market prices over time."

**Warning signs:**
- Ticker prices exceed 2x or fall below 0.5x the realistic seed price
- User sees "AAPL: $47,230.50" in watchlist
- Charts become unusable due to scale

**Phase to address:** Market Data Simulator phase (already complete per MARKET_DATA_SUMMARY.md, but needs bounds validation).

---

### Pitfall 6: Frontend SSE Reconnection Storm

**What goes wrong:**
When the SSE connection drops (network glitch, server restart), all connected browser tabs simultaneously attempt to reconnect. Each tab sends multiple reconnection attempts with exponential backoff. This creates a thundering herd that overwhelms the server.

**Why it happens:**
`EventSource` automatically reconnects, and browsers aggressively retry. With 3 tabs open, 3 simultaneous reconnection storms hit the server.

**How to avoid:**
- Add a random jitter (0-2 seconds) to reconnection attempts in the frontend before calling `new EventSource()`.
- Track connection state in React state and show a "Reconnecting..." indicator (the yellow dot).
- Debounce reconnection: if disconnected, wait before reconnecting rather than immediate retry.
- Limit reconnection attempts: after 5 failures, stop and show "Connection lost. Refresh page."

**Warning signs:**
- Server logs show SSE connection bursts after a server restart
- CPU spike correlated with client reconnection
- Multiple `GET /api/stream/prices` with identical timestamps

**Phase to address:** Frontend SSE Integration phase -- implement before any demo or user testing.

---

### Pitfall 7: Portfolio Snapshot Data Growth

**What goes wrong:**
Portfolio snapshots are written every 30 seconds. After 24 hours: 2,880 rows. After 30 days: 86,400 rows. Reading `/api/portfolio/history` returns thousands of rows, causing slow API responses and large payload sizes.

**Why it happens:**
No cleanup strategy. The `portfolio_snapshots` table grows indefinitely.

**How to avoid:**
- Implement a **cleanup task**: delete snapshots older than 7 days on container startup and daily.
- Alternatively, use a rolling window: keep only the last N snapshots (e.g., 1,000 = ~8 hours at 30s intervals).
- Add a database index on `recorded_at` for fast range queries.

**Warning signs:**
- `SELECT * FROM portfolio_snapshots ORDER BY recorded_at DESC LIMIT 100` returns thousands of rows
- API response size > 1MB for portfolio history
- Slow chart rendering due to data volume

**Phase to address:** Backend Database Integration phase -- should be verified with data growth over time.

---

### Pitfall 8: Fractional Share Precision Errors

**What goes wrong:**
A user buys 0.1 share of AAPL at $190. avg_cost = $190. Later they sell 0.05 shares. The fractional arithmetic produces $9.499999999 instead of $9.50, leading to penny discrepancies in cash balance that accumulate.

**Why it happens:**
IEEE 754 floating point is inexact for decimal values. `0.1 + 0.2 != 0.3` in floating point.

**How to avoid:**
- Store all quantities and prices as **integers representing cents** (e.g., $190.00 stored as 19000 cents).
- For display, convert back to dollars with 2 decimal places.
- In Python: use `Decimal` from the `decimal` module for all financial calculations.
- In SQLite: store as `INTEGER` (cents) not `REAL`.

**Warning signs:**
- Cash balance shows "$9,999.999999996"
- Position unrealized P&L shows "-$0.0000004"
- Trade validation fails due to penny discrepancies

**Phase to address:** Portfolio Logic phase -- all financial calculations must use Decimal.

---

### Pitfall 9: uv Project Not Building in Docker Multi-Stage

**What goes wrong:**
`uv sync` in the Docker build fails because `uv` is not installed in the Python stage, or because the lockfile was generated on a different platform (macOS ARM vs Linux x86), causing platform-specific dependency resolution failures.

**Why it happens:**
The Dockerfile copies `backend/pyproject.toml` and `backend/uv.lock` but does not install `uv` before running `uv sync`. Alternatively, the lockfile contains platform-specific wheels that fail on the slim Python image.

**How to avoid:**
- Install `uv` via `pip install uv` in the Dockerfile before `uv sync`.
- Use `uv sync --no-editable` for cleaner installation in containers.
- Ensure `uv.lock` is platform-agnostic or regenerate it inside the container.
- Test the Docker build locally before calling it done.

**Warning signs:**
- `uv: command not found` in Docker build logs
- `-wheel`s failing to install in container
- `pyproject.toml` changes but `uv.lock` is out of sync

**Phase to address:** Docker Infrastructure phase -- must verify with actual Docker build.

---

### Pitfall 10: Chat History Growth Causes LLM Context Overflow

**What goes wrong:**
After extended use, `chat_messages` table grows to hundreds of messages. The LLM prompt includes the entire conversation history plus portfolio context, exceeding the model's context window and causing truncated responses or errors.

**Why it happens:**
The chat endpoint loads all messages from `chat_messages` table and sends them all to the LLM. No sliding window or token limit enforcement.

**How to avoid:**
- Load only the **last N messages** (e.g., last 20) plus a summary of older messages ("Earlier, you suggested buying AAPL...").
- Include a token count estimate before sending to LLM; truncate if approaching limit.
- Alternatively, store only the last 50 messages and archive older ones.

**Warning signs:**
- LLM responses become truncated or nonsensical
- `context_length_exceeded` errors from LiteLLM
- Chat performance degrades over time

**Phase to address:** Backend LLM Integration phase -- implement message windowing.

---

## Technical Debt Patterns

| Shortcut | Immediate Benefit | Long-term Cost | When Acceptable |
|----------|-------------------|----------------|-----------------|
| Skip WAL mode on SQLite | Simpler setup | Write blocking, possible deadlocks under load | Never for this project |
| Use `REAL` for monetary values | Simpler schema | Floating point rounding errors | Never -- use INTEGER cents or Decimal |
| No retry on LLM calls | Simpler code | Silent failures, broken chat | Never -- must retry at least once |
| Skip keep-alive in SSE | Simpler streaming code | Connection timeouts after 60s | Never |
| No portfolio snapshot cleanup | Simpler database code | Data growth, slow queries | Only in MVP, cleanup before release |
| Skip connection state in frontend | Less code | Poor UX on disconnect | Never |

---

## Integration Gotchas

| Integration | Common Mistake | Correct Approach |
|-------------|----------------|-----------------|
| **FastAPI + Next.js Static** | Expecting API routes to work | All API logic in FastAPI; Next.js only fetches from FastAPI at same origin |
| **EventSource** | Not handling `onerror` properly | Always implement `onerror` handler with reconnection logic |
| **LiteLLM structured output** | Not catching validation errors | Wrap in try-catch, retry once, return graceful fallback |
| **SQLite in Docker** | Volume mount path mismatch | Container writes to `/app/db`, host maps to `db/` -- must match start script |
| **Price cache** | Reading stale prices in REST while SSE writes | PriceCache is single source of truth for live prices; REST reads from cache |

---

## Performance Traps

| Trap | Symptoms | Prevention | When It Breaks |
|------|----------|------------|----------------|
| **SSE without keep-alive** | Connection closes after proxy timeout (usually 60s) | Send `:\n\n` comment every 30s | Behind nginx, Cloudflare, or any proxy |
| **Unbounded chat history** | LLM context overflow, slow prompt construction | Load only last N messages with token budget | After ~100 messages |
| **Unbounded snapshot table** | Slow `/api/portfolio/history` | Rolling window or daily cleanup | After 7+ days of use |
| **Many concurrent SSE watchers** | File descriptor exhaustion | Limit SSE connections per IP, HTTP/2 | At 100+ simultaneous connections |
| **Static export + many pages** | Long build times | Incremental builds, output tracing config | With 50+ pages |

---

## Security Mistakes

| Mistake | Risk | Prevention |
|---------|------|------------|
| **No input validation on ticker symbols** | XSS if ticker rendered unsanitized in DOM | Validate ticker is uppercase alphanumeric, max 5 chars |
| **No rate limiting on trade endpoint** | Accidental or intentional rapid-fire trading | Add a rate limit: max 10 trades per minute per IP |
| **LLM prompt injection** | User crafts message that manipulates AI into unauthorized actions | Validate ticker symbols server-side before execution; never trust LLM's ticker list alone |
| **OPENROUTER_API_KEY in Docker image** | Key visible in container layers | Use `--env-file .env` at runtime, not baked into image |

---

## UX Pitfalls

| Pitfall | User Impact | Better Approach |
|---------|-------------|-----------------|
| **No connection status indicator** | User doesn't know if prices are live | Show colored dot: green=connected, yellow=reconnecting, red=disconnected |
| **Trade confirmation dialog** | Breaks the "instant fill" demo experience | No dialog -- execute immediately, show confirmation toast |
| **Silent trade failures** | User doesn't know buy/sell didn't happen | Show inline error: "Could not complete: insufficient cash" |
| **SSE data loss on reconnect** | Gaps in sparkline charts | Accumulate price data client-side; reconnect resumes from latest |
| **No loading state on chat** | User doesn't know if AI is thinking | Show typing indicator while awaiting response |

---

## "Looks Done But Isn't" Checklist

- [ ] **SSE streaming:** Endpoint returns 200 but no events arrive client-side -- verify EventSource `onmessage` fires
- [ ] **Trade execution:** Buy button updates UI optimistically but API returns 400 -- verify position actually appears after refresh
- [ ] **LLM chat:** Mock mode returns hardcoded response -- verify structured output schema matches real LLM output
- [ ] **Docker volume:** Database file created but not visible on host -- verify volume mount path matches `db/` directory
- [ ] **Price flash animation:** CSS transition defined but never triggers -- verify direction prop changes and class is applied
- [ ] **Portfolio heatmap:** Treemap renders but all rectangles same size -- verify size calculation uses position value, not fixed size
- [ ] **Sparklines:** Canvas draws but data resets on reconnect -- verify client accumulates price history across SSE reconnections

---

## Recovery Strategies

| Pitfall | Recovery Cost | Recovery Steps |
|---------|---------------|----------------|
| SSE memory leak | MEDIUM | Restart container; fix disconnect detection; add connection limit |
| SQLite write lock timeout | LOW | Enable WAL mode; shorten transactions; retry with backoff |
| LLM parse failure | LOW | Graceful fallback response; log raw output; retry once |
| Price drift far from seed | LOW | Restart simulator with fresh seed prices; add bounds checking |
| Snapshot table growth | LOW | Run DELETE FROM portfolio_snapshots WHERE recorded_at < datetime('now', '-7 days') |

---

## Pitfall-to-Phase Mapping

| Pitfall | Prevention Phase | Verification |
|---------|------------------|--------------|
| Static export / API routes | Frontend Infrastructure | Build frontend, verify API calls to FastAPI succeed |
| SSE connection leaks | Backend SSE Streaming | Run SSE for 1 hour, check memory stable, verify disconnect detection |
| SQLite write serialization | Backend Database Integration | Concurrent trade + chat requests, verify no blocking |
| LLM parse failures | Backend LLM Integration | Send 50 malformed prompt variations, verify graceful handling |
| Price drift | Market Data Simulator | Let simulator run 24h, verify prices within bounds |
| SSE reconnection storm | Frontend SSE Integration | Simulate network disconnect, observe server logs |
| Snapshot data growth | Backend Database Integration | Insert 10k snapshots, query performance acceptable |
| Fractional share precision | Portfolio Logic | Buy 0.1, sell 0.05, verify exact $9.50 cash change |
| uv Docker build | Docker Infrastructure | Run `docker build`, verify no errors |
| Chat history overflow | Backend LLM Integration | Insert 500 chat messages, verify prompt still under limit |

---

## Sources

- [SQLite Whentouse](https://www.sqlite.org/whentouse.html) -- concurrency model, network filesystem warnings
- [MDN Server-Sent Events](https://developer.mozilla.org/en-US/docs/Web/API/Server-sent_events/Using_server-sent_events) -- connection limits (6 per domain), reconnection behavior
- [Next.js Static Export](https://nextjs.org/docs/app/guides/static-export) -- API routes not supported in static export
- [SQLite AUTOINCREMENT](https://www.sqlite.org/autoinc.html) -- performance overhead, rowid behavior
- [LiteLLM Structured Output](https://docs.litellm.ai/docs/structured_output_troubleshooting) -- validation errors, stop sequences causing failures
- [FastAPI SSE Patterns](https://fastapi.tiangolo.com/advanced/using-sse/) -- connection abort detection, keep-alive comments

---
*Pitfalls research for: AI-Powered Trading Workstation*
*Researched: 2026-06-26*
