# Stack Research

**Domain:** AI Trading Workstation
**Researched:** 2026-06-26
**Confidence:** HIGH

## Recommended Stack

### Core Technologies

| Technology | Version | Purpose | Why Recommended |
|------------|---------|---------|-----------------|
| **Next.js** | 15.x | React framework, static export | App Router is the standard React pattern; `output: 'export'` produces static files served by FastAPI; no SSR complexity needed for a single-page trading dashboard |
| **TypeScript** | 5.x | Type safety | Catches trading logic bugs at compile time; all major trading UI libraries ship types; required for maintainable AI-trading codebase |
| **Python** | 3.12 | Backend runtime | Already specified in project; excellent for financial calculations; FastAPI's async support handles SSE at scale |
| **FastAPI** | 0.138.1 | REST API + SSE streaming | Native async, automatic OpenAPI docs, SSE support via `StreamingResponse`; most modern Python web framework |
| **uv** | (latest) | Python package manager | Already specified in project; faster installs, deterministic lockfiles, what the course teaches |
| **LiteLLM** | (latest via pip) | LLM orchestration | Unified interface to OpenRouter/Cerebras; structured outputs via `response_format`; mock mode built-in for testing |
| **SQLite** | 3.x | Persistence | Already specified; zero-config, self-contained; adequate for single-user simulated trading |
| **Tailwind CSS** | 4.3 | Styling | Latest version with `@theme` directive; CSS-first config; dark mode via `color-scheme: dark`; no per-component class extraction overhead |
| **React** | 19 | UI library | Comes with Next.js 15; Concurrent features help with SSE-driven re-renders |
| **Zustand** | 5.x | Client state management | Minimal boilerplate; works with static export (no SSR pitfalls); ideal for price cache and portfolio state shared across components |

### Supporting Libraries

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| **Lightweight Charts** | 5.2.0 | Canvas-based financial charts | Main chart area and sparklines; `update()` method (NOT `setData()`) for real-time streaming data per TradingView docs |
| **shadcn/ui** | (latest) | Accessible component primitives | Trade bar, chat panel, positions table; copy-paste components, no package dependency |
| **SWR** | 2.x | Client-side data fetching | Fetching REST endpoints (`/api/portfolio`, `/api/watchlist`) with built-in revalidation and caching |
| **aiosqlite** | (latest) | Async SQLite access | Non-blocking DB reads in FastAPI route handlers; keeps SSE loop responsive |
| **Pydantic** | 2.x | Data validation | Request/response models in FastAPI; trade validation logic; structured output parsing from LLM |
| **python-dotenv** | (latest) | Environment variable loading | Reads `.env` for `OPENROUTER_API_KEY`, `MASSIVE_API_KEY`, `LLM_MOCK` |
| **Rich** | 13.x | Terminal output | Market data demo script; already in backend dependencies |

### Development Tools

| Tool | Purpose | Notes |
|------|---------|-------|
| **Playwright** | E2E browser testing | Already in plan; run against `LLM_MOCK=true` for deterministic tests |
| **pytest** | Backend unit tests | Already in pyproject.toml; use `pytest-asyncio` for async route tests |
| **ruff** | Python linting | Already in pyproject.toml; faster than flake8, covers isort + pyupgrade |
| **ESLint + TypeScript plugin** | Frontend linting | Comes with Next.js scaffold; add `tailwindcss` plugin |
| **Prettier** | Frontend formatting | Standard with Next.js; add `prettier-plugin-tailwindcss` for class sorting |

## Installation

### Frontend

```bash
# Create Next.js app (choose: TypeScript yes, Tailwind yes, ESLint yes, App Router yes, src/ no)
npx create-next-app@latest frontend --typescript --tailwind --eslint --app --no-src-dir --import-alias "@/*"

cd frontend
npm install lightweight-charts swr zustand clsx tailwind-merge
npm install -D @types/node
```

### Backend

```bash
cd backend
uv sync

# Add LiteLLM for AI chat
uv add litellm

# Add aiosqlite for async DB
uv add aiosqlite
```

## Alternatives Considered

| Recommended | Alternative | When to Use Alternative |
|-------------|-------------|------------------------|
| Next.js 15 static export | Vite + React SPA | If needing faster build times or simpler mental model; but Next.js static export gives routing, code splitting, and image optimization for free |
| Zustand | Redux Toolkit | Redux has too much boilerplate for a single-user dashboard; Zustand covers all state sharing needs with minimal API |
| Lightweight Charts | Recharts | Recharts is SVG-based and cannot handle 500ms price updates without jank; Lightweight Charts is canvas-based and purpose-built for financial data |
| SWR | React Query | SWR is lighter and sufficient for read-heavy trading dashboards; React Query adds bloat for marginal benefit |
| shadcn/ui | MUI / Ant Design | shadcn/ui components are copy-paste (not a package) so no version lock-in; accessible by default; dark theme matches trading terminals |
| Tailwind CSS v4 | Tailwind CSS v3 | v4 has CSS-first config (`@theme` directive) which is simpler; however v4 is very new - if compatibility issues arise, fall back to v3.4 |
| FastAPI | Flask | Flask requires more boilerplate for SSE and has no native async; FastAPI's auto-generated OpenAPI docs are a bonus |
| LiteLLM | Direct OpenAI SDK | LiteLLM adds OpenRouter abstraction, unified interface, and mock mode for testing; direct SDK ties you to one provider |
| aiosqlite | sqlite3 (sync) | Synchronous SQLite blocks the uvicorn worker thread; aiosqlite keeps SSE streaming responsive |

## What NOT to Use

| Avoid | Why | Use Instead |
|-------|-----|-------------|
| WebSockets | One-way SSE is all the design requires; WebSockets add bidirectional complexity, proxy configuration, and browser reconnect logic for no benefit | SSE via FastAPI `StreamingResponse` |
| Next.js Pages Router | Pages Router is the legacy pattern; App Router enables React Server Components, better streaming, and is the direction the ecosystem is moving | Next.js App Router |
| `setData()` for real-time charts | TradingView explicitly warns against calling `setData()` for updates as it replaces all data and hurts performance | `series.update()` for single-point updates |
| `axios` | `fetch` is native, works everywhere, and covers all HTTP needs; axios adds a dependency for marginal features | Native `fetch` |
| Chart.js | SVG-based, cannot handle high-frequency updates without performance collapse | Lightweight Charts (canvas) |
| PostgreSQL | Adds a separate server process; far too heavy for a single-user simulation with no auth | SQLite |
| Separate Docker containers | Single-container design is a core constraint; docker-compose adds complexity that defeats the one-command student experience | Single multi-stage Dockerfile |
| Server-Side Rendering for the trading UI | The dashboard is entirely client-driven (prices via SSE, trades via POST); SSR adds complexity for no benefit with static export | Static Next.js export, client-side rendering |

## Stack Patterns by Variant

**If using the market simulator (default):**
- No external API dependencies at runtime
- Everything works offline
- Backend is fully self-contained

**If using Massive API for real market data:**
- Set `MASSIVE_API_KEY` environment variable
- No code changes needed -- the `MarketDataSource` factory handles the switch
- Backend uses REST polling (every 15s on free tier), not WebSockets

**If running E2E tests:**
- Set `LLM_MOCK=true` -- deterministic mock responses, no API key needed, fast tests
- Playwright container connects to the app container via docker-compose.test.yml

## Version Compatibility

| Package | Compatible With | Notes |
|---------|-----------------|-------|
| Next.js 15 | React 19, TypeScript 5.x | React 19 is included with Next.js 15; do not pin React separately |
| Tailwind CSS 4.3 | Next.js 15, PostCSS | v4 uses `@tailwindcss/postcss` plugin instead of `tailwindcss` PostCSS plugin; check `@tailwindcss/postcss` compatibility |
| FastAPI 0.138.1 | Python 3.12+, uvicorn 0.32+ | Already in pyproject.toml with uvicorn[standard] |
| LiteLLM (latest) | Python 3.10+ | Check PyPI for exact version; requires `OPENROUTER_API_KEY` in environment |
| Lightweight Charts 5.2.0 | All modern browsers (ES2020+) | No IE11 support; fine for a desktop-first trading app |
| aiosqlite (latest) | Python 3.10+ | Async wrapper around sqlite3; shares SQLite file format with the sync version |
| Zustand 5.x | React 18+ | React 19 support confirmed; no SSR concerns with static export |

## Sources

- [Next.js Static Export docs](https://nextjs.org/docs/app/guides/static-exports) -- verified current syntax for `output: 'export'`, supported/unsupported features, version history (v14 removed `next export`, v13.3 deprecated)
- [Tailwind CSS v4.3 docs](https://tailwindcss.com/docs/installation) -- confirmed v4.3 as latest, `@theme` directive, `color-scheme` for dark mode
- [TradingView Lightweight Charts](https://tradingview.github.io/lightweight-charts/) -- confirmed v5.2.0 latest, `update()` vs `setData()` performance guidance, series type immutability
- [FastAPI on PyPI](https://pypi.org/project/fastapi/) -- confirmed 0.138.1 as latest version (June 25, 2026)
- [React.dev new project guide](https://react.dev/learn/start-a-new-react-project) -- Next.js App Router is recommended framework in 2025
- [LiteLLM docs](https://docs.litellm.ai/) -- structured outputs via `response_format` parameter, mock mode for testing

---
*Stack research for: AI Trading Workstation*
*Researched: 2026-06-26*
