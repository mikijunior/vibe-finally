---
phase: 04-frontend-docker-testing
plan: 02
subsystem: frontend
tags: [nextjs, react, tailwind-v4, zustand, swr, sse, typescript, shadcn, treemap, lightweight-charts, chat-panel]
status: complete

# Phase 4 Plan 2: Portfolio Visualizations + Trade Bar + Chat Panel — Summary

# Dependency graph
requires:
  - phase: 04-frontend-docker-testing/04-01
    provides: Locked deps, api.ts (fetch wrappers incl. executeTrade/sendChat),
      store.ts (Zustand price store + sparkline buffer), usePortfolio /
      usePortfolioHistory / useWatchlist SWR hooks, usePriceStream singleton,
      MainChart, WatchlistPanel, Sparkline, PriceCell, globals.css @theme tokens
  - phase: 02-backend-api-sse-streaming
    provides: REST endpoints (/api/portfolio, /api/portfolio/trade,
      /api/portfolio/history, /api/watchlist, /api/chat) with typed schemas
provides:
  - Header bar with live total value (recomputed on every SSE tick), cash
    balance, and SSE connection-status dot
  - PortfolioHeatmap — SVG slice-and-dice treemap sized by weight, colored
    by P&L with opacity derived from pnl_percent
  - PnLChart — Lightweight Charts areaSeries for /api/portfolio/history with
    series.update() on new snapshots
  - PositionsTable — tabular positions with live price override and P&L
    coloring
  - TradeBar — ticker + qty inputs with Buy/Sell buttons; inline error
    display for HTTP 4xx; SWR cache refresh on success
  - ChatPanel — conversation surface with role-tinted message bubbles, inline
    action chips (green/red trade, purple watchlist, red failed), pulsing
    "thinking" loader, collapsible 32px rail
  - useChat hook — session-local messages, calls sendChat, appends
    assistant message + ChatActionResult array, refreshes portfolio +
    watchlist caches on success
  - Local shadcn-style UI primitives (button/input/table) — no radix-ui dep
  - Composed dashboard grid: Header / Watchlist+Chart / Heatmap+PnL+Positions /
    TradeBar+Chat — replaces 04-01 placeholders
affects:
  - phase 04-03 (FastAPI mounts frontend/out/ as static files; layout is
    now complete and exportable)

# Tech tracking
tech-stack:
  added:
    - (no new deps — all built on top of 04-01's locked set:
      clsx, lightweight-charts, lucide-react, swr, zustand)
  patterns:
    - SVG slice-and-dice treemap (no library) — picked a ~50% weight split,
      alternates vertical/horizontal cuts, falls back to equal-area grid when
      all weights are zero/negative
    - Lightweight Charts areaSeries for /api/portfolio/history with strict
      monotonic-time synthesis (UTCTimestamp branded type cast on cursor) —
      mirrors the Sparkline/MainChart pattern from 04-01
    - Chip-driven action confirmations in ChatPanel — color encodes type and
      outcome (green = buy, red = sell or failed, purple = watchlist) so the
      message bubble stays scannable
    - Collapse-the-right-rail UX for ChatPanel — 32px rail with chevron toggle
      preserves full-width chart space when the user wants more room
    - Inline server-error display — TradeBar sets `error` to the ApiError's
      `.message` (`status: detail`) so the backend's structured `detail`
      string shows up unchanged next to the inputs
    - Session-local chat history — useChat starts empty; matches the v1
      product spec ("scrollable conversation history" without persistence)
      and avoids a second REST endpoint

key-files:
  created:
    - frontend/src/components/Header.tsx
    - frontend/src/components/PortfolioHeatmap.tsx
    - frontend/src/components/PnLChart.tsx
    - frontend/src/components/PositionsTable.tsx
    - frontend/src/components/TradeBar.tsx
    - frontend/src/components/ChatPanel.tsx
    - frontend/src/components/ui/button.tsx
    - frontend/src/components/ui/input.tsx
    - frontend/src/components/ui/table.tsx
    - frontend/src/lib/hooks/useChat.ts
  modified:
    - frontend/src/app/page.tsx (dashboard composition)
    - frontend/src/app/globals.css (explicit .text-pnl-up/.text-pnl-down
      utility shortcuts under @layer utilities)

# Decisions

1. **No treemap dependency** — implemented an SVG slice-and-dice layout
   inline rather than pulling in d3-hierarchy / react-d3-treemap. ~80 lines
   of code, no new dep, keeps the build small per the project's "prefer
   custom over deps" guideline. Falls back to equal-area grid for
   pathological inputs (all weights zero/negative).
2. **No shadcn CLI / radix-ui dependency** — wrote the three UI primitives
   (button / input / table) as local copy-paste components using `clsx` and
   `forwardRef`. The components live under `frontend/src/components/ui/` per
   shadcn convention so a future `components.json` swap is mechanical.
3. **ChatPanel collapse-to-rail** — added a 32px rail collapse so the user
   can reclaim horizontal space for the chart. Both chevron and chat icon
   expand the panel (target area is small but the affordance is consistent
   with IDE-style collapsible sidebars).
4. **`PositionsTable` uses an inline `<table>`** rather than the local
   `<Table>` primitives — the table needs a sticky `thead` to keep the
   column headers visible while rows scroll, and the primitive set's
   `bg-bg-elevated` header background wouldn't survive sticky positioning.
   Keeping it inline avoids adding sticky-context complications to the
   primitive API.
5. **`useChat` is session-local** — empty by default; matches the product
   spec which only requires "scrollable conversation history" without
   persistence for v1. The backend already persists every exchange to
   `chat_messages` so a future rehydration UI can replay history from a
   `GET /api/chat/history` endpoint without touching `useChat`'s API.
6. **`PortfolioHeatmap` empty-state is descriptive** — instead of a blank
   rectangle, shows "No positions yet — Use the trade bar below to open a
   position" so a new user immediately understands the workflow.
7. **`Header` total value recomputes on every SSE tick** — subscribes to
   `usePriceStore(s => s.prices)` (full map) and reduces in a `useMemo`. The
   `version` counter incremented inside `bulkUpdate` ensures the memo
   re-runs even when the same price ticks the same value twice.
8. **Auto-clear success chip in TradeBar** — fades after 1.5s so the bar
   stays focused on inputs during rapid trading.

# Deviations from Plan

## Auto-fixed Issues

**1. [Rule 1 - Bug] TableBody forwardRef body wrapped JSX returned without parens**
- **Found during:** Task 1 (first tsc check)
- **Issue:** `return <tbody .../>);` had a stray `)` after the closing tag,
  producing `TS1005: ';' expected` / `TS1128` at the `<tbody>` closing tag.
- **Fix:** Reformatted the return to wrap the JSX in parens across multiple
  lines so the trailing `)` is part of the return expression.
- **Files modified:** frontend/src/components/ui/table.tsx
- **Commit:** 070c391

**2. [Rule 1 - Bug] Unused `formatDollars` import in ChatPanel**
- **Found during:** Task 2 (eslint check)
- **Issue:** `formatDollars` was imported speculatively but the action-chip
  text uses the trade's `quantity` only (the executor doesn't return price
  in `ChatActionResult`). ESLint --max-warnings 0 flagged the unused import.
- **Fix:** Removed `formatDollars` from the import line.
- **Files modified:** frontend/src/components/ChatPanel.tsx
- **Commit:** 989c6a5

# Verification

- `cd frontend && npx tsc --noEmit` exits 0 (no TypeScript errors)
- `cd frontend && npx eslint src/ --max-warnings 0` exits 0 (no lint warnings)
- `cd frontend && npx next build` exits 0 and produces `frontend/out/index.html`
  + `frontend/out/_next/` static assets (170 kB First Load JS, route size 67.6 kB)
- `cd backend && uv run --extra dev pytest -q` -> **194 passed** (no regressions
  vs. 04-01)
- Generated `frontend/out/index.html` contains test markers for `chat-panel`,
  `header-total-value`, `pnl-chart`, `trade-buy-`, `trade-sell-`,
  `trade-ticker-`, `trade-quantity-` (the portfolio-heatmap and chat-action
  testids only appear post-mount since they're driven by client-side data).
- All 23 v1 requirements (PF-01..05, TB-01..07, CHAT-01..07, HDR-01..03) are
  implemented by these components. No requirements file edits required.

# Requirements covered

PF-01: PortfolioHeatmap renders treemap of positions -> implemented.
PF-02: Heatmap sized by weight, colored by P&L (green/red) -> implemented
  via SVG `<rect fill={color} fillOpacity={opacity}>` with opacity derived
  from |pnl_percent|.
PF-03: Heatmap empty-state placeholder -> implemented ("No positions yet").
PF-04: PnLChart renders area chart of portfolio value over time ->
  implemented via Lightweight Charts areaSeries + series.update().
PF-05: PnLChart shows "Waiting for first snapshot…" placeholder ->
  implemented; overlay shown when `snapshots.length === 0`.

TB-01: Trade bar ticker + quantity inputs -> implemented.
TB-02: Buy button executes buy market order -> implemented.
TB-03: Sell button executes sell market order -> implemented.
TB-04: Trade POSTs to /api/portfolio/trade with no confirmation dialog ->
  implemented (instant submit, no modal).
TB-05: 4xx error message displayed inline -> implemented
  (`.text-pnl-down` element under the inputs, displays `ApiError.message`
  which carries the backend's `detail`).
TB-06: Trade success clears inputs and refreshes portfolio + watchlist SWR
  caches -> implemented.
TB-07: Transient success indicator after fill -> implemented
  (`Filled buy 5 AAPL • cash $9,512.34` for 1.5s).

CHAT-01: Chat panel text input + Send button -> implemented.
CHAT-02: Loading indicator during POST /api/chat -> implemented
  (`FinAlly is thinking...` with pulsing dot).
CHAT-03: Assistant message content rendered -> implemented.
CHAT-04: Inline confirmation chips for executed trades
  ("Bought/Sold Q TICKER") -> implemented.
CHAT-05: Inline confirmation chips for executed watchlist changes
  ("+/- TICKER added/removed") -> implemented.
CHAT-06: Failed actions render red chips with server detail -> implemented.
CHAT-07: Portfolio + watchlist caches refreshed after each successful chat
  response -> implemented in useChat.

HDR-01: Header shows portfolio total value -> implemented (recomputed on
  every price tick from `cash + sum(qty * live price)`).
HDR-02: Header shows cash balance -> implemented.
HDR-03: Header shows colored connection-status dot reflecting EventSource
  readyState (green=connected, yellow=reconnecting, red=disconnected)
  -> implemented.

# Known Stubs

- `ChatActionResult` does not currently carry the executed `price` per trade
  (only `side` + `quantity`). The trade chip therefore reads
  "Bought 10 AAPL" without "@ $price". This matches the executor's current
  output schema; adding price would require extending both the
  `execute_actions` helper and the `ChatActionResult` Pydantic model. This
  is a backend follow-up, not a 04-02 frontend gap.
- Chat history is session-local; no `GET /api/chat/history` endpoint is
  implemented yet. The `chat_messages` rows are persisted for audit and
  can back a future rehydration UI.
- Trade chip in chat panel does not show "filled @ price" because the
  executor returns the post-trade `cash_balance` in the trade row only,
  not in the `actions_executed` summary. See "Known Stubs" above.

# Self-Check: PASSED

- frontend/src/components/{Header,PortfolioHeatmap,PnLChart,PositionsTable,TradeBar,ChatPanel}.tsx all exist
- frontend/src/components/ui/{button,input,table}.tsx all exist
- frontend/src/lib/hooks/useChat.ts exists
- frontend/src/app/page.tsx imports all 6 new components AND retains WatchlistPanel + MainChart
- `frontend/out/index.html` exists
- Commits 070c391, 989c6a5, 8920c70 all present in git log
