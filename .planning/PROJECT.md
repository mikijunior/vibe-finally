# FinAlly — AI Trading Workstation

## What This Is

FinAlly (Finance Ally) is a visually stunning AI-powered trading workstation that streams live market data, lets users trade a simulated portfolio, and integrates an LLM chat assistant that can analyze positions and execute trades on the user's behalf. It looks and feels like a modern Bloomberg terminal with an AI copilot.

This is the capstone project for an agentic AI coding course. It is built entirely by Coding Agents demonstrating how orchestrated AI agents can produce a production-quality full-stack application.

## Core Value

A single-container, zero-setup trading platform where AI agents collaborate to build a professional-grade trading workstation that any student can launch with one Docker command.

## Business Context

- **Customer**: Coding course students learning agentic AI workflows
- **Revenue model**: Course capstone project — no monetization
- **Success metric**: All 10 default tickers streaming live prices; user can buy, sell, chat with AI, and see portfolio visualizations
- **Strategy notes**: Built by agents, for agents — demonstrates full-stack AI-powered application delivery

## Requirements

### Validated

(None yet — ship to validate)

### Active

- [ ] FastAPI backend serving REST + SSE on port 8000
- [ ] Next.js static frontend served by FastAPI
- [ ] SQLite database with lazy initialization (users, watchlist, positions, trades, portfolio_snapshots, chat_messages)
- [ ] Market data SSE streaming (GET /api/stream/prices)
- [ ] Portfolio REST endpoints (GET /api/portfolio, POST /api/portfolio/trade, GET /api/portfolio/history)
- [ ] Watchlist CRUD (GET/POST/DELETE /api/watchlist)
- [ ] Chat endpoint (POST /api/chat) with LLM structured output
- [ ] Market data simulator (geometric Brownian motion, correlated moves, ~500ms updates)
- [ ] Massive API integration (optional, env-driven)
- [ ] Price flash animations (green/red, ~500ms CSS transitions)
- [ ] Watchlist grid with sparklines, prices, daily change %
- [ ] Main chart area (click ticker → detailed view)
- [ ] Portfolio heatmap (treemap, sized by weight, colored by P&L)
- [ ] P&L chart (portfolio value over time from snapshots)
- [ ] Positions table (ticker, qty, avg cost, current price, unrealized P&L, % change)
- [ ] Trade bar (ticker, quantity, buy/sell buttons, market orders, instant fill)
- [ ] AI chat panel (conversation history, loading indicator, inline trade confirmations)
- [ ] Header (portfolio total value, connection status dot, cash balance)
- [ ] Dark terminal aesthetic (#0d1117/#1a1a2e backgrounds, #ecad0a yellow, #209dd7 blue, #753991 purple)
- [ ] Docker multi-stage build (Node → Python, single port 8000)
- [ ] Start/stop scripts for macOS/Linux and Windows
- [ ] E2E Playwright tests with LLM_MOCK=true mode

### Out of Scope

- Real trading (money or real brokerage) — fake cash, simulated fills only
- Limit orders — market orders only, no order book
- Multi-user authentication — single "default" user, schema supports future expansion
- Mobile app — desktop-first, browser only
- Video/advanced chart types — canvas-based lightweight charts for core OHLC
- Order book visualization — not in plan

## Context

- The `backend/market/` directory contains the completed market data simulator and Massive API integration (per `planning/MARKET_DATA_SUMMARY.md`)
- The `backend/` has a basic structure with `pyproject.toml` and `uv.lock` already set up
- The `frontend/` directory does not yet exist — it needs to be created from scratch
- `planning/PLAN.md` contains the full product specification, architecture, API contracts, and database schema — this is the source of truth
- `planning/MARKET_DATA_SUMMARY.md` summarizes the completed market data work
- Docker build is not yet written — Dockerfile and docker-compose.yml need to be created
- No tests exist yet beyond the market data demo

## Constraints

- **Single Container**: One Docker container, one port (8000) — FastAPI serves both API and static frontend
- **No CORS**: Frontend and API share origin — no cross-origin configuration
- **SQLite persistence**: Volume-mounted at `db/finally.db` — no external database server
- **SSE only**: One-way server→client push only — no WebSockets
- **Market orders**: No limit orders, no partial fills, no fees
- **LLM via OpenRouter**: Cerebras inference for chat — structured outputs required
- **Next.js static export**: `output: 'export'` — no server-side rendering

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| SSE over WebSockets | One-way push is all we need; simpler, no bidirectional complexity | — Pending |
| Static Next.js export | Single origin, no CORS, one port, one container | — Pending |
| SQLite over Postgres | No auth = no multi-user = no need for a database server | — Pending |
| Single Docker container | Students run one command | — Pending |
| uv for Python | Fast, modern Python project management | — Pending |
| Market orders only | Eliminates order book, limit order logic, partial fills | — Pending |
| LLM structured outputs | Trade execution needs reliable JSON parsing | — Pending |

---

*Last updated: 2026-06-26 after initialization*
