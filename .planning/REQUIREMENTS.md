# Requirements: FinAlly — AI Trading Workstation

**Defined:** 2026-06-26
**Core Value:** A single-container, zero-setup trading platform where AI agents collaborate to build a professional-grade trading workstation.

## v1 Requirements

### Backend — Database

- [ ] **DB-01**: SQLite database initialized lazily on first request (creates tables if missing, seeds default data)
- [ ] **DB-02**: SQLite running in WAL mode for concurrent read/write safety
- [ ] **DB-03**: All monetary values stored as INTEGER cents (no floating-point REAL for money)
- [ ] **DB-04**: Tables: users_profile, watchlist, positions, trades, portfolio_snapshots, chat_messages

### Backend — Market Data (Simulator)

- [x] **MKT-01**: Geometric Brownian motion price generation with configurable drift/volatility per ticker
- [x] **MKT-02**: Correlated price moves across tickers (sector groupings)
- [x] **MKT-03**: Random "event" spikes (2-5% sudden moves) at low frequency
- [x] **MKT-04**: Price updates at ~500ms intervals
- [x] **MKT-05**: Realistic seed prices per ticker (AAPL ~$190, GOOGL ~$175, etc.)
- [ ] **MKT-06**: Abstract MarketDataSource interface — simulator and Massive API both implement it
- [ ] **MKT-07**: Thread-safe in-memory PriceCache shared by all endpoints

### Backend — Market Data (Massive API)

- [x] **MAP-01**: REST polling client for Massive (Polygon.io) API when MASSIVE_API_KEY is set
- [x] **MAP-02**: Falls back to simulator when MASSIVE_API_KEY is absent or empty
- [x] **MAP-03**: Same PriceCache interface as simulator — downstream code is agnostic to source

### Backend — REST API

- [ ] **API-01**: GET /api/portfolio — returns cash balance, positions with P&L, total portfolio value
- [ ] **API-02**: POST /api/portfolio/trade — executes market order: {ticker, quantity, side}, validates sufficient cash/shares, returns trade result
- [ ] **API-03**: GET /api/portfolio/history — returns portfolio snapshots for P&L chart
- [ ] **API-04**: GET /api/watchlist — returns current watchlist tickers with latest prices
- [ ] **API-05**: POST /api/watchlist — adds ticker: {ticker}, validates ticker format
- [ ] **API-06**: DELETE /api/watchlist/{ticker} — removes ticker from watchlist
- [ ] **API-07**: POST /api/chat — receives {message}, loads portfolio context + chat history, calls LLM with structured output, auto-executes trades, stores message + actions, returns {message, actions}
- [ ] **API-08**: GET /api/health — returns health check status

### Backend — SSE Streaming

- [ ] **SSE-01**: GET /api/stream/prices — SSE stream, pushes all watched tickers' prices every ~500ms
- [ ] **SSE-02**: Each event contains: ticker, price, previous_price, timestamp, direction (up/down/unchanged)
- [ ] **SSE-03**: Proper SSE headers: Content-Type text/event-stream, Cache-Control no-cache, Connection keep-alive
- [ ] **SSE-04**: Keep-alive comment events every 30s to prevent proxy timeouts
- [ ] **SSE-05**: Graceful disconnect handling via connection_aborted() check

### Backend — LLM Integration

- [ ] **LLM-01**: LiteLLM wrapper calling OpenRouter → Cerebras (openai/gpt-oss-120b) with structured outputs
- [ ] **LLM-02**: Structured output schema: {message: string, trades: array, watchlist_changes: array}
- [ ] **LLM-03**: System prompt: FinAlly AI trading assistant, data-driven, concise, always valid JSON
- [ ] **LLM-04**: Context injection: cash balance, positions with P&L, watchlist with live prices, total portfolio value, recent chat history
- [ ] **LLM-05**: Auto-execute approved trades and watchlist changes after validation
- [ ] **LLM-06**: Retry once on malformed structured output; fall back gracefully on repeated failure
- [ ] **LLM-07**: LLM_MOCK=true mode returns deterministic mock responses for testing

### Backend — Portfolio Snapshots

- [ ] **SNAP-01**: Background task records portfolio total value to portfolio_snapshots every 30 seconds
- [ ] **SNAP-02**: Snapshot recorded immediately after each trade execution

### Frontend — Setup

- [ ] **FE-01**: Next.js 15 with App Router, TypeScript, static export (output: 'export')
- [ ] **FE-02**: Tailwind CSS v4 with dark theme (color-scheme: dark, backgrounds #0d1117/#1a1a2e)
- [ ] **FE-03**: State management: Zustand store for SSE price cache, shared across components
- [ ] **FE-04**: Color scheme: #ecad0a accent yellow, #209dd7 blue primary, #753991 purple secondary
- [ ] **FE-05**: EventSource connection to /api/stream/prices with auto-reconnect

### Frontend — Watchlist

- [ ] **WL-01**: Grid of watched tickers showing: symbol, current price, daily change %, sparkline
- [ ] **WL-02**: Price flash animation: green background on uptick, red on downtick, fades over ~500ms via CSS transition
- [ ] **WL-03**: Sparkline mini-chart: accumulated from SSE stream since page load, canvas-based (Lightweight Charts)
- [ ] **WL-04**: Click ticker row → selects it for main chart display
- [ ] **WL-05**: Add ticker via input + button (POST /api/watchlist)
- [ ] **WL-06**: Remove ticker via delete button on row (DELETE /api/watchlist/{ticker})

### Frontend — Main Chart Area

- [ ] **CH-01**: Larger chart for selected ticker using Lightweight Charts
- [ ] **CH-02**: Real-time updates via series.update() (NOT setData) for streaming prices
- [ ] **CH-03**: Default view: 1-day price action, time-based X axis, price-based Y axis
- [ ] **CH-04**: OHLC candles or line chart (canvas-based, performant at ~500ms update rate)

### Frontend — Portfolio

- [ ] **PF-01**: Portfolio heatmap: treemap visualization, rectangles sized by portfolio weight, colored by P&L (green = profit, red = loss)
- [ ] **PF-02**: P&L chart: line chart of total portfolio value over time, from /api/portfolio/history
- [ ] **PF-03**: Positions table: ticker, quantity, avg cost, current price, unrealized P&L, % change
- [ ] **PF-04**: Cash balance displayed in header and portfolio panel
- [ ] **PF-05**: Total portfolio value (cash + positions) displayed in header, updates live

### Frontend — Trade Bar

- [ ] **TB-01**: Ticker input field (text)
- [ ] **TB-02**: Quantity input field (number, fractional shares supported)
- [ ] **TB-03**: Buy button — submits market buy order
- [ ] **TB-04**: Sell button — submits market sell order
- [ ] **TB-05**: Instant fill at current price, no confirmation dialog
- [ ] **TB-06**: Cash insufficient → show error inline, do not execute
- [ ] **TB-07**: Shares insufficient (sell) → show error inline, do not execute

### Frontend — AI Chat Panel

- [ ] **CHAT-01**: Collapsible sidebar panel with chat interface
- [ ] **CHAT-02**: Message input field + send button
- [ ] **CHAT-03**: Scrollable conversation history (user + assistant messages)
- [ ] **CHAT-04**: Loading indicator while waiting for LLM response
- [ ] **CHAT-05**: Trade execution confirmations shown inline in chat (e.g., "Bought 10 AAPL @ $191.50")
- [ ] **CHAT-06**: Watchlist change confirmations shown inline (e.g., "Added TSLA to watchlist")
- [ ] **CHAT-07**: Error messages shown inline when trade fails validation

### Frontend — Header & Status

- [ ] **HDR-01**: Header bar: portfolio total value (live), cash balance, connection status dot
- [ ] **HDR-02**: Connection status dot: green = connected, yellow = reconnecting, red = disconnected
- [ ] **HDR-03**: Auto-reconnect on disconnect (EventSource handles this)

### Docker & Deployment

- [ ] **DOCKER-01**: Multi-stage Dockerfile: Stage 1 (Node 20 → build Next.js static export), Stage 2 (Python 3.12 + uv → run FastAPI)
- [ ] **DOCKER-02**: FastAPI serves static frontend files on /
- [ ] **DOCKER-03**: FastAPI serves API routes on /api/*
- [ ] **DOCKER-04**: Single port 8000 exposed
- [ ] **DOCKER-05**: Docker volume mount for db/ directory (SQLite persistence across container restarts)
- [ ] **DOCKER-06**: Start script (macOS/Linux): builds image, runs container with volume + env file, prints URL
- [ ] **DOCKER-07**: Stop script (macOS/Linux): stops and removes container, preserves volume
- [ ] **DOCKER-08**: Windows PowerShell equivalents for start/stop scripts
- [ ] **DOCKER-09**: docker-compose.yml as optional convenience wrapper

### Testing

- [ ] **TEST-01**: Backend unit tests: market simulator GBM math, trade execution logic, P&L calculations, edge cases (sell more than owned, buy with insufficient cash), LLM structured output parsing
- [ ] **TEST-02**: Frontend unit tests: component rendering with mock data, price flash triggers, watchlist CRUD, portfolio calculations
- [ ] **TEST-03**: E2E Playwright tests: fresh start (default watchlist, $10k balance, streaming prices), add/remove ticker, buy shares (cash decreases, position appears), sell shares (cash increases, position updates/disappears), portfolio visualizations render, AI chat with mocked LLM, SSE disconnect/reconnect

## v2 Requirements

(None yet — to be defined)

## Out of Scope

| Feature | Reason |
|---------|--------|
| Real trading (money or real brokerage) | Fake cash, simulated fills only |
| Limit orders | Market orders only — dramatically simpler; no order book |
| Multi-user authentication | Single "default" user — schema supports future expansion |
| Mobile app | Desktop-first — browser only |
| Video or advanced chart types | Canvas-based lightweight charts for core OHLC only |
| Order book visualization | Not in the product specification |
| WebSocket upgrades | SSE is sufficient for one-way server→client push |
| PostgreSQL or external database | SQLite is self-contained and zero-config |

## Traceability

| Requirement | Phase | Status |
|-------------|-------|--------|
| DB-01 — DB-04 | Phase 1 | Pending |
| MKT-01 — MKT-05 | Phase 0 (Validated) | Complete |
| MKT-06 — MKT-07 | Phase 1 | Pending |
| MAP-01 — MAP-03 | Phase 0 (Validated) | Complete |
| API-01 — API-06, API-08 | Phase 2 | Pending |
| API-07 (chat) | Phase 3 | Pending |
| SSE-01 — SSE-05 | Phase 2 | Pending |
| LLM-01 — LLM-07 | Phase 3 | Pending |
| SNAP-01 — SNAP-02 | Phase 2 | Pending |
| FE-01 — FE-05 | Phase 4 | Pending |
| WL-01 — WL-06 | Phase 4 | Pending |
| CH-01 — CH-04 | Phase 4 | Pending |
| PF-01 — PF-05 | Phase 4 | Pending |
| TB-01 — TB-07 | Phase 4 | Pending |
| CHAT-01 — CHAT-07 | Phase 4 | Pending |
| HDR-01 — HDR-03 | Phase 4 | Pending |
| DOCKER-01 — DOCKER-09 | Phase 4 | Pending |
| TEST-01 — TEST-03 | Phase 4 | Pending |

**Coverage:**
- v1 requirements: 78 total
- Market data (MKT-01..MKT-05, MAP-01..MAP-03): 8 validated complete
- Remaining mapped to phases: 70
- Unmapped: 0

---
*Requirements defined: 2026-06-26*
*Last updated: 2026-06-26 after roadmap creation*
