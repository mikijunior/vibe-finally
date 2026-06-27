---
phase: 04-frontend-docker-testing
plan: 01
subsystem: frontend
tags: [nextjs, react, tailwind-v4, zustand, lightweight-charts, swr, sse, eventsource, typescript]
status: complete

# Phase 4 Plan 1: Frontend Setup + Watchlist + Main Chart — Summary

# Dependency graph
requires:
  - phase: 01-database-foundation
    provides: SQLite schema with watchlist table seeded with 10 default tickers
  - phase: 02-backend-api-sse-streaming
    provides: /api/watchlist (GET/POST/DELETE), /api/stream/prices (SSE),
      Pydantic schemas, thread-safe PriceCache
provides:
  - Scaffolded Next.js 15.5.19 frontend at frontend/ with TypeScript, Tailwind v4
    (`@theme` CSS-first config), App Router, src/ layout, and static export
    (`output: 'export'`) ready to be mounted by FastAPI in 04-03
  - Locked dependency stack (next@15, react@19, zustand@5, lightweight-charts@5.2.0,
    swr@2, clsx, lucide-react, prettier, prettier-plugin-tailwindcss)
  - Typed API client (fetch wrappers) for all REST endpoints with backend `detail`
    error extraction
  - Zustand price store with sparkline buffers + direction tracking, fed by a
    singleton EventSource that auto-reconnects via the server's `retry: 1000` SSE
  - SWR-backed `useWatchlist` + Zustand `useSelectedTicker` hooks
  - WatchlistPanel with inline add/remove and click-to-select rows
  - Sparkline (canvas mini-chart) and MainChart (480px Lightweight Charts
    areaSeries) both using `series.update()` for live appends
  - PriceCell with 500ms green/red flash animation on direction change
  - Dashboard layout composing header placeholder, watchlist sidebar, main
    chart, and footer placeholder; placeholders reserve space for 04-02
    portfolio/chat components
affects:
  - phase 04-02 (consumes usePortfolio/usePortfolioHistory stubs, expands layout)
  - phase 04-03 (FastAPI mounts frontend/out/ as static files)

# Tech tracking
tech-stack:
  added:
    - next@15.5.19 + react@19.2.7 + react-dom@19.2.7 (pinned from create-next-app default)
    - tailwindcss@^4 + @tailwindcss/postcss@^4 (CSS-first `@theme` config)
    - zustand@^5 (price + selected-ticker stores)
    - lightweight-charts@^5.2.0 (canvas-based real-time charts)
    - swr@^2 (data fetching/caching for watchlist + portfolio)
    - clsx@^2.1.1 (className composition)
    - lucide-react@^1.21.0 (icons)
    - prettier@^3.9.0 + prettier-plugin-tailwindcss@^0.6.14 (formatting)
    - eslint@^8 (downgraded from v9 because eslint-config-next@15 ships legacy
      module-style config; flat config produced circular-structure errors)
  patterns:
    - Singleton EventSource managed at module scope; subscribers increment a
      refcount and a custom DOM event (`finally:price-status`) propagates
      ConnectionStatus updates without prop drilling
    - SSE payload parsed as `Record<string, PriceUpdate>` then dispatched to
      `bulkUpdate` (single store transaction per tick)
    - Rolling sparkline buffer capped at 60 points to bound memory; live updates
      skip duplicate timestamps to satisfy lightweight-charts' monotonic-time
      requirement
    - `outputFileTracingRoot` set to `..` in `next.config.ts` so Next 15 does not
      infer the project root from the wrong `package-lock.json` when the parent
      repo hosts multiple lockfiles
    - `tailwind v4 @theme { ... }` instead of `tailwind.config.ts` (CSS-first
      config is the recommended v4 pattern; falls back only if the installed
      v4 still requires a config file)
    - `<html lang="en" className="dark">` + `color-scheme: dark` on `html` for
      native dark scrollbars/forms without a Next `ThemeProvider`

key-files:
  created:
    - frontend/package.json (locked deps + scripts)
    - frontend/next.config.ts (output: 'export', trailingSlash: false,
      images.unoptimized, outputFileTracingRoot)
    - frontend/tsconfig.json (paths `@/*` -> `./src/*`)
    - frontend/eslint.config.mjs (initial scaffold, later replaced)
    - frontend/.eslintrc.json (final legacy config; extends next/core-web-vitals
      and next/typescript)
    - frontend/.prettierrc (semi + double quotes + tailwindcss plugin)
    - frontend/.prettierignore
    - frontend/postcss.config.mjs (@tailwindcss/postcss)
    - frontend/.gitignore (Next.js scaffold defaults)
    - frontend/src/app/layout.tsx (html dark, body with PriceStreamProvider)
    - frontend/src/app/page.tsx (dashboard grid composition)
    - frontend/src/app/globals.css (@theme tokens, dark base)
    - frontend/src/app/favicon.ico (Next.js default)
    - frontend/src/lib/types.ts (all backend Pydantic schema mirrors)
    - frontend/src/lib/api.ts (fetch wrappers + ApiError)
    - frontend/src/lib/format.ts (dollar/percent/quantity formatters)
    - frontend/src/lib/store.ts (Zustand price store + sparkline buffer)
    - frontend/src/lib/price-stream.ts (singleton EventSource hook)
    - frontend/src/lib/hooks/useWatchlist.ts (SWR wrapper)
    - frontend/src/lib/hooks/useSelectedTicker.ts (Zustand selection store)
    - frontend/src/lib/hooks/usePortfolio.ts (SWR stubs for 04-02)
    - frontend/src/components/PriceStreamProvider.tsx (root SSE mount)
    - frontend/src/components/PriceCell.tsx (flash animations)
    - frontend/src/components/Sparkline.tsx (Lightweight Charts mini-chart)
    - frontend/src/components/WatchlistPanel.tsx (CRUD + click-to-select)
    - frontend/src/components/MainChart.tsx (large areaSeries chart)
    - frontend/src/styles/flash.css (500ms keyframes)
    - frontend/public/* (Next.js default SVG/ico assets)
  modified:
    - .gitignore (added frontend/node_modules/, frontend/.next/, frontend/out/,
      frontend/.turbo/; re-included frontend/src/lib/ via !-prefix since the
      Python lib/ rule was ignoring the TS source folder)
    - frontend/package.json (initially scaffolded with next@16, lucide-react@1.x;
      pinned to next@15, react@19 and force-installed eslint-config-next@15.5.19;
      added prettier dev deps; legacy scripts preserved)

# Decisions

1. **Next.js 15 (not 16)** — create-next-app@latest installed Next 16.2.9 by
   default; pinned down to next@15.5.19 + react@19.2.7 + react-dom@19.2.7 to
   match the project's stack contract and ecosystem compatibility with
   eslint-config-next 15.
2. **ESLint legacy config + ESLint v8** — eslint-config-next@15.5.19 ships
   legacy module-style config. ESLint v9 flat config produced "Converting
   circular structure to JSON" errors when FlatCompat tried to wrap the legacy
   module. Solved by downgrading eslint to v8 and using a plain `.eslintrc.json`
   with `extends: ["next/core-web-vitals", "next/typescript"]`. This avoids
   the v9 migration churn for now; can revisit when eslint-config-next ships
   flat config in v16+.
3. **Output tracing root** — Next 15 inferred the workspace root from the parent
   repo's package-lock.json and complained about "multiple lockfiles". Setting
   `outputFileTracingRoot: path.join(__dirname, "..")` in `next.config.ts`
   silences the warning and lets the static export resolve correctly. A
   stray `package.json` / `node_modules` at the project root (left by an earlier
   `npm install` running from cwd=/Users/mijunior/vibecode/finally) was deleted
   to remove the source of the warning.
4. **Module-level EventSource singleton** — implemented in price-stream.ts so
   React StrictMode double-mounts and hot reloads don't open parallel
   connections. A custom DOM event (`finally:price-status`) bridges readyState
   changes to React subscribers without prop drilling.
5. **UTCTimestamp handling** — Lightweight Charts requires strictly
   non-decreasing timestamps. Synthesized monotonic times for sparkline seeds
   (anchored to `now - length`) and skipped updates that would collide with
   `lastTimeRef`, per TradingView guidance.
6. **Tailwind v4 CSS-first config** — used `@theme { ... }` block in
   globals.css with all 8 project color tokens. No `tailwind.config.ts` was
   created; the v4.3 docs mark the JS config as deprecated.
7. **Header/footer placeholders** — the dashboard layout reserves header
   (portfolio total value + cash + status dot) and footer (heatmap + P&L +
   positions + trade bar + chat) regions with copy indicating 04-02 will fill
   them. This keeps the grid stable across plans.

# Deviations from Plan

## Auto-fixed Issues

**1. [Rule 3 - Blocking] Pinned Next.js to v15 after create-next-app installed v16**
- **Found during:** Task 1
- **Issue:** create-next-app@latest default installed next@16.2.9 despite the
  plan specifying Next.js 15.x; would have caused an ecosystem mismatch with
  eslint-config-next 15, lucide-react v1, and React 19 in the project contract.
- **Fix:** `npm install next@15 react@19 react-dom@19` then rewrote
  `package.json` to pin `eslint-config-next@^15.5.19`, then
  `rm -rf node_modules package-lock.json && npm install` to regenerate the
  lockfile from the corrected manifest.
- **Files modified:** frontend/package.json, frontend/package-lock.json
- **Commit:** 8b8359b

**2. [Rule 1 - Bug] Lightweight Charts v5 API change: `addAreaSeries` -> `addSeries(AreaSeries, ...)`**
- **Found during:** Task 3 build
- **Issue:** `chart.addAreaSeries({...})` is no longer available on `IChartApi`
  in v5; the new API is `chart.addSeries(AreaSeries, {...})` (the series
  definitions are exported as symbols and passed in).
- **Fix:** Updated Sparkline.tsx and MainChart.tsx to import `AreaSeries` and
  call `chart.addSeries(AreaSeries, {...})`.
- **Files modified:** frontend/src/components/Sparkline.tsx, frontend/src/components/MainChart.tsx
- **Commit:** 3f00d22

**3. [Rule 1 - Bug] `UTCTimestamp` branded type literal mismatch**
- **Found during:** Task 3 build
- **Issue:** `let cursor: UTCTimestamp = 0` failed type-check because
  `UTCTimestamp` is a branded type (`{ [Symbol.species]: "UTCTimestamp" }`)
  and `0` is a plain `number`. Same issue for `lastTimeRef.current ?? 0` in
  Sparkline.
- **Fix:** Cast literals to `as UTCTimestamp` at the cursor initialisation site.
- **Files modified:** frontend/src/components/Sparkline.tsx, frontend/src/components/MainChart.tsx
- **Commit:** 3f00d22

**4. [Rule 3 - Blocking] Switched ESLint from v9 flat config to v8 + legacy `.eslintrc.json`**
- **Found during:** Task 3 build
- **Issue:** Next 15's bundled eslint-config-next ships legacy module-style
  config; wrapping it with `@eslint/eslintrc` `FlatCompat` produced
  `TypeError: Converting circular structure to JSON` from the plugin graph
  validator. The plan acceptance criterion requires `npx eslint src/ --max-warnings 0`
  to exit 0.
- **Fix:** Downgraded `eslint` to v8 (last major with legacy config support)
  and replaced the flat `eslint.config.mjs` with a `.eslintrc.json` that
  extends `next/core-web-vitals` and `next/typescript` directly. Both
  `npx tsc --noEmit` and `npx eslint src/ --max-warnings 0` now exit 0.
- **Files modified:** frontend/package.json, frontend/eslint.config.mjs (deleted),
  frontend/.eslintrc.json (created)
- **Commit:** 3f00d22

**5. [Rule 3 - Blocking] Root `.gitignore` `lib/` rule blocked staging `frontend/src/lib/`**
- **Found during:** Task 2 commit
- **Issue:** Python's stock `.gitignore` has a top-level `lib/` entry
  (Distribution/packaging) that matches anywhere in the tree; `git add` refused
  to stage `frontend/src/lib/` with the hint "The following paths are ignored by
  one of your .gitignore files".
- **Fix:** Added `!frontend/src/lib/` re-include rule right after the `lib/` /
  `lib64/` lines in `.gitignore`.
- **Files modified:** .gitignore
- **Commit:** 5d68943

## Auth gates
None.

# Verification

- `cd frontend && npm run build` exits 0 and produces `frontend/out/index.html`
  + `frontend/out/_next/` static assets
- `cd frontend && npx tsc --noEmit` exits 0 (no TypeScript errors)
- `cd frontend && npx eslint src/ --max-warnings 0` exits 0 (no lint errors)
- `cd backend && uv run --extra dev pytest -q` -> **194 passed** (no regressions)
- The static export's HTML payload renders the FinAlly dashboard with header,
  watchlist loading state, "Select a ticker" chart placeholder, and footer
  placeholder. Tailwind v4 theme tokens are applied (e.g. `text-accent-yellow`,
  `bg-bg-elevated`, `border-border-muted`).

# Requirements covered

FE-01..FE-05: dashboard layout, live price stream, click-to-select chart,
add/remove watchlist, EventSource reconnect -> implemented.
WL-01..WL-06: 10 default tickers render, live updates with flash, sparkline
accumulation, click-to-select, inline add/remove, EventSource retry -> implemented.
CH-01..CH-04: chat panel surface area reserved as a footer placeholder for 04-02;
the data plumbing (api.ts sendChat, types ChatEndpointResponse) is already in
place so 04-02 can drop in the panel without touching the network layer.

# Known Stubs

- The header bar shows a static "Header (portfolio + status) lands in 04-02"
  message instead of live portfolio total value / cash / connection dot.
- The footer bar shows a static "Portfolio heatmap, P&L chart, positions table,
  trade bar, and chat panel land in 04-02." message instead of those components.
- usePortfolio() and usePortfolioHistory() are wired but only the SWR fetcher
  shells are exported; the consuming components land in 04-02.

These stubs are intentional plan boundaries, not blockers.

# Self-Check: PASSED

- frontend/out/index.html exists
- frontend/src/components/{WatchlistPanel,Sparkline,MainChart,PriceCell}.tsx all exist
- frontend/src/lib/{api,types,store,price-stream,format}.ts all exist
- frontend/src/components/PriceStreamProvider.tsx wraps children in src/app/layout.tsx
- Commits 8b8359b, 5d68943, 3f00d22 all present in git log