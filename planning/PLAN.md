# FinAlly — AI Trading Workstation

## Project Specification

## 1. Vision

FinAlly (Finance Ally) is a visually stunning AI-powered trading workstation that streams live market data, lets users trade a simulated portfolio, and integrates an LLM chat assistant that can analyze positions and execute trades on the user's behalf. It looks and feels like a modern Bloomberg terminal with an AI copilot.

This is the capstone project for an agentic AI coding course. It is built entirely by Coding Agents demonstrating how orchestrated AI agents can produce a production-quality full-stack application. Agents interact through files in `planning/`.

## 2. User Experience

### First Launch

The user runs a single Docker command (or a provided start script). A browser opens to `http://localhost:8000`. No login, no signup. They immediately see:

- A watchlist of 10 default tickers with live-updating prices in a grid
- $10,000 in virtual cash
- A dark, data-rich trading terminal aesthetic
- An AI chat panel ready to assist

### What the User Can Do

- **Watch prices stream** — prices flash green (uptick) or red (downtick) with subtle CSS animations that fade
- **View sparkline mini-charts** — price action beside each ticker in the watchlist, accumulated on the frontend from the SSE stream since page load (sparklines fill in progressively)
- **Click a ticker** to see a larger detailed chart in the main chart area
- **Buy and sell shares** — market orders only, instant fill at current price, no fees, no confirmation dialog
- **Monitor their portfolio** — a heatmap (treemap) showing positions sized by weight and colored by P&L, plus a P&L chart tracking total portfolio value over time
- **View a positions table** — ticker, quantity, average cost, current price, unrealized P&L, % change
- **Chat with the AI assistant** — ask about their portfolio, get analysis, and have the AI execute trades and manage the watchlist through natural language
- **Manage the watchlist** — add/remove tickers manually or via the AI chat

### Visual Design

- **Dark theme**: backgrounds around `#0d1117` or `#1a1a2e`, muted gray borders, no pure black
- **Price flash animations**: brief green/red background highlight on price change, fading over ~500ms via CSS transitions
- **Connection status indicator**: a small colored dot (green = connected, yellow = reconnecting, red = disconnected) visible in the header
- **Professional, data-dense layout**: inspired by Bloomberg/trading terminals — every pixel earns its place
- **Responsive but desktop-first**: optimized for wide screens, functional on tablet

### Color Scheme
- Accent Yellow: `#ecad0a`
- Blue Primary: `#209dd7`
- Purple Secondary: `#753991` (submit buttons)

## 3. Architecture Overview

### Single Container, Single Port

```
┌─────────────────────────────────────────────────┐
│  Docker Container (port 8000)                   │
│                                                 │
│  FastAPI (Python/uv)                            │
│  ├── /api/*          REST endpoints             │
│  ├── /api/stream/*   SSE streaming              │
│  └── /*              Static file serving         │
│                      (Next.js export)            │
│                                                 │
│  SQLite database (volume-mounted)               │
│  Background task: market data polling/sim        │
└─────────────────────────────────────────────────┘
```

- **Frontend**: Next.js with TypeScript, built as a static export (`output: 'export'`), served by FastAPI as static files
- **Backend**: FastAPI (Python), managed as a `uv` project
- **Database**: SQLite, single file at `db/finally.db`, volume-mounted for persistence
- **Real-time data**: Server-Sent Events (SSE) — simpler than WebSockets, one-way server→client push, works everywhere
- **AI integration**: LiteLLM → OpenRouter (Cerebras for fast inference), with structured outputs for trade execution
- **Market data**: Environment-variable driven — simulator by default, real data via Massive API if key provided

### Why These Choices

| Decision | Rationale |
|---|---|
| SSE over WebSockets | One-way push is all we need; simpler, no bidirectional complexity, universal browser support |
| Static Next.js export | Single origin, no CORS issues, one port, one container, simple deployment |
| SQLite over Postgres | No auth = no multi-user = no need for a database server; self-contained, zero config |
| Single Docker container | Students run one command; no docker-compose for production, no service orchestration |
| uv for Python | Fast, modern Python project management; reproducible lockfile; what students should learn |
| Market orders only | Eliminates order book, limit order logic, partial fills — dramatically simpler portfolio math |

---

## 4. Directory Structure

```
finally/
├── frontend/                 # Next.js TypeScript project (static export)
├── backend/                  # FastAPI uv project (Python)
│   └── db/                   # Schema definitions, seed data, migration logic
├── planning/                 # Project-wide documentation for agents
│   ├── PLAN.md               # This document
│   └── ...                   # Additional agent reference docs
├── scripts/
│   ├── start_mac.sh          # Launch Docker container (macOS/Linux)
│   ├── stop_mac.sh           # Stop Docker container (macOS/Linux)
│   ├── start_windows.ps1     # Launch Docker container (Windows PowerShell)
│   └── stop_windows.ps1      # Stop Docker container (Windows PowerShell)
├── test/                     # Playwright E2E tests + docker-compose.test.yml
├── db/                       # Volume mount target (SQLite file lives here at runtime)
│   └── .gitkeep              # Directory exists in repo; finally.db is gitignored
├── Dockerfile                # Multi-stage build (Node → Python)
├── docker-compose.yml        # Developer convenience: `docker compose up` builds and runs the container with the correct volume/env flags. Not required for the canonical quick-start (use scripts/start_mac.sh instead).
├── .env                      # Environment variables (gitignored, .env.example committed)
└── .gitignore
```

### Key Boundaries

- **`frontend/`** is a self-contained Next.js project. It knows nothing about Python. It talks to the backend via `/api/*` endpoints and `/api/stream/*` SSE endpoints. Internal structure is up to the Frontend Engineer agent.
- **`backend/`** is a self-contained uv project with its own `pyproject.toml`. It owns all server logic including database initialization, schema, seed data, API routes, SSE streaming, market data, and LLM integration. Internal structure is up to the Backend/Market Data agents.
- **`backend/db/`** contains schema SQL definitions and seed logic. The backend initializes the database at startup — creating tables and seeding default data if the SQLite file doesn't exist or is empty.
- **`db/`** at the top level is the runtime volume mount point. The SQLite file (`db/finally.db`) is created here by the backend and persists across container restarts via Docker volume.
- **`planning/`** contains project-wide documentation, including this plan. All agents reference files here as the shared contract.
- **`test/`** contains Playwright E2E tests and supporting infrastructure (e.g., `docker-compose.test.yml`). Unit tests live within `frontend/` and `backend/` respectively, following each framework's conventions.
- **`scripts/`** contains start/stop scripts that wrap Docker commands.

---

### Global Conventions

- **Timestamps**: all timestamps are UTC ISO 8601 strings (e.g., `"2024-01-15T10:30:00Z"`), generated by `datetime.utcnow().isoformat() + 'Z'` in Python.
- **Money / prices**: stored and calculated as integers representing cents (× 100) in the backend to avoid floating-point errors. Rounding to 2 decimal places happens only at display time (frontend formatting or API response serialization). Backend trade execution uses `round(price * quantity, 2)`.
- **Routers before static mounts**: in FastAPI, API route handlers (including SSE) must be registered before mounting the static file middleware, otherwise requests to `/api/stream/prices` may be caught by the `/*` static file handler and return an HTML 404. The backend must use `app.include_router(...)` before `app.mount(...)`.

```bash
# Optional: OpenRouter API key for LLM chat functionality.
# If absent or empty, the app runs with a disabled chat panel (mock responses are NOT automatic).
# Set to a valid key to enable the AI assistant.
OPENROUTER_API_KEY=

# Optional: Massive (Polygon.io) API key for real market data.
# If not set, the built-in market simulator is used (recommended for most users).
# "Massive" is the name of the Python client library for Polygon.io — do not implement a separate integration.
MASSIVE_API_KEY=

# Optional: Set to "true" for deterministic mock LLM responses (testing).
# Only effective when OPENROUTER_API_KEY is also set (or left empty).
LLM_MOCK=false
```

### Behavior

- If `OPENROUTER_API_KEY` is set and non-empty → backend uses LiteLLM/OpenRouter for chat; `LLM_MOCK` is ignored
- If `OPENROUTER_API_KEY` is absent or empty → the AI chat panel is disabled on the frontend (grayed out with a tooltip); no API calls are made
- If `MASSIVE_API_KEY` is set and non-empty → backend uses Massive (Polygon.io) REST API for market data
- If `MASSIVE_API_KEY` is absent or empty → backend uses the built-in market simulator
- If `LLM_MOCK=true` AND `OPENROUTER_API_KEY` is non-empty → backend returns deterministic mock LLM responses for E2E tests
- The backend reads `.env` from the project root (mounted into the container or read via docker `--env-file`)

---

## 6. Market Data

### Two Implementations, One Interface

Both the simulator and the Massive client implement the same abstract interface. The backend selects which to use based on the environment variable. All downstream code (SSE streaming, price cache, frontend) is agnostic to the source.

### Simulator (Default)

- Generates prices using geometric Brownian motion (GBM) with configurable drift and volatility per ticker
- Updates at ~500ms intervals
- Correlated moves: uses a two-factor model — a shared market factor (common Gaussian noise drawn once per tick) plus an independent idiosyncratic noise term per ticker, each with ticker-specific loadings (betas). This produces convincing co-movement without full Cholesky decomposition.
- Occasional random "events" — sudden 2-5% moves on a ticker for drama
- Starts from realistic seed prices (e.g., AAPL ~$190, GOOGL ~$175, etc.)
- Runs as an in-process background task — no external dependencies

### Massive API (Optional)

- REST API polling (not WebSocket) — simpler, works on all tiers
- Polls for the union of all watched tickers on a configurable interval
- Free tier (5 calls/min): poll every 15 seconds
- Paid tiers: poll every 2-15 seconds depending on tier
- Parses REST response into the same format as the simulator
- **Market hours**: outside regular market hours (weekdays 9:30–16:00 ET), Massive returns stale last-known prices. The backend continues serving the last received price. The frontend displays no special "market closed" state — the last available price is shown as-is. Overnight gaps from the simulator are independent of this behavior.

### Shared Price Cache

- A single background task (simulator or Massive poller) writes to an in-memory price cache
- The cache holds the latest price, previous price, and timestamp for each ticker
- SSE streams read from this cache and push updates to connected clients
- This architecture supports future multi-user scenarios without changes to the data layer

### SSE Streaming

- Endpoint: `GET /api/stream/prices`
- Long-lived SSE connection; client uses native `EventSource` API
- Server pushes price updates for all tickers currently in the user's watchlist at a regular cadence (~500ms)
- Removing a ticker from the watchlist immediately stops SSE events for that ticker (the backend's market data source continues generating it in case another user adds it back — this architecture is intentional for future multi-user scenarios)
- Each SSE event contains ticker, price, previous price, timestamp, and change direction
- **Startup**: on a new SSE connection, the server immediately sends the full current state of all tickers (one `price` event each) before entering the regular cadence, so the frontend's sparklines and prices have initial data without waiting for the first tick
- Client handles reconnection automatically (EventSource has built-in retry)

---

## 7. Database

### SQLite with Startup Initialization

The backend initializes the database on application startup — before the server begins accepting requests. If the SQLite file doesn't exist or tables are missing, it creates the schema and seeds default data. This gives clearer failure signals for Docker health checks and avoids hidden edge cases from lazy initialization.

### Schema

All tables include a `user_id` column defaulting to `"default"`. This is hardcoded for now (single-user) but enables future multi-user support without schema migration.

**users_profile** — User state (cash balance). Single-row table; there is no `user_id` column since this is a single-user app.
- `id` TEXT PRIMARY KEY (always `"default"`)
- `cash_balance` REAL (default: `10000.0`)
- `created_at` TEXT (ISO timestamp)

**watchlist** — Tickers the user is watching
- `id` TEXT PRIMARY KEY (UUID)
- `user_id` TEXT (default: `"default"`)
- `ticker` TEXT
- `added_at` TEXT (ISO timestamp)
- UNIQUE constraint on `(user_id, ticker)`

**positions** — Current holdings (one row per ticker per user)
- `id` TEXT PRIMARY KEY (UUID)
- `user_id` TEXT (default: `"default"`)
- `ticker` TEXT
- `quantity` REAL (fractional shares supported)
- `avg_cost` REAL
- `updated_at` TEXT (ISO timestamp)
- UNIQUE constraint on `(user_id, ticker)`

**trades** — Trade history (append-only log)
- `id` TEXT PRIMARY KEY (UUID)
- `user_id` TEXT (default: `"default"`)
- `ticker` TEXT
- `side` TEXT (`"buy"` or `"sell"`)
- `quantity` REAL (fractional shares supported)
- `price` REAL
- `executed_at` TEXT (ISO timestamp)

**portfolio_snapshots** — Portfolio value over time (for P&L chart). Recorded every 60 seconds by a background task, and immediately after each trade execution. Snapshots are best-effort: container restarts may cause gaps. An initial snapshot at `$10,000` is seeded at startup to anchor the chart for empty portfolios. Snapshots older than 24 hours may be pruned by a background cleanup task to bound storage (this is acceptable since the chart is for short-term session use).
- `id` TEXT PRIMARY KEY (UUID)
- `user_id` TEXT (default: `"default"`)
- `total_value` REAL
- `recorded_at` TEXT (ISO timestamp)

**chat_messages** — Conversation history with LLM
- `id` TEXT PRIMARY KEY (UUID)
- `user_id` TEXT (default: `"default"`)
- `role` TEXT (`"user"` or `"assistant"`)
- `content` TEXT
- `actions` TEXT (JSON — trades executed, watchlist changes made; null for user messages)
- `created_at` TEXT (ISO timestamp)

### Default Seed Data

- One user profile: `id="default"`, `cash_balance=10000.0`
- Ten watchlist entries: AAPL, GOOGL, MSFT, AMZN, TSLA, NVDA, META, JPM, V, NFLX

---

## 8. API Endpoints

### Market Data
| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/stream/prices` | SSE stream of live price updates |

### Portfolio
| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/portfolio` | Current positions, cash balance, total value, unrealized P&L |
| POST | `/api/portfolio/trade` | Execute a trade: `{ticker, quantity, side}` |
| GET | `/api/portfolio/history` | Portfolio value snapshots over time (for P&L chart) |

### Watchlist
| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/watchlist` | Current watchlist tickers with latest prices |
| POST | `/api/watchlist` | Add a ticker: `{ticker}` |
| DELETE | `/api/watchlist/{ticker}` | Remove a ticker |

### Chat
| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/chat` | Send a message, receive complete JSON response (message + executed actions) |

### System
| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/health` | Health check (for Docker/deployment) |

### Response Shapes

All timestamps are UTC ISO 8601 strings (e.g., `"2024-01-15T10:30:00Z"`). Money values are JSON numbers; the backend performs all calculations in cents (multiplied by 100) to avoid floating-point errors and rounds to 2 decimal places only at display time.

**GET `/api/portfolio`**
```json
{
  "cash_balance": 10000.00,
  "positions": [
    {
      "ticker": "AAPL",
      "quantity": 10,
      "avg_cost": 185.50,
      "current_price": 190.25,
      "unrealized_pnl": 47.50,
      "unrealized_pnl_pct": 2.56
    }
  ],
  "total_value": 10475.00,
  "total_value_including_cash": 20475.00
}
```
- `total_value` — sum of (quantity × current_price) across all positions
- `total_value_including_cash` — total_value + cash_balance; this is the figure shown in the header

**POST `/api/portfolio/trade`**
Request: `{"ticker": "AAPL", "quantity": 5, "side": "buy"}`
Success (200): `{"success": true, "trade_id": "uuid", "ticker": "AAPL", "quantity": 5, "side": "buy", "price": 190.25, "executed_at": "..."}`
Error (400): `{"success": false, "error": "Insufficient cash"}`

**GET `/api/watchlist`**
```json
{
  "tickers": [
    {
      "ticker": "AAPL",
      "current_price": 190.25,
      "previous_price": 190.10,
      "change_pct": 0.08,
      "direction": "up",
      "updated_at": "..."
    }
  ]
}
```

**POST `/api/chat`**
Request: `{"message": "Buy 10 shares of AAPL"}`
Success (200):
```json
{
  "message": "Done! I've bought 10 shares of AAPL at $190.25.",
  "trades": [{"ticker": "AAPL", "side": "buy", "quantity": 10, "price": 190.25}],
  "watchlist_changes": [],
  "errors": []
}
```
Error (400): `{"message": "...", "trades": [], "watchlist_changes": [], "errors": ["Insufficient cash"]}`

**GET `/api/stream/prices` — SSE**
```
event: price
data: {"ticker":"AAPL","price":190.25,"previous_price":190.10,"direction":"up","updated_at":"2024-01-15T10:30:00Z"}

event: price
data: {"ticker":"GOOGL","price":175.00,"previous_price":175.30,"direction":"down","updated_at":"2024-01-15T10:30:00Z"}
```
- The stream sends one `price` event per ticker, per update cycle (~500ms)
- The SSE connection is long-lived; clients should handle a `: ping` comment every ~30s to keep proxies alive

### Trade Validation Rules

- **Fractional shares**: supported for both buys and sells (e.g., buy 0.5 shares). Quantity is stored and calculated as a float.
- **Short selling**: forbidden. A sell order fails if the user does not own at least the requested quantity.
- **Rounding**: quantities are stored as-is. Prices used in trade calculations are rounded to 2 decimal places at execution time.
- **Position cleanup**: when a sell reduces a position's quantity to zero (or below, after floating-point edge cases), the position row is deleted from the `positions` table rather than kept with quantity 0.
- **Sufficient cash check (buys)**: `quantity × current_price` must not exceed `cash_balance`. The check uses the price at the moment the trade executes (not at order time).
- **Partial fills**: not applicable — market orders fill completely or not at all.

**GET `/api/portfolio/history`**
```json
{
  "snapshots": [
    {"total_value": 10475.00, "recorded_at": "2024-01-15T10:00:00Z"},
    {"total_value": 10480.00, "recorded_at": "2024-01-15T10:00:30Z"}
  ]
}
```

---

## 9. LLM Integration

When writing code to make calls to LLMs, use cerebras-inference skill to use LiteLLM via OpenRouter to the `openrouter/openai/gpt-oss-120b` model with Cerebras as the inference provider. Structured Outputs should be used to interpret the results.

There is an OPENROUTER_API_KEY in the .env file in the project root.

### How It Works

When the user sends a chat message, the backend:

1. Loads the user's current portfolio context (cash, positions with P&L, watchlist with live prices, total portfolio value)
2. Loads the last 20 `chat_messages` rows (10 user + 10 assistant turns) from the `chat_messages` table, ordered by `created_at` ascending. Older messages are dropped from context to avoid prompt bloat and token overruns.
3. Constructs a prompt with a system message, portfolio context, conversation history, and the user's new message
4. Calls the LLM via LiteLLM → OpenRouter, requesting structured output, using the cerebras-inference skill
5. Parses the complete structured JSON response
6. Auto-executes any trades or watchlist changes specified in the response
7. Stores the message and executed actions in `chat_messages`
8. Returns the complete JSON response to the frontend (no token-by-token streaming — Cerebras inference is fast enough that a loading indicator is sufficient)

### Structured Output Schema

The LLM is instructed to respond with JSON matching this schema:

```json
{
  "message": "Your conversational response to the user",
  "trades": [
    {"ticker": "AAPL", "side": "buy", "quantity": 10}
  ],
  "watchlist_changes": [
    {"ticker": "PYPL", "action": "add"}
  ]
}
```

- `message` (required): The conversational text shown to the user
- `trades` (optional): Array of trades to auto-execute. Each trade goes through the same validation as manual trades (sufficient cash for buys, sufficient shares for sells)
- `watchlist_changes` (optional): Array of watchlist modifications

### Auto-Execution

Trades specified by the LLM execute automatically — no confirmation dialog. This is a deliberate design choice:
- It's a simulated environment with fake money, so the stakes are zero
- It creates an impressive, fluid demo experience
- It demonstrates agentic AI capabilities — the core theme of the course

If a trade fails validation (e.g., insufficient cash), the error is included in the chat response so the LLM can inform the user.

When the LLM requests multiple actions and some succeed while others fail, **partial success is allowed**: the response includes both the successful trades and the errors. All actions attempted (both successful and failed) are stored in `chat_messages.actions` as a JSON array so the full audit trail is preserved. Example `actions` field:
```json
[
  {"type": "trade", "ticker": "AAPL", "side": "buy", "quantity": 10, "status": "success", "price": 190.25},
  {"type": "trade", "ticker": "TSLA", "side": "buy", "quantity": 100, "status": "error", "reason": "Insufficient cash"}
]
```

### System Prompt Guidance

The LLM should be prompted as "FinAlly, an AI trading assistant" with instructions to:
- Analyze portfolio composition, risk concentration, and P&L
- Suggest trades with reasoning
- Execute trades when the user asks or agrees
- Manage the watchlist proactively
- Be concise and data-driven in responses
- Always respond with valid structured JSON

### LLM Mock Mode

When `LLM_MOCK=true`, the backend returns deterministic mock responses instead of calling OpenRouter. This enables:
- Fast, free, reproducible E2E tests
- Development without an API key
- CI/CD pipelines

---

## 10. Frontend Design

### Layout

The frontend is a single-page application with a dense, terminal-inspired layout. The specific component architecture and layout system is up to the Frontend Engineer, but the UI should include these elements:

- **Watchlist panel** — grid/table of watched tickers with: ticker symbol, current price (flashing green/red on change), daily change %, and a sparkline mini-chart (accumulated from SSE since page load)
- **Main chart area** — larger chart for the currently selected ticker, with at minimum price over time. Clicking a ticker in the watchlist selects it here.
- **Portfolio heatmap** — treemap visualization where each rectangle is a position, sized by portfolio weight, colored by P&L (green = profit, red = loss)
- **P&L chart** — line chart showing total portfolio value over time, using data from `portfolio_snapshots`
  - **Implementation order**: implement the positions table and one of these two visualizations first (the treemap is recommended as the primary portfolio view). The second visualization can be added once the core trading and portfolio flows are stable. Both are specified here so both agent teams can plan accordingly.
- **Positions table** — tabular view of all positions: ticker, quantity, avg cost, current price, unrealized P&L, % change
- **Trade bar** — quantity field, buy button, sell button. Market orders, instant fill. The ticker is the one currently selected in the main chart / watchlist — no separate ticker input field. If no ticker is selected, the buy/sell buttons are disabled.
- **AI chat panel** — docked/collapsible sidebar. Message input, scrolling conversation history, loading indicator while waiting for LLM response. Trade executions and watchlist changes shown inline as confirmations.
- **Header** — portfolio total value (updating live), connection status indicator, cash balance

### Technical Notes

- Use `EventSource` for SSE connection to `/api/stream/prices`
- Use **Lightweight Charts** (by TradingView) for all price charts — purpose-built for financial data, handles streaming updates well, and has a React wrapper (`lightweight-charts-react`). Recharts is a general-purpose charting library and is not the preferred choice for this project.
- Price flash effect: on receiving a new price, briefly apply a CSS class with background color transition, then remove it
- All API calls go to the same origin (`/api/*`) — no CORS configuration needed
- Tailwind CSS for styling with a custom dark theme

---

## 11. Docker & Deployment

### Multi-Stage Dockerfile

```
Stage 1: Node 20 slim
  - Copy frontend/
  - Use the package manager indicated by the committed lockfile:
    - pnpm-lock.yaml -> corepack enable && pnpm install --frozen-lockfile && pnpm build
    - package-lock.json -> npm ci && npm run build
  - The frontend agent must commit exactly one lockfile before the Dockerfile is finalized

Stage 2: Python 3.12 slim
  - Install uv
  - WORKDIR /app
  - Copy backend/ to /app/backend/
  - Run uv sync from /app/backend/ during build (install Python dependencies from lockfile)
  - Copy frontend build output into a static/ directory
  - Keep /app as the runtime working directory
  - Expose port 8000
  - CMD: uvicorn serving FastAPI app
```

FastAPI serves the static frontend files and all API routes on port 8000.

### Container Filesystem Contract

- Runtime working directory: `/app`
- Backend project path: `/app/backend`
- Static frontend output path served by FastAPI: `/app/static`
- SQLite database path: `/app/db/finally.db`
- Docker volume/bind mount target: `/app/db`

The backend must not depend on the process being launched from `/app/backend` to find the SQLite database. It should use an explicit database path, defaulting to `/app/db/finally.db` in the container and `db/finally.db` for local development from the repository root. If the backend introduces a `DATABASE_PATH` environment variable, `/app/db/finally.db` remains the container default.

### Docker Volume

The SQLite database persists via a bind mount from the project root's `db/` directory:

```bash
docker run -v $(pwd)/db:/app/db -p 8000:8000 --env-file .env finally
```

The bind mount is used so students can inspect the SQLite file directly on their host machine with any SQLite viewer. The backend writes `db/finally.db` to this path. The named volume approach (`finally-data:/app/db`) is equivalent but opaque — use the bind mount as the canonical quick-start command.

### Start/Stop Scripts

**`scripts/start_mac.sh`** (macOS/Linux):
- Builds the Docker image if not already built (or if `--build` flag passed)
- Runs the container with the volume mount, port mapping, and `.env` file
- Prints the URL to access the app
- Optionally opens the browser

**`scripts/stop_mac.sh`** (macOS/Linux):
- Stops and removes the running container
- Does NOT remove the volume (data persists)

**`scripts/start_windows.ps1`** / **`scripts/stop_windows.ps1`**: PowerShell equivalents for Windows.

All scripts should be idempotent — safe to run multiple times.

### Optional Cloud Deployment

The container is designed to deploy to AWS App Runner, Render, or any container platform. A Terraform configuration for App Runner may be provided in a `deploy/` directory as a stretch goal, but is not part of the core build.

---

## 12. Testing Strategy

### Unit Tests (within `frontend/` and `backend/`)

**Backend (pytest)**:
- Market data: simulator generates valid prices, GBM math is correct, Massive API response parsing works, both implementations conform to the abstract interface
- Portfolio: trade execution logic, P&L calculations, edge cases (selling more than owned, buying with insufficient cash, selling at a loss)
- LLM: structured output parsing handles all valid schemas, graceful handling of malformed responses, trade validation within chat flow
- API routes: correct status codes, response shapes, error handling

**Frontend (React Testing Library or similar)**:
- Component rendering with mock data
- Price flash animation triggers correctly on price changes
- Watchlist CRUD operations
- Portfolio display calculations
- Chat message rendering and loading state

### E2E Tests (in `test/`)

**Infrastructure**: A separate `docker-compose.test.yml` in `test/` that spins up the app container plus a Playwright container. This keeps browser dependencies out of the production image.

**Environment**: Tests run with `LLM_MOCK=true` by default for speed and determinism.

**Key Scenarios**:
- Fresh start: default watchlist appears, $10k balance shown, prices are streaming
- Add and remove a ticker from the watchlist
- Buy shares: cash decreases, position appears, portfolio updates
- Sell shares: cash increases, position updates or disappears
- Portfolio visualization: treemap renders with correct rectangle sizes and P&L colors
- AI chat (mocked): send a message, receive a response, trade execution appears inline
- SSE resilience: the frontend's `EventSource` reconnection is handled automatically by the browser. The E2E suite does **not** test SSE disconnect/reconnect directly — cover that behavior with unit tests instead. Playwright focuses on visible user-facing workflows only.

---

## 13. Documentation Review — Resolved

All items from the review have been incorporated into the document. Summary of changes:

| # | Item | Resolution |
|---|------|------------|
| 1 | OpenRouter API key absent at startup | Section 5: chat panel is disabled (grayed out) when key is absent; no crash, no mock fallback auto-enabled |
| 2 | Massive naming clarification | Section 5: added inline note that Massive is the Polygon.io Python client |
| 3 | Database initialization timing | Section 7 + Key Boundaries: changed to startup initialization; clearer for health checks |
| 4 | API response contracts missing | Section 8: added full response schemas for all endpoints |
| 5 | Trade validation rules | Section 8: added Trade Validation Rules subsection (fractional shares, no short selling, position cleanup, cash check, partial fills) |
| 6 | Market hours behavior | Section 6 (Massive): last-known price shown, no "market closed" UI state |
| 7 | Watchlist/stream scope | Section 6 (SSE): removing a ticker stops SSE events for it; backend continues generating data for future multi-user scenarios |
| 8 | Portfolio snapshots retention | Section 7: every 60s, initial $10k seed snapshot at startup, 24-hour pruning |
| 9 | LLM auto-execution audit trail | Section 9: partial success allowed, all attempted actions (success + failure) stored in `chat_messages.actions` |
| 10 | Frontend charting choice | Section 10: Lightweight Charts (TradingView) is the preferred/default library |
| 11 | Docker volume wording | Section 11: bind mount `$(pwd)/db:/app/db` is the canonical command; named volume alternative noted |
| 12 | Simulator + mock LLM as zero-config default | Not adopted: chat panel is disabled without a key rather than silently mocking. This is clearer for users. |
| 13 | Defer real Massive polling | Not adopted: simulator is already default; Massive is clearly optional |
| 14 | Start with one portfolio visualization | Section 10: added note to implement positions table + one visualization (treemap recommended) first |
| 15 | Use startup DB initialization | Adopted in #3 above |
| 16 | Standardize timestamps/money precision | Section 5: added Global Conventions block |
| 17 | Keep E2E focused on user flows | Section 12: removed SSE reconnect from E2E scenarios; covered by unit tests |
| 18 | Dockerfile build tool | Section 11: Dockerfile must use the package manager indicated by the committed frontend lockfile; no frontend lockfile exists yet |
| 19 | Container working directory | Section 11: runtime `WORKDIR` is `/app`, backend lives at `/app/backend`, SQLite lives at `/app/db/finally.db` |
