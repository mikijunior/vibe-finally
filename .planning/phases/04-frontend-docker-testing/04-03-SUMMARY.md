---
phase: 04-frontend-docker-testing
plan: 03
subsystem: deployment
tags: [docker, docker-compose, multi-stage-build, fastapi-static, playwright, e2e, ci, idempotent-scripts, bash, powershell]
status: complete

# Phase 4 Plan 3: Docker + Scripts + E2E Tests + CI — Summary

# Dependency graph
requires:
  - phase: 04-frontend-docker-testing/04-01
    provides: frontend/out/ static export built by `npm run build`
      (Lightweight Charts components, watchlist panel, SSE wiring)
  - phase: 04-frontend-docker-testing/04-02
    provides: complete dashboard with Header / Heatmap / PnLChart /
      PositionsTable / TradeBar / ChatPanel + the data-testid hooks the
      E2E specs rely on (header-connection-status, trade-ticker-input,
      chat-panel, chat-action-trade-AAPL, etc.)
  - phase: 02-backend-api-sse-streaming
    provides: REST endpoints + /api/stream/prices SSE + PriceCache;
      the TESTING=1 endpoints in main.py (cache/state, watchlist/test-add,
      watchlist/test-remove) that the reset fixture uses
  - phase: 03-llm-integration
    provides: MockLLMClient (deterministic "Mock:" response on
      `buy|sell|add|remove <ticker>`), ChatActionResult schema, executor
      that auto-applies trades — all needed for the chat E2E spec
provides:
  - Single multi-stage Dockerfile (node:20-slim -> python:3.12-slim + uv)
    that produces a self-contained image with FastAPI + frontend/out/
    + uvicorn on 0.0.0.0:8000
  - .dockerignore keeping the build context minimal (excludes .git,
    .planning, .claude, node_modules, .venv, .env, db/*.db, test/, scripts/)
  - docker-compose.yml single-service wrapper with the `finally-data`
    named volume mounted at /app/db for SQLite persistence
  - .env.example documenting OPENROUTER_API_KEY (required),
    MASSIVE_API_KEY (optional, defaults to simulator), LLM_MOCK (default
    false) — no real keys committed
  - backend/app/main.py extended with `from fastapi.staticfiles import
    StaticFiles` and `app.mount("/", StaticFiles(directory="/app/static",
    html=True))` registered AFTER all API routers (registration order
    matters in Starlette), guarded by an `os.path.isdir` check so dev
    mode (no /app/static) skips with a logged warning instead of crashing
  - scripts/start_mac.sh + scripts/stop_mac.sh: idempotent bash scripts,
    executable (`chmod +x`), `bash -n` clean, `--build` flag on start
  - scripts/start_windows.ps1 + scripts/stop_windows.ps1: idempotent
    PowerShell equivalents with `-Build` switch
  - scripts/README.md: usage for both platforms, data persistence
    notes, env var reference table
  - test/docker-compose.test.yml: app service (build from .., LLM_MOCK=true,
    TESTING=1, healthcheck) + playwright service
    (mcr.microsoft.com/playwright:v1.49.0-jammy)
  - test/playwright.config.ts (baseURL http://app:8000, chromium-only,
    retain-on-failure trace), test/package.json, test/tsconfig.json
  - test/e2e/fixtures.ts: extended test with APIRequestContext + auto
    resetWatchlist fixture using backend TESTING=1 endpoints
  - Five Playwright spec files: watchlist, trade, portfolio, chat,
    sse-resilience — exercising every requirement surface from DOCKER-01
    through DOCKER-09 and TEST-01 through TEST-03
  - test/README.md: how to run locally + what each spec covers
  - .github/workflows/e2e.yml: runs the compose suite on every PR and
    push to main; uploads playwright-report artifact on failure
affects:
  - milestone v1.0 (the entire "one Docker command" student experience
    + automated regression coverage are now real artifacts in the repo)

# Tech tracking
tech-stack:
  added:
    - node:20-slim Docker image (frontend build stage only)
    - python:3.12-slim Docker image (runtime)
    - uv==0.5.11 (pinned in Dockerfile)
    - mcr.microsoft.com/playwright:v1.49.0-jammy (test stage only)
    - @playwright/test@1.49.0 (test/dev dependency)
    - typescript@5.6.3 + @types/node@^20 (test/dev dependencies)
  patterns:
    - Two-stage Docker build with the npm + uv deps installed inside
      the build stages; the runtime stage only ships Python code,
      frontend/out/ (the static export), and the uv-managed deps —
      no node, no npm, no build tools in production image
    - `npm ci || npm install` fallback in the Docker build so the
      build succeeds even when package-lock.json has drifted; the
      primary path uses `npm ci` for reproducibility
    - Idempotent start scripts: detect an already-running container,
      build only if the image is missing (or `--build` was passed),
      wait up to 30s for /api/health before printing the URL
    - Idempotent stop scripts: `docker compose down` preserves the
      `finally-data` volume so SQLite persists across restarts;
      defensive `docker rm -f` for stray containers started via plain
      `docker run`
    - Dev-mode guard in main.py: `os.path.isdir("/app/static")` check
      before mounting — running uvicorn outside Docker for tests does
      not crash if the directory is absent (logs a warning instead)
    - Route registration order in FastAPI: API routers MUST be
      `include_router`'d before the static mount so `/api/*` resolves
      first (Starlette matches in registration order); the mount on
      `/` is a catch-all
    - Playwright fixture pattern: an auto-fixture (`{ auto: true }`)
      resets the watchlist to the 10 default tickers before each test
      using backend TESTING=1 endpoints, so spec files can mutate state
      without leaking across tests
    - CI uses `--abort-on-container-exit --exit-code-from playwright`
      so the playwright container's exit code propagates and the
      build fails fast on any spec failure
    - Playwright HTML report uploaded as a CI artifact on failure
      (`if: failure()` + `if-no-files-found: ignore`) so devs can
      inspect screenshots/traces without re-running locally

key-files:
  created:
    - Dockerfile (multi-stage, node + python+uv)
    - .dockerignore (excludes build noise + secrets + plans)
    - .env.example (template, no real keys)
    - docker-compose.yml (single app service + finally-data volume)
    - scripts/start_mac.sh (executable)
    - scripts/stop_mac.sh (executable)
    - scripts/start_windows.ps1
    - scripts/stop_windows.ps1
    - scripts/README.md (cross-platform usage docs)
    - test/docker-compose.test.yml (app + playwright services)
    - test/playwright.config.ts (chromium-only, baseURL http://app:8000)
    - test/package.json (Playwright + TypeScript devDeps)
    - test/tsconfig.json (strict ESM, ES2022 target)
    - test/e2e/fixtures.ts (custom test fixture with resetWatchlist)
    - test/e2e/watchlist.spec.ts (4 tests)
    - test/e2e/trade.spec.ts (3 tests)
    - test/e2e/portfolio.spec.ts (2 tests)
    - test/e2e/chat.spec.ts (1 test)
    - test/e2e/sse-resilience.spec.ts (2 tests)
    - test/README.md (how to run + what's tested)
    - .github/workflows/e2e.yml (CI: docker compose suite + report upload)
  modified:
    - backend/app/main.py (added `from fastapi.staticfiles import
      StaticFiles`, imported `os` already present; added static mount
      AFTER all API routers, with dev-mode guard)
    - .gitignore (added test/node_modules/, test/playwright-report/,
      test/test-results/)

# Decisions

1. **Two-stage Docker build, not single-stage** — production image
   should not contain node, npm, or the build tools. Stage 1 builds
   `frontend/out/`, stage 2 copies it as `/app/static` and ships only
   Python + uv-managed deps + uvicorn.
2. **uv pinned in Dockerfile** — `pip install --no-cache-dir uv==0.5.11`
   (instead of `pip install uv`) for reproducibility; the lockfile
   (backend/uv.lock) drives the actual dep set via
   `uv sync --frozen --no-dev || uv sync --no-dev`. The `||` fallback
   covers the case where the lockfile is in flux mid-development.
3. **`npm ci || npm install` fallback** — `npm ci` requires an
   up-to-date lockfile; during active development the lockfile can
   lag `package.json`. Falling back to `npm install` keeps the Docker
   build robust; production lockfile updates are still committed.
4. **Static mount AFTER API routers** — Starlette matches routes in
   registration order. If the mount on `/` were registered first, it
   would intercept `/api/*` requests. The plan and the implementation
   both call this out.
5. **Dev-mode `os.path.isdir` guard in main.py** — the backend must
   remain importable and runnable for `uv run --extra dev pytest`
   (no `/app/static` present in the sandbox or in CI test runners
   that don't run the full Docker build). The guard logs a warning
   and continues; production Docker images have the directory present.
6. **Idempotent start scripts over `--force-recreate`** — checking
   `docker ps -q -f name=finally` first and exiting 0 with a "already
   running" message is friendlier than `docker compose up --force-recreate`
   which would tear down + recreate the container on every run.
7. **`--abort-on-container-exit --exit-code-from playwright`** —
   these flags ensure the CI job exits with the playwright container's
   exit code (not the app's), so a failing spec fails the workflow.
8. **`healthcheck` with `condition: service_healthy`** in
   docker-compose.test.yml — playwright waits for the app's
   `/api/health` to respond before running tests. Without this the
   first spec races the FastAPI startup and times out.
9. **`LLM_MOCK=true` + `TESTING=1` in test env** — chat tests need
   deterministic responses (mock routes on keywords), and the
   `resetWatchlist` fixture needs the test-only endpoints. Both are
   environment-gated; production deploys keep `LLM_MOCK=false` and
   `TESTING` unset.
10. **Playwright types under `@types/node`** — `request.newContext`
    and friends reference Node APIs (`URL`, `Request`). Without
    `@types/node` the `tsc --noEmit` step in Task 3 fails with
    TS2688 (Cannot find type definition file for 'node'). Added as
    a devDependency.
11. **Gitignore `test/node_modules/`, `test/playwright-report/`,
    `test/test-results/`** — `npm install` from the test/ directory
    produced a node_modules tree that `git status` flagged as
    untracked; the root `.gitignore` didn't have a rule for `test/`
    yet. Adding the rule keeps the repo clean while letting devs
    iterate on the specs locally.

# Deviations from Plan

## Auto-fixed Issues

**1. [Rule 3 - Blocking] `tsc --noEmit` failed with TS2688 missing `@types/node`**
- **Found during:** Task 3 verification
- **Issue:** `tsconfig.json` declared `"types": ["node"]` (for `request.newContext`'s
  Node API references), but `@types/node` was not in `package.json`'s
  devDependencies. `npx tsc` failed with "Cannot find type definition file
  for 'node'".
- **Fix:** Added `"@types/node": "^20"` to `test/package.json`'s
  devDependencies and re-ran `npm install`. `tsc --noEmit` then exits 0.
- **Files modified:** test/package.json
- **Commit:** 9c1adde (included in the Task 3 commit; package-lock.json
  was regenerated to lock the new dep)

**2. [Rule 2 - Critical functionality] StaticFiles mount would crash dev mode**
- **Found during:** Task 1 verification
- **Issue:** The plan's exact Dockerfile path is `/app/static`, but
  `backend/uv run --extra dev pytest` (run inside the repo, not inside
  Docker) starts the FastAPI app without `/app/static` present. An
  unguarded `app.mount("/", StaticFiles(directory="/app/static"))` would
  crash with FileNotFoundError before pytest could even import the app.
- **Fix:** Wrapped the mount in an `if os.path.isdir("/app/static")` check
  with a logged warning. The mount is registered in Docker (where
  `/app/static` exists) and skipped in dev (where it does not, with
  the API still serving normally). All 194 backend tests still pass.
- **Files modified:** backend/app/main.py
- **Commit:** a3697df (included in the Task 1 commit)

**3. [Rule 3 - Blocking] test/node_modules was untracked**
- **Found during:** Task 3 staging
- **Issue:** `npm install` inside `test/` produced `test/node_modules`
  and `test/package-lock.json` — the latter should be committed, the
  former should not. The root `.gitignore` had rules for
  `frontend/node_modules/` but not `test/`.
- **Fix:** Added `test/node_modules/`, `test/playwright-report/`, and
  `test/test-results/` to the root `.gitignore`. Re-ran
  `git check-ignore -v test/node_modules` to confirm.
- **Files modified:** .gitignore
- **Commit:** 9c1adde (included in the Task 3 commit)

## Out-of-scope items logged for future work

- **No actual `docker build` run.** The sandbox does not have a running
  Docker daemon (only the CLI is installed). The plan explicitly notes
  "DO NOT attempt `docker build`" in this environment. Verification was
  done via file presence + syntax checks + route-registration-order
  inspection + backend pytest (194 passed). The full
  `docker build` + `docker compose -f test/docker-compose.test.yml up`
  validation is left to the student's first run OR to CI.
- **No `npx playwright install` run.** Same reason — the Playwright
  browser download is ~300 MB and the Docker compose file already uses
  the official Playwright image with browsers preinstalled. The
  `npm install` (4 packages, ~5s) DID run cleanly.
- **The plan's instruction "Tasks covered: DOCKER-01..09, TEST-01..03"
  are all referenced** — see the "Requirements covered" section below.

# Verification

## Files present (all 21 created/modified)
```
FOUND: Dockerfile
FOUND: .dockerignore
FOUND: .env.example
FOUND: docker-compose.yml
FOUND: scripts/start_mac.sh
FOUND: scripts/stop_mac.sh
FOUND: scripts/start_windows.ps1
FOUND: scripts/stop_windows.ps1
FOUND: scripts/README.md
FOUND: test/docker-compose.test.yml
FOUND: test/playwright.config.ts
FOUND: test/e2e/fixtures.ts
FOUND: test/e2e/watchlist.spec.ts
FOUND: test/e2e/trade.spec.ts
FOUND: test/e2e/portfolio.spec.ts
FOUND: test/e2e/chat.spec.ts
FOUND: test/e2e/sse-resilience.spec.ts
FOUND: test/README.md
FOUND: .github/workflows/e2e.yml
```

## Bash syntax check (Task 2 scripts)
```
bash -n scripts/start_mac.sh   -> exit 0
bash -n scripts/stop_mac.sh    -> exit 0
[ -x scripts/start_mac.sh ]    -> true
[ -x scripts/stop_mac.sh ]     -> true
```
PowerShell scripts were not validated with `pwsh` (not installed in
sandbox); manual review confirms `#Requires -Version 5.1`, idempotent
flow, and `$LASTEXITCODE` checks matching the bash equivalents.

## Docker availability
```
docker --version  -> Docker version 28.3.2, build 578ccf6
```

## Backend tests (no regression from main.py change)
```
cd backend && uv run --extra dev pytest -q
-> 194 passed, 2 warnings in 36.58s
```

## Frontend checks (no regression)
```
cd frontend && npx tsc --noEmit            -> exit 0
cd frontend && npx eslint src/ --max-warnings 0 -> exit 0
```

## Test directory type check
```
test/node_modules/.bin/tsc --noEmit -p test/tsconfig.json
-> exit 0 (no errors)
```

## Route registration order
```
cd backend && uv run python -c "from app.main import app; ..."
-> API routes registered: 10
-> Static mount routes: []   (dev mode — directory absent)
-> Logs: "Static directory /app/static not found; skipping static mount."
```

## Not run in sandbox (per plan instructions)
- `docker build -t finally .` — daemon not available
- `docker compose up` — daemon not available
- `docker compose -f test/docker-compose.test.yml up` — daemon not available
- `npx playwright install` — 300 MB browser download skipped; the
  Playwright Docker image has browsers preinstalled

# Auth gates
None.

# Requirements covered

DOCKER-01: Single `docker build -t finally .` produces a runnable image
  -> Dockerfile (two-stage, node + python+uv) implements this.
DOCKER-02: Container exposes the full app at http://localhost:8000
  -> CMD runs uvicorn on 0.0.0.0:8000; EXPOSE 8000; port mapping in
  docker-compose.yml.
DOCKER-03: FastAPI serves both /api/* and /* on the same port
  -> StaticFiles mount on "/" AFTER the API routers; FastAPI matches
  in registration order.
DOCKER-04: SQLite persists via named Docker volume at /app/db
  -> docker-compose.yml maps `finally-data:/app/db`; Dockerfile
  creates `/app/db` with `RUN mkdir -p`.
DOCKER-05: .env loaded for OPENROUTER_API_KEY, MASSIVE_API_KEY, LLM_MOCK
  -> docker-compose.yml uses `env_file: .env`; .env.example documents
  each var.
DOCKER-06: Idempotent start scripts (mac/Linux + Windows)
  -> scripts/start_mac.sh + scripts/start_windows.ps1 both detect an
  already-running container and exit 0; build is conditional on image
  presence (or `--build`).
DOCKER-07: Stop script preserves the data volume
  -> scripts/stop_mac.sh uses `docker compose down` (preserves volumes);
  start_windows.ps1 equivalent.
DOCKER-08: docker-compose.yml as a convenience wrapper
  -> Single `app` service + `finally-data` volume; `docker compose up -d`
  is the canonical start path used by the start scripts.
DOCKER-09: .dockerignore keeps build context minimal
  -> Excludes .git, .planning, .claude, .env, node_modules, .venv,
  db/*.db, test/, scripts/.

TEST-01: Playwright E2E tests run against the Docker stack
  -> test/docker-compose.test.yml spins up app + playwright; 5 spec
  files cover watchlist, trade, portfolio, chat, sse-resilience.
TEST-02: Tests run with LLM_MOCK=true (deterministic)
  -> docker-compose.test.yml sets LLM_MOCK=true and TESTING=1; chat
  spec asserts on the deterministic "Mock:" response text.
TEST-03: CI workflow runs the suite on every PR
  -> .github/workflows/e2e.yml runs
  `docker compose -f test/docker-compose.test.yml up --abort-on-container-exit --exit-code-from playwright`
  on pull_request and push to main; uploads playwright-report on failure.

# Known Stubs

- **`docker build` + `docker compose up` validation:** not run in this
  sandbox. The Dockerfile is syntactically clean and matches the
  multi-stage pattern the project spec calls for; the start script is
  exercised by `docker compose up` only on a real Docker host.
  Validation path: a student runs `./scripts/start_mac.sh` and sees
  the full app at http://localhost:8000; CI runs the playwright
  suite against the same image.
- **PowerShell script syntax:** not validated with `pwsh` (not installed
  in the sandbox). Manual review confirms the script follows
  PowerShell 5.1 conventions, uses `$ErrorActionPreference = "Stop"`,
  and exits with the docker command's `$LASTEXITCODE` where appropriate.
- **`npx playwright install` (browser download):** not run. The
  playwright Docker image (`mcr.microsoft.com/playwright:v1.49.0-jammy`)
  has Chromium preinstalled; `npx playwright install` is only needed
  for direct local invocation outside Docker.
- **The Playwright suite is not executed in the sandbox** because the
  full Docker stack is required and the daemon is unavailable. The
  specs were type-checked (`tsc --noEmit` exits 0) and reviewed against
  the existing frontend data-testid attributes (Header.tsx status dot,
  TradeBar inputs, ChatPanel trade chips, WatchlistPanel rows) and
  backend response shapes (PortfolioResponse, TradeResponse detail
  field, ChatEndpointResponse actions_executed). The CI workflow is the
  authoritative execution path.

# Self-Check: PASSED

- 19/19 expected artifacts present on disk
- 3/3 expected commits present in git log (a3697df, c994187, 9c1adde)
- backend: 194/194 tests pass
- frontend: tsc + eslint clean
- test/: tsc clean, npm install clean, gitignore properly excludes
  node_modules + playwright-report + test-results
- main.py: static mount registered AFTER API routers, dev-mode guard
  verified via route inspection
- bash scripts: `bash -n` clean, executable bit set
- Docker CLI installed (28.3.2) for future user validation
