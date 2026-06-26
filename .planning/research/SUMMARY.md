# Project Research Summary

**Project:** FinAlly - AI Trading Workstation
**Domain:** AI-Powered Trading Simulator
**Researched:** 2026-06-26
**Confidence:** HIGH

## Executive Summary

FinAlly is a single-container AI-powered trading workstation that streams live simulated market data, allows users to trade a virtual portfolio, and integrates an LLM copilot that can analyze positions and execute trades via natural language. The platform follows a proven architecture: FastAPI backend serving REST + SSE endpoints with Next.js static frontend on the same port. Key technical decisions include SSE over WebSockets (one-way push is sufficient), SQLite with WAL mode for persistence, LiteLLM via OpenRouter for AI integration, and canvas-based charting via Lightweight Charts.

The recommended build sequence is Phase 1 (Database Foundation), Phase 2 (Price Cache + Market Data), Phase 3 (REST API Layer), Phase 4 (SSE Streaming), Phase 5 (LLM Integration), Phase 6 (Frontend Visualizations), Phase 7 (Docker + Scripts), Phase 8 (E2E Tests). The critical path runs through Phase 4. LLM integration (Phase 5) can start after Phase 3 REST APIs are functional. Frontend visualizations (Phase 6) can overlap with Phase 4/5 since the frontend is isolated.

Key risks include: static export incompatibility with API routes (must resolve before frontend-backend integration), SQLite write serialization (must enable WAL mode), LLM parsing failures (must implement graceful fallback), price drift in the simulator (must implement bounds), and fractional share precision errors (must use Decimal for all financial calculations).

## Key Findings

### Recommended Stack

The stack is well-established and version-locked based on verified official documentation. **Next.js 15** with App Router and `output: 'export'` produces static files served by FastAPI on port 8000 -- but this creates a critical pitfall: API routes in Next.js static export are ignored, so ALL API logic must live in FastAPI. The frontend must make same-origin fetch calls to `/api/*` on the same origin (FastAPI). **TypeScript 5.x** catches trading logic bugs at compile time. **FastAPI 0.138.1** with native async handles SSE streaming via `StreamingResponse`. **aiosqlite** provides non-blocking SQLite access, keeping SSE responsive. **Zustand 5.x** manages client state without SSR pitfalls. **Lightweight Charts 5.2.0** is canvas-based (not SVG) and handles 500ms price updates without jank -- must use `series.update()` not `setData()` for real-time streaming. **LiteLLM** provides unified OpenRouter/Cerebras access with structured outputs; structured outputs are mandatory for reliable trade execution parsing.

### Expected Features

**Must have (table stakes):** Live price streaming via SSE, watchlist grid with ticker/price/change%, buy/sell trade bar (market orders only, instant fill, no confirmation), portfolio value display, position tracking table (ticker/qty/avg cost/current price/P&L), connection status indicator, dark terminal aesthetic (Bloomberg-style), cash balance display.

**Should have (competitive differentiators):** AI chat that executes trades via natural language (core differentiator), portfolio heatmap (treemap sized by weight, colored by P&L), sparkline mini-charts in watchlist (accumulate SSE data client-side), price flash animations (CSS transitions, ~500ms fade), P&L chart (portfolio value over time from snapshots).

**Defer to v2+:** Real market data via Massive API (simulator is fine for demo), limit orders (conflicts with market-order-only simplicity), multi-user authentication (schema already has user_id for future), mobile app (desktop-first is explicit design intent).

### Architecture Approach

The system uses a layered architecture with clear boundaries. Backend layers: Data Access (SQLite via aiosqlite repositories) -> Service Layer (portfolio, watchlist, chat business logic) -> API Layer (FastAPI routers). Market data layer: abstract `MarketDataSource` interface with two implementations (GBM simulator, Massive REST client) sharing a common `PriceCache`. SSE and REST both read from the price cache (single source of truth). Frontend layers: React components -> Zustand/context state -> custom hooks (usePriceStream, usePortfolio, useChat) -> API client (`lib/api.ts`). Critical anti-patterns: never mix business logic in HTTP handlers, never read market data inside REST response builders, never use synchronous SQLite in async handlers.

### Critical Pitfalls

1. **Next.js Static Export / API Routes Mismatch** -- With `output: 'export'`, Next.js API routes are ignored. ALL API logic must live in FastAPI. The frontend must make same-origin fetch calls to FastAPI at port 8000.
2. **SQLite Write Serialization** -- SQLite allows only one writer at a time. Must enable WAL mode (`PRAGMA journal_mode=WAL`), keep transactions short, and skip snapshot writes if the previous one was within 25 seconds.
3. **LLM Structured Output Parsing Failures** -- LLM returns malformed JSON occasionally despite schema constraints. Must wrap LiteLLM calls in try-catch with retry-once logic and graceful fallback.
4. **Fractional Share Precision Errors** -- IEEE 754 floating point produces penny discrepancies. Must use Python `Decimal` for all monetary calculations and store as INTEGER cents in SQLite, not REAL.
5. **Price Simulator Drift** -- GBM has no mean reversion. Over 24 hours prices can drift to implausible values. Must implement price bounds (clamp to +/-50% of seed price).

## Implications for Roadmap

### Phase 1: Database Foundation
**Rationale:** All downstream systems depend on persistent data. The database must be designed with WAL mode and INTEGER cents for monetary values before any trade logic is written.
**Delivers:** SQLite schema (all tables with user_id), repositories for user/position/trade/snapshot/watchlist/chat, seed data, database connection management.
**Addresses:** Fractional share precision (store as INTEGER cents), snapshot table growth (add recorded_at index).
**Research flag:** None -- well-documented SQLite patterns.

### Phase 2: Price Cache + Market Data
**Rationale:** The entire real-time experience depends on the price cache. Both simulator and Massive client must conform to the abstract interface before SSE can be built.
**Delivers:** Thread-safe PriceCache, MarketDataSource abstract interface, GBM simulator (default), Massive REST client (optional), background task lifecycle.
**Research flag:** None -- GBM math and cache patterns are standard.

### Phase 3: REST API Layer
**Rationale:** Phase 4 (SSE) and Phase 5 (LLM) both depend on REST APIs being functional.
**Delivers:** `/api/portfolio` (GET), `/api/portfolio/trade` (POST), `/api/watchlist` (GET/POST/DELETE), `/api/health`, portfolio service, watchlist service.
**Research flag:** None -- FastAPI REST patterns are well-documented.

### Phase 4: SSE Streaming
**Rationale:** Core real-time experience. Must include disconnect detection, keep-alive comments, and proper SSE headers.
**Delivers:** `/api/stream/prices` SSE endpoint, `usePriceStream` React hook, price flash animations, connection status indicator.
**Addresses:** SSE memory leaks (connection_abort detection), reconnection storms (add jitter), keep-alive.
**Research flag:** Needs integration testing with actual disconnects.

### Phase 5: LLM Integration
**Rationale:** Headline feature. Can start after Phase 3 REST APIs are working.
**Delivers:** LiteLLM client wrapper, system prompts and structured output schema, chat service, `/api/chat` endpoint, chat_messages repository.
**Addresses:** LLM parse failures (retry + graceful fallback), chat history overflow (load only last N messages).
**Research flag:** Structured output schema needs testing against real model responses.

### Phase 6: Frontend Visualizations
**Rationale:** Visual polish differentiates FinAlly. Can overlap with Phase 4/5 since frontend is isolated.
**Delivers:** Main ticker chart (Lightweight Charts with `update()`), portfolio heatmap (treemap), P&L chart (line from snapshots), positions table, sparklines.
**Research flag:** Lightweight Charts v5 API -- verify `update()` API for streaming data.

### Phase 7: Docker + Scripts
**Rationale:** The one-command student experience. Must be the last backend phase.
**Delivers:** Multi-stage Dockerfile, docker-compose.yml, start/stop scripts.
**Addresses:** uv Docker build failure (install uv via pip before `uv sync`), volume mount path mismatch.
**Research flag:** Must verify Docker build locally.

### Phase 8: E2E Tests
**Rationale:** Validates all user journeys before shipping.
**Delivers:** Playwright tests for watchlist CRUD, trade execution, portfolio display, AI chat (mocked), SSE resilience.
**Research flag:** None -- Playwright patterns are standard.

### Phase Ordering Rationale

1. Phase 1 -> 2 -> 3 -> 4 is strictly sequential (each builds on the previous).
2. Phase 5 (LLM) starts after Phase 3 REST APIs work, can overlap with Phase 4.
3. Phase 6 (Frontend Visualizations) starts after Phase 4 SSE is working, can overlap with Phase 5.
4. Phase 7 (Docker) and Phase 8 (E2E) depend on everything and run at the end.
5. Pitfall prevention is embedded in phase deliverables.

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack | HIGH | Verified against official docs (Next.js static export, Tailwind v4.3, FastAPI 0.138.1, Lightweight Charts v5.2.0, LiteLLM) |
| Features | HIGH | Feature set fully defined in PLAN.md, competitor analysis completed |
| Architecture | HIGH | Standard FastAPI+React patterns, clear component boundaries |
| Pitfalls | HIGH | 10 pitfalls identified with prevention strategies, verified against docs |

**Overall confidence:** HIGH

### Gaps to Address

1. **Lightweight Charts v5 API surface** -- Verified v5.2.0 as latest and `update()` vs `setData()` guidance. Exact API signature for streaming should be verified during Phase 6 planning.
2. **Real LLM structured output reliability** -- LiteLLM docs describe the mechanism but real model behavior under schema constraints varies. Phase 5 should include prompt/response testing sprint.
3. **Tailwind CSS v4 compatibility** -- v4 uses CSS-first `@theme` directive which is new. If `@tailwindcss/postcss` has compatibility issues with Next.js 15, fall back to v3.4.

## Sources

### Primary (HIGH confidence)
- [Next.js Static Export docs](https://nextjs.org/docs/app/guides/static-exports) -- verified `output: 'export'` behavior, API route incompatibility
- [Tailwind CSS v4.3 docs](https://tailwindcss.com/docs/installation) -- `@theme` directive, dark mode
- [TradingView Lightweight Charts](https://tradingview.github.io/lightweight-charts/) -- `update()` vs `setData()` performance guidance
- [FastAPI on PyPI](https://pypi.org/project/fastapi/) -- confirmed 0.138.1 as latest
- [MDN Server-Sent Events](https://developer.mozilla.org/en-US/docs/Web/API/Server-Sent_events/Using_server-sent_events) -- connection limits, reconnection
- [LiteLLM docs](https://docs.litellm.ai/) -- structured outputs, mock mode

### Secondary (HIGH confidence)
- [SQLite Whentouse](https://www.sqlite.org/whentouse.html) -- WAL mode, concurrency
- [FastAPI Lifespan Documentation](https://fastapi.tiangolo.com/reference/fastapi/) -- background tasks
- [aiosqlite GitHub](https://github.com/psycopg/aiosqlite) -- async SQLite pattern
- [Polygon.io Market Data API](https://polygon.io/docs) -- Massive API REST patterns

### Research Files
- `.planning/research/STACK.md` -- Full stack analysis
- `.planning/research/FEATURES.md` -- Feature landscape, prioritization
- `.planning/research/ARCHITECTURE.md` -- Component map, data flows, build order
- `.planning/research/PITFALLS.md` -- 10 critical pitfalls, anti-patterns

---
*Research completed: 2026-06-26*
*Ready for roadmap: yes*
