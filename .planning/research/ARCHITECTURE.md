# Architecture Research

**Domain:** AI-Powered Trading Workstation
**Researched:** 2026-06-26
**Confidence:** HIGH

## Standard Architecture

### System Overview

```
┌─────────────────────────────────────────────────────────────────────┐
│                         Docker Container (port 8000)                 │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  ┌─────────────────────────── FASTAPI ──────────────────────────┐   │
│  │                                                            │   │
│  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────────┐  │   │
│  │  │  REST API    │  │  SSE Stream   │  │  Static Files   │  │   │
│  │  │  /api/*      │  │  /api/stream/* │  │  /*             │  │   │
│  │  └──────┬───────┘  └───────┬──────┘  └──────────────────┘  │   │
│  │         │                   │                               │   │
│  │  ┌──────┴───────────────────┴───────────────────────────┐   │   │
│  │  │              SERVICE LAYER                            │   │   │
│  │  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐   │   │   │
│  │  │  │ Portfolio   │  │ Watchlist   │  │ Chat        │   │   │   │
│  │  │  │ Service     │  │ Service     │  │ Service     │   │   │   │
│  │  │  └──────┬──────┘  └──────┬──────┘  └──────┬──────┘   │   │   │
│  │  └─────────┼─────────────────┼────────────────┼──────────┘   │   │
│  │            │                 │                │               │   │
│  │  ┌─────────┴─────────────────┴────────────────┴───────────┐   │   │
│  │  │                    DATA ACCESS LAYER                    │   │   │
│  │  │    ┌─────────────┐  ┌─────────────┐  ┌─────────────┐   │   │   │
│  │  │    │ SQLite DB   │  │ Price Cache │  │ LLM Client  │   │   │   │
│  │  │    │ (finally.db)│  │ (in-memory) │  │ (LiteLLM)   │   │   │   │
│  │  │    └─────────────┘  └──────┬──────┘  └─────────────┘   │   │   │
│  │  └───────────────────────────┼───────────────────────────┘   │   │
│  │                              │                                 │   │
│  │  ┌───────────────────────────┴───────────────────────────┐   │   │
│  │  │              MARKET DATA LAYER                         │   │   │
│  │  │  ┌─────────────────┐    ┌─────────────────────────┐   │   │   │
│  │  │  │ Market Simulator │    │ Massive API Client      │   │   │   │
│  │  │  │ (GBM, 500ms)     │    │ (REST polling)          │   │   │   │
│  │  │  └────────┬────────┘    └───────────┬─────────────┘   │   │   │
│  │  │           │                         │                 │   │   │
│  │  │           └───────────┬─────────────┘                 │   │   │
│  │  │                       ▼                               │   │   │
│  │  │              ┌────────────────┐                       │   │   │
│  │  │              │  Price Cache   │ ◄── Background task   │   │   │
│  │  │              │  (in-memory)   │                       │   │   │
│  │  │              └────────────────┘                       │   │   │
│  │  └─────────────────────────────────────────────────────────┘   │   │
│  └───────────────────────────────────────────────────────────────┘   │
│                                                                      │
└─────────────────────────────────────────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────────┐
│                         Next.js Frontend (Browser)                   │
│                                                                      │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────────────┐   │
│  │ EventSource  │  │  REST Client │  │  UI Components          │   │
│  │ (SSE listener)│  │  (fetch API) │  │  (React/TS)             │   │
│  └──────┬───────┘  └──────┬───────┘  └───────────┬──────────────┘   │
│         │                 │                       │                  │
│  ┌──────┴─────────────────┴───────────────────────┴──────────────┐  │
│  │                    State Management (React Context/Zustand)    │  │
│  └──────────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────┘
```

### Component Responsibilities

| Component | Responsibility | Typical Implementation |
|-----------|----------------|----------------------|
| **Price Cache** | In-memory store of latest/previous prices per ticker; written by market data task, read by SSE and REST | Python dict with threading.Lock |
| **Market Simulator** | Generates realistic price movements via GBM; runs as background task writing to cache | Background asyncio task |
| **Massive API Client** | Polls Polygon.io REST API; parses response, writes to same cache interface | httpx async client with polling interval |
| **Portfolio Service** | Executes trades, computes P&L, manages positions/balances | Business logic layer over data access |
| **Watchlist Service** | CRUD operations for user watchlist | Business logic layer |
| **Chat Service** | Constructs LLM prompts with context, calls LiteLLM, parses structured output, auto-executes actions | LLM integration + business logic |
| **SSE Manager** | Holds async generators for connected clients; broadcasts price cache updates | FastAPI StreamingResponse with background task |
| **REST Handlers** | HTTP request/response handling, input validation, error formatting | FastAPI router decorators |
| **Frontend State** | Reactive state for prices, portfolio, chat messages; SSE subscription management | React hooks + Context or Zustand |
| **SQLite Database** | Persistent storage for user data, positions, trades, history | Python sqlite3 or SQLModel/aiosqlite |

## Recommended Project Structure

### Backend (`backend/`)

```
backend/
├── pyproject.toml              # uv project definition
├── src/
│   └── finally/
│       ├── __init__.py
│       ├── main.py            # FastAPI app entry, routes, lifespan
│       ├── config.py          # Environment variable parsing
│       ├── dependencies.py   # FastAPI dependencies (DB session, etc.)
│       ├── db/
│       │   ├── __init__.py
│       │   ├── connection.py # SQLite connection management
│       │   ├── schema.sql    # Table creation DDL
│       │   ├── seed.py       # Default data seeding
│       │   └── repositories/ # Data access objects
│       │       ├── __init__.py
│       │       ├── user.py
│       │       ├── watchlist.py
│       │       ├── position.py
│       │       ├── trade.py
│       │       └── snapshot.py
│       ├── market/
│       │   ├── __init__.py
│       │   ├── interface.py  # Abstract interface both impls conform to
│       │   ├── simulator.py  # GBM-based market simulator
│       │   ├── massive.py    # Massive API REST client
│       │   ├── cache.py      # In-memory price cache (shared)
│       │   └── polling.py    # Background polling task
│       ├── services/
│       │   ├── __init__.py
│       │   ├── portfolio.py  # Trade execution, P&L calc
│       │   ├── watchlist.py # Watchlist CRUD
│       │   └── chat.py      # LLM integration
│       ├── api/
│       │   ├── __init__.py
│       │   ├── portfolio.py  # Portfolio endpoints
│       │   ├── watchlist.py  # Watchlist endpoints
│       │   ├── chat.py       # Chat endpoint
│       │   ├── stream.py     # SSE endpoint
│       │   └── health.py    # Health check
│       └── llm/
│           ├── __init__.py
│           ├── client.py     # LiteLLM wrapper
│           └── prompts.py    # System prompts, schema definitions
└── tests/
    ├── __init__.py
    ├── conftest.py
    ├── test_market/
    ├── test_portfolio/
    └── test_api/
```

### Frontend (`frontend/`)

```
frontend/
├── package.json
├── next.config.ts
├── src/
│   ├── app/
│   │   ├── layout.tsx
│   │   ├── page.tsx           # Main SPA entry
│   │   └── globals.css
│   ├── components/
│   │   ├── Header.tsx
│   │   ├── Watchlist/
│   │   │   ├── WatchlistGrid.tsx
│   │   │   ├── TickerCard.tsx
│   │   │   └── Sparkline.tsx
│   │   ├── Chart/
│   │   │   └── MainChart.tsx
│   │   ├── Portfolio/
│   │   │   ├── Heatmap.tsx
│   │   │   ├── PnlChart.tsx
│   │   │   └── PositionsTable.tsx
│   │   ├── Trade/
│   │   │   └── TradeBar.tsx
│   │   └── Chat/
│   │       ├── ChatPanel.tsx
│   │       └── MessageBubble.tsx
│   ├── hooks/
│   │   ├── usePriceStream.ts   # SSE EventSource management
│   │   ├── usePortfolio.ts
│   │   ├── useWatchlist.ts
│   │   └── useChat.ts
│   ├── lib/
│   │   ├── api.ts             # REST API client
│   │   └── types.ts          # Shared TypeScript types
│   └── stores/
│       └── priceStore.ts     # Zustand or React Context for price state
```

### Structure Rationale

- **`backend/src/finally/market/`:** Market data is isolated because it has two implementations (simulator/Massive) sharing a common interface and cache. Keeping it separate makes swapping implementations frictionless.
- **`backend/src/finally/db/repositories/`:** Data access objects separate business logic from persistence. Enables easy testing with in-memory mocks.
- **`backend/src/finally/services/`:** Business logic lives here, independent of HTTP layer. This allows portfolio/chat logic to be tested without FastAPI overhead.
- **`frontend/src/hooks/`:** Custom hooks encapsulate SSE subscription and API call logic, keeping components declarative. Each hook owns its data fetching lifecycle.
- **`frontend/src/lib/api.ts`:** Single API client module prevents scattered `fetch` calls across components.

## Architectural Patterns

### Pattern 1: Shared In-Memory Price Cache

**What:** A thread-safe Python dict (or dataclass with a Lock) holds the latest and previous prices for all tickers. The market data background task writes to it; SSE reads from it.

**When to use:** When multiple async tasks need to access the same mutable state, or when one task produces data consumed by many subscribers.

**Trade-offs:**
- Pro: Zero network overhead for inter-component communication; extremely fast read
- Pro: SSE broadcast can read cache at any interval without coordinating with producers
- Con: State is not persisted; container restart resets prices (acceptable for a simulator)
- Con: Single-process only; would need redesign for multi-container deployment

**Example:**
```python
# backend/src/finally/market/cache.py
from dataclasses import dataclass, field
from threading import Lock
from typing import Optional

@dataclass
class PriceCache:
    _lock: Lock = field(default_factory=Lock)
    _prices: dict[str, dict] = field(default_factory=dict)  # ticker -> {price, prev, ts}

    def update(self, ticker: str, price: float, prev: float, ts: str) -> None:
        with self._lock:
            self._prices[ticker] = {"price": price, "prev": prev, "timestamp": ts}

    def get(self, ticker: str) -> Optional[dict]:
        with self._lock:
            return self._prices.get(ticker)

    def get_all(self) -> dict[str, dict]:
        with self._lock:
            return dict(self._prices)
```

### Pattern 2: Abstract Market Data Interface

**What:** Both the simulator and Massive API client implement the same abstract interface (`MarketDataSource`). The rest of the application is agnostic to which is active.

**When to use:** When you have multiple implementations selectable at runtime via environment variable.

**Trade-offs:**
- Pro: Seamless swap between simulator and real data without changing SSE or service code
- Pro: Easy to add new data sources (e.g., Yahoo Finance, Alpha Vantage)
- Con: Interface must be stable; adding methods breaks all implementations

**Example:**
```python
# backend/src/finally/market/interface.py
from abc import ABC, abstractmethod

class MarketDataSource(ABC):
    @abstractmethod
    async def get_price(self, ticker: str) -> float: ...

    @abstractmethod
    async def get_prices(self, tickers: list[str]) -> dict[str, float]: ...
```

### Pattern 3: SSE Streaming via FastAPI StreamingResponse

**What:** Long-lived HTTP connection using `text/event-stream`. FastAPI yields events from an async generator that reads the price cache.

**When to use:** When the server needs to push updates to the client without WebSocket complexity.

**Trade-offs:**
- Pro: Built-in browser EventSource reconnection; simple HTTP infrastructure
- Pro: Works through most proxies and firewalls
- Con: One-way only; client cannot send binary control messages without polling
- Con: Each connected client holds a server thread/coroutine

**Example:**
```python
# backend/src/finally/api/stream.py
from fastapi import APIRouter
from fastapi.responses import StreamingResponse
import asyncio
import json

router = APIRouter()

async def price_event_generator():
    cache = price_cache  # shared in-memory cache
    while True:
        data = cache.get_all()
        for ticker, info in data.items():
            event = f"data: {json.dumps({'ticker': ticker, **info})}\n\n"
            yield event
        await asyncio.sleep(0.5)

@router.get("/api/stream/prices")
async def stream_prices():
    return StreamingResponse(price_event_generator(), media_type="text/event-stream")
```

### Pattern 4: Background Task with Lifespan

**What:** FastAPI lifespan events start/stop the market data background task (simulator or Massive poller). The price cache is created at startup and injected as a shared dependency.

**When to use:** For any long-running task that should run for the lifetime of the application.

**Trade-offs:**
- Pro: Task starts automatically when container starts; stops cleanly on shutdown
- Pro: Cache is available to all requests via dependency injection
- Con: Requires careful async/shutdown handling to avoid orphaned tasks

## Data Flow

### Request Flow

```
[User clicks Buy]
    │
    ▼
[Frontend TradeBar component]
    │ POST /api/portfolio/trade {ticker, quantity, side}
    ▼
[FastAPI router: portfolio.py]
    │ validates input
    ▼
[Portfolio Service]
    │ loads position from DB, checks cash/shares
    │ executes trade: updates cash, creates/updates position
    ▼
[Trade Repository]
    │ INSERT INTO trades ...
    │ INSERT INTO portfolio_snapshots (immediate after trade)
    ▼
[SQLite Database]
    │
    ▼
[Response: {success, position, cash_balance}]
    │
    ▼
[Frontend updates positions table + cash display]
```

### SSE Streaming Flow

```
[Market Simulator Background Task] ──writes──► [Price Cache]
                                              │
                                              │ reads every ~500ms
                                              ▼
                                    [SSE Event Loop]
                                              │
                                              │ yields SSE events
                                              ▼
                                    [StreamingResponse]
                                              │
                                              │ HTTP 200, text/event-stream
                                              ▼
                              [Browser EventSource API]
                                              │
                                              │ dispatches events
                                              ▼
                              [Frontend usePriceStream hook]
                                              │
                                              │ updates price state
                                              ▼
                              [React components re-render]
```

### Chat Flow

```
[User sends chat message]
    │
    ▼
[Frontend ChatPanel]
    │ POST /api/chat {message}
    ▼
[FastAPI router: chat.py]
    ▼
[Chat Service]
    │ 1. Loads portfolio context (cash, positions, watchlist, prices)
    │ 2. Loads chat history from DB
    │ 3. Builds prompt with system message + context + history + user message
    ▼
[LiteLLM Client]
    │ calls OpenRouter API with structured output schema
    ▼
[LLM Response: {message, trades[], watchlist_changes[]}]
    │
    ├──────────────────────────────────────┐
    ▼                                      ▼
[Auto-execute trades]              [Auto-execute watchlist changes]
    │                                      │
    ▼                                      ▼
[Portfolio Service]                [Watchlist Service]
    │                                      │
    ▼                                      ▼
[Database updates]                  [Database updates]
    │
    ▼
[Store chat message + actions in chat_messages table]
    │
    ▼
[Return response to frontend]
```

### Key Data Flows

1. **Price streaming:** Market data task (simulator) writes to price cache every 500ms. SSE endpoint reads all prices from cache and formats as SSE events. Browser EventSource receives events and updates React state.

2. **Trade execution:** REST POST to `/api/portfolio/trade`. Portfolio service validates (cash/shares), updates SQLite positions + cash balance, logs trade, creates immediate portfolio snapshot, returns updated state.

3. **Chat with AI:** REST POST to `/api/chat`. Chat service assembles context (portfolio + history), calls LLM with structured output schema, auto-executes any requested trades/watchlist changes, stores message in DB, returns complete response.

4. **Portfolio snapshots:** Background task records portfolio total_value every 30 seconds to `portfolio_snapshots`. Frontend fetches history for P&L chart.

## Scaling Considerations

| Scale | Architecture Adjustments |
|-------|--------------------------|
| 0-100 users (single container) | Current design is optimal. SQLite handles thousands of reads/writes per second. Price cache is in-process. |
| 100-1,000 users | Add connection pooling for SQLite (already aiosqlite). SSE connections scale with asyncio; monitor open file limits. Consider moving price cache to Redis. |
| 1,000-10,000 users | Redis pub/sub for price cache across multiple containers. Consider moving to PostgreSQL. Restrict SSE to user-specific tickers. |
| 10,000+ users | Multi-container FastAPI with Redis. LLM response caching. Horizontal scaling of static frontend via CDN. |

### Scaling Priorities

1. **First bottleneck: SSE connections.** Each browser tab holds one SSE connection. At high concurrency, uvicorn async workers become the limit. Mitigation: increase worker count, move SSE to a separate process.

2. **Second bottleneck: SQLite writes.** Portfolio snapshots every 30s + trade logging generates write traffic. Mitigation: batch snapshot inserts, eventually move to PostgreSQL.

3. **Third bottleneck: LLM latency.** Chat responses take 1-5 seconds. Mitigation: show loading state immediately, consider caching frequent queries (e.g., "analyze my portfolio").

## Anti-Patterns

### Anti-Pattern 1: Blocking the Event Loop

**What people do:** Run synchronous blocking code (e.g., `time.sleep`, synchronous DB calls) inside async FastAPI route handlers or background tasks.

**Why it's wrong:** Python asyncio runs on a single thread for all coroutines. Blocking calls freeze the entire event loop, stalling all SSE streams and other requests.

**Do this instead:** Always use `await` with async libraries (`aiosqlite`, `httpx.AsyncClient`). For sync-only libraries, run them in a thread pool via `asyncio.to_thread()` or `run_in_executor()`.

### Anti-Pattern 2: Storing Price State in REST Response Handlers

**What people do:** Calling the market data source (or recalculating prices) inside a REST endpoint handler to build a response.

**Why it's wrong:** Market data changes independently of REST requests. Doing this creates race conditions and inconsistent data between SSE and REST.

**Do this instead:** Always read from the shared price cache. SSE and REST should return data from the same source for consistency.

### Anti-Pattern 3: Mixing Business Logic with HTTP Layer

**What people do:** Putting trade validation, P&L calculation, or LLM prompting directly inside FastAPI route handlers.

**Why it's wrong:** Route handlers become bloated, hard to test, and impossible to reuse. Business logic should be callable from tests or future API versions without HTTP overhead.

**Do this instead:** Keep route handlers thin (parse input, call service, format response). All business logic lives in `services/`. Route handlers should be ~10 lines.

## Integration Points

### External Services

| Service | Integration Pattern | Notes |
|---------|---------------------|-------|
| **Massive API (Polygon.io)** | REST polling via `httpx.AsyncClient`, environment-variable driven | Poll interval: 15s (free tier), 2-15s (paid). Response parsed into same format as simulator. |
| **OpenRouter / Cerebras** | LiteLLM client, structured JSON output schema | API key via `OPENROUTER_API_KEY`. Mock mode via `LLM_MOCK=true` for testing. |
| **LLM Structured Output** | `cerebras-inference` skill with JSON schema constraint | Trade execution requires reliable parsing; structured outputs are mandatory. |

### Internal Boundaries

| Boundary | Communication | Notes |
|----------|---------------|-------|
| **Frontend → Backend** | REST (`fetch`) + SSE (`EventSource`) | Same origin, no CORS. SSE is unidirectional server→client only. |
| **Market Layer → Cache** | Direct function call (shared memory) | Both simulator and Massive write to same cache. No queue needed in single-process model. |
| **Service Layer → Database** | Repository pattern with async SQLite | Services never touch DB directly; they call repository methods. |
| **SSE → Price Cache** | Async generator reading cache | SSE endpoint is a `StreamingResponse` yielding from a `while True` loop reading the cache every 500ms. |

## Build Order Implications

The following build order respects dependencies and enables incremental testing at each phase:

```
Phase 1: Database Foundation
├── backend/src/finally/db/schema.sql          # Define all tables
├── backend/src/finally/db/connection.py         # SQLite connection management
├── backend/src/finally/db/repositories/*        # All CRUD operations
└── backend/src/finally/db/seed.py              # Default data seeding
→ Output: Fresh container writes schema + seed on first start

Phase 2: Price Cache + Market Data
├── backend/src/finally/market/cache.py         # In-memory price cache (shared)
├── backend/src/finally/market/interface.py     # Abstract interface
├── backend/src/finally/market/simulator.py     # GBM simulator (default)
├── backend/src/finally/market/massive.py        # Massive API client (optional)
└── backend/src/finally/market/polling.py        # Background task startup
→ Output: `price_cache.get_all()` returns all ticker prices

Phase 3: REST API Layer
├── backend/src/finally/services/portfolio.py    # Trade execution, P&L
├── backend/src/finally/services/watchlist.py    # Watchlist CRUD
├── backend/src/finally/api/portfolio.py         # GET /api/portfolio, POST /trade
├── backend/src/finally/api/watchlist.py         # GET/POST/DELETE /api/watchlist
└── backend/src/finally/api/health.py           # GET /api/health
→ Output: Manual trade execution works via REST

Phase 4: SSE Streaming
├── backend/src/finally/api/stream.py            # GET /api/stream/prices
├── backend/src/finally/main.py                  # Wire lifespan (starts background task)
└── frontend/src/hooks/usePriceStream.ts         # EventSource hook
→ Output: Prices stream live in browser; flash animations work

Phase 5: LLM Integration
├── backend/src/finally/llm/client.py           # LiteLLM wrapper
├── backend/src/finally/llm/prompts.py           # System prompts + schema
├── backend/src/finally/services/chat.py         # Context assembly + action execution
├── backend/src/finally/api/chat.py             # POST /api/chat
└── backend/src/finally/db/repositories/chat.py  # chat_messages CRUD
→ Output: AI chat can analyze portfolio and execute trades

Phase 6: Frontend Visualizations
├── frontend/src/components/Portfolio/Heatmap.tsx    # Treemap
├── frontend/src/components/Portfolio/PnlChart.tsx   # Portfolio value line chart
├── frontend/src/components/Chart/MainChart.tsx      # Larger ticker chart
└── frontend/src/components/Portfolio/PositionsTable.tsx
→ Output: All portfolio visualizations render correctly

Phase 7: Docker + Scripts
├── Dockerfile (multi-stage: Node build + Python serve)
├── docker-compose.yml
├── scripts/start_mac.sh / start_windows.ps1
└── scripts/stop_mac.sh / stop_windows.ps1
→ Output: `docker run` launches complete working app

Phase 8: E2E Tests
├── test/docker-compose.test.yml
├── test/test_*.py (Playwright scenarios)
└── backend/tests/ (pytest unit tests)
→ Output: Automated verification of all key user journeys
```

**Critical path:** Phase 1 → 2 → 3 → 4 must be sequential (each builds on the previous). Phase 5 (LLM) can start after Phase 3 since it only needs REST APIs. Phase 6 (frontend visualizations) can overlap with Phase 4/5 since frontend is isolated. Phase 7 and 8 depend on everything.

## Sources

- [FastAPI Lifespan Documentation](https://fastapi.tiangolo.com/reference/fastapi/) — lifespan context for background tasks
- [MDN: Using EventSource](https://developer.mozilla.org/en-US/docs/Web/API/EventSource) — SSE client-side reconnection behavior
- [LiteLLM Structured Outputs](https://docs.litellm.ai/docs/completion/structured_outputs) — Cerebras/OpenRouter structured output invocation
- [aiosqlite async SQLite](https://github.com/psycopg/aiosqlite) — async database access pattern
- [Polygon.io Market Data API](https://polygon.io/docs) — Massive API REST endpoint patterns

---
*Architecture research for: AI-Powered Trading Workstation*
*Researched: 2026-06-26*
