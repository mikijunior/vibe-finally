# Roadmap: FinAlly — AI Trading Workstation

## Overview

FinAlly is a single-container AI-powered trading workstation streaming live market data, enabling simulated portfolio trading, and integrating an LLM copilot that can analyze positions and execute trades via natural language. The build sequence is: Database foundation -> Backend API + SSE streaming -> LLM integration -> Frontend + Docker + Testing.

**Market data component is ALREADY COMPLETE** (MKT-01 to MKT-07, MAP-01 to MAP-03) — grouped as validated. The plan below covers remaining work.

## Phases

- [ ] **Phase 1: Database Foundation** - SQLite schema, WAL mode, thread-safe price cache
- [ ] **Phase 2: Backend API + SSE Streaming** - REST endpoints, SSE streaming, portfolio snapshots
- [ ] **Phase 3: LLM Integration** - LiteLLM chat with structured output and auto-trade execution
- [ ] **Phase 4: Frontend + Docker + Testing** - All UI components, Docker deployment, E2E tests

## Phase Details

### Phase 1: Database Foundation
**Goal**: SQLite database with lazy initialization, WAL mode, INTEGER cents storage, and thread-safe price cache ready for SSE streaming
**Depends on**: Nothing (first phase)
**Requirements**: DB-01, DB-02, DB-03, DB-04, MKT-06, MKT-07
**Mode**: mvp
**Success Criteria** (what must be TRUE):
  1. SQLite database initializes on first request, creating all tables if missing
  2. All monetary values stored as INTEGER cents (no floating-point REAL for money)
  3. SQLite runs in WAL mode for concurrent read/write safety
  4. Default seed data present: user profile ($10,000 cash), 10 watchlist tickers
  5. Thread-safe PriceCache shared by all endpoints with ticker/price/previous_price/direction
**Plans**: 3 plans

Plans:
- [ ] 01-01: SQLite schema and lazy initialization (DB-01, DB-04)
- [ ] 01-02: WAL mode and INTEGER cents storage (DB-02, DB-03)
- [ ] 01-03: Thread-safe PriceCache with MarketDataSource interface (MKT-06, MKT-07)

### Phase 2: Backend API + SSE Streaming
**Goal**: Complete REST API layer and SSE streaming for real-time price updates
**Depends on**: Phase 1
**Requirements**: API-01, API-02, API-03, API-04, API-05, API-06, API-08, SSE-01, SSE-02, SSE-03, SSE-04, SSE-05, SNAP-01, SNAP-02
**Mode**: mvp
**Success Criteria** (what must be TRUE):
  1. User can fetch portfolio: cash balance, positions with P&L, total value via GET /api/portfolio
  2. User can execute market orders (buy/sell) via POST /api/portfolio/trade with validation
  3. User can fetch portfolio history via GET /api/portfolio/history
  4. User can manage watchlist: GET all tickers, POST to add, DELETE to remove via /api/watchlist
  5. Prices stream in real-time via SSE at /api/stream/prices (~500ms cadence)
  6. SSE events contain ticker, price, previous_price, timestamp, direction (up/down/unchanged)
  7. Portfolio value recorded every 30 seconds and after each trade
  8. Health check returns 200 at GET /api/health
**Plans**: 3 plans

Plans:
- [ ] 02-01: Portfolio + watchlist REST endpoints (API-01, API-02, API-03, API-04, API-05, API-06, API-08)
- [ ] 02-02: SSE streaming endpoint (SSE-01, SSE-02, SSE-03, SSE-04, SSE-05)
- [ ] 02-03: Portfolio snapshot background task (SNAP-01, SNAP-02)

### Phase 3: LLM Integration
**Goal**: AI chat assistant that loads portfolio context, calls LLM with structured output, and auto-executes approved trades
**Depends on**: Phase 2
**Requirements**: LLM-01, LLM-02, LLM-03, LLM-04, LLM-05, LLM-06, LLM-07, API-07
**Mode**: mvp
**Success Criteria** (what must be TRUE):
  1. User can send chat messages and receive AI responses via POST /api/chat
  2. AI receives full context: cash balance, positions with P&L, watchlist with live prices, total portfolio value, chat history
  3. AI responds with structured JSON: message, trades array, watchlist_changes array
  4. Approved trades execute automatically after validation (sufficient cash/shares)
  5. Watchlist changes (add/remove) execute automatically after validation
  6. LLM_MOCK=true returns deterministic responses for testing
  7. Retry once on malformed structured output; graceful fallback on repeated failure
**Plans**: 2 plans

Plans:
- [ ] 03-01: LiteLLM client + chat endpoint (LLM-01, LLM-02, LLM-03, LLM-04, API-07)
- [ ] 03-02: Auto-execution + retry logic + mock mode (LLM-05, LLM-06, LLM-07)

### Phase 4: Frontend + Docker + Testing
**Goal**: Complete trading workstation UI, Docker deployment, and E2E tests
**Depends on**: Phase 3
**Requirements**: FE-01, FE-02, FE-03, FE-04, FE-05, WL-01, WL-02, WL-03, WL-04, WL-05, WL-06, CH-01, CH-02, CH-03, CH-04, PF-01, PF-02, PF-03, PF-04, PF-05, TB-01, TB-02, TB-03, TB-04, TB-05, TB-06, TB-07, CHAT-01, CHAT-02, CHAT-03, CHAT-04, CHAT-05, CHAT-06, CHAT-07, HDR-01, HDR-02, HDR-03, DOCKER-01, DOCKER-02, DOCKER-03, DOCKER-04, DOCKER-05, DOCKER-06, DOCKER-07, DOCKER-08, DOCKER-09, TEST-01, TEST-02, TEST-03
**Mode**: mvp
**Success Criteria** (what must be TRUE):
  1. User sees dark terminal UI with watchlist grid: ticker, live price (flashing green/red), daily change %, sparkline
  2. User can click a ticker to view detailed chart in main chart area
  3. User can buy/sell shares via trade bar: instant fill at current price, inline errors for insufficient funds/shares
  4. User sees portfolio heatmap (treemap sized by weight, colored by P&L) and P&L chart (value over time)
  5. User sees positions table: ticker, quantity, avg cost, current price, unrealized P&L, % change
  6. User can chat with AI assistant: sends messages, sees responses, sees inline trade/watchlist confirmations
  7. Header shows live portfolio total value, cash balance, and SSE connection status dot (green/yellow/red)
  8. Docker container builds successfully and runs with one command; data persists across restarts
  9. Playwright E2E tests pass: watchlist CRUD, trade execution, portfolio display, AI chat, SSE resilience
**Plans**: 3 plans

Plans:
- [ ] 04-01: Frontend setup + watchlist + main chart (FE-01, FE-02, FE-03, FE-04, FE-05, WL-01, WL-02, WL-03, WL-04, WL-05, WL-06, CH-01, CH-02, CH-03, CH-04)
- [ ] 04-02: Portfolio visualizations + trade bar + chat + header (PF-01, PF-02, PF-03, PF-04, PF-05, TB-01, TB-02, TB-03, TB-04, TB-05, TB-06, TB-07, CHAT-01, CHAT-02, CHAT-03, CHAT-04, CHAT-05, CHAT-06, CHAT-07, HDR-01, HDR-02, HDR-03)
- [ ] 04-03: Docker deployment + E2E tests (DOCKER-01, DOCKER-02, DOCKER-03, DOCKER-04, DOCKER-05, DOCKER-06, DOCKER-07, DOCKER-08, DOCKER-09, TEST-01, TEST-02, TEST-03)

## Progress

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 1. Database Foundation | 0/3 | Not started | - |
| 2. Backend API + SSE Streaming | 0/3 | Not started | - |
| 3. LLM Integration | 0/2 | Not started | - |
| 4. Frontend + Docker + Testing | 0/3 | Not started | - |

## Coverage

**Market data (validated/already complete):**
- MKT-01, MKT-02, MKT-03, MKT-04, MKT-05: GBM simulator
- MKT-06, MKT-07: PriceCache + MarketDataSource interface
- MAP-01, MAP-02, MAP-03: Massive API integration

**All remaining v1 requirements mapped:** 67/67

| Phase | Requirements | Count |
|-------|--------------|-------|
| 1 - Database Foundation | DB-01, DB-02, DB-03, DB-04, MKT-06, MKT-07 | 6 |
| 2 - Backend API + SSE Streaming | API-01, API-02, API-03, API-04, API-05, API-06, API-08, SSE-01, SSE-02, SSE-03, SSE-04, SSE-05, SNAP-01, SNAP-02 | 14 |
| 3 - LLM Integration | LLM-01, LLM-02, LLM-03, LLM-04, LLM-05, LLM-06, LLM-07, API-07 | 8 |
| 4 - Frontend + Docker + Testing | FE-01, FE-02, FE-03, FE-04, FE-05, WL-01..WL-06, CH-01..CH-04, PF-01..PF-05, TB-01..TB-07, CHAT-01..CHAT-07, HDR-01..HDR-03, DOCKER-01..DOCKER-09, TEST-01..TEST-03 | 39 |
