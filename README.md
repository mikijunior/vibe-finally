# FinAlly — AI Trading Workstation

A Bloomberg-inspired AI trading workstation with live market data, simulated portfolio trading, and an LLM copilot that executes trades via natural language.

Built by orchestrated AI coding agents.

## Quick Start

```bash
cp .env.example .env          # Add OPENROUTER_API_KEY for AI chat
./scripts/start_mac.sh        # Builds & runs Docker container
open http://localhost:8000
```

**What you get immediately:** 10 default tickers with live prices, $10,000 virtual cash, dark terminal UI, AI chat panel ready to go.

## Features

| Feature | Description |
|---------|-------------|
| **Live prices** | SSE stream, green/red flash animations on tick |
| **Trading** | Market orders, instant fill, fractional shares, no fees |
| **Portfolio view** | Treemap heatmap, P&L chart, positions table |
| **AI Copilot** | Chat to analyze positions, suggest trades, auto-execute |
| **Watchlist** | Add/remove tickers manually or via AI |

## Architecture

Single Docker container on **port 8000**:

```
FastAPI (Python/uv)          Next.js (TypeScript, static export)
├── /api/*      REST         served as static/
├── /api/stream/*  SSE       
└── /*          static files
```

- **Market data**: GBM simulator (default) or Polygon.io via Massive SDK
- **AI**: LiteLLM → OpenRouter (Cerebras), structured outputs
- **Database**: SQLite at `db/finally.db` (volume-mounted)
- **Real-time**: SSE (server → client only)

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `OPENROUTER_API_KEY` | — | Required for AI chat. Without it, chat panel is disabled. |
| `MASSIVE_API_KEY` | — | Optional. Real market data via Polygon.io; omit for simulator. |
| `LLM_MOCK` | `false` | Deterministic mock LLM responses (testing/E2E) |

## Project Layout

```
finally/
├── frontend/          # Next.js (static export)
├── backend/          # FastAPI uv project
│   └── app/market/   # Market data subsystem (simulator + Massive)
├── planning/         # Full spec, agent contracts
├── test/             # Playwright E2E tests
└── scripts/          # start_mac.sh, stop_mac.sh
```

## Backend Dev

```bash
cd backend
uv sync --extra dev
uv run pytest -v --cov=app
uv run market_data_demo.py   # Rich terminal demo of live prices
```

## Demo

Market data is fully implemented and testable without any API keys:

```bash
cd backend && uv run market_data_demo.py
```

Shows a Rich terminal dashboard with 10 tickers, sparklines, and event log.
