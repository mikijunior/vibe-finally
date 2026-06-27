# FinAlly Start/Stop Scripts

## macOS / Linux

```bash
./scripts/start_mac.sh           # build (if needed) and start the container
./scripts/start_mac.sh --build   # force a rebuild before starting
./scripts/stop_mac.sh            # stop and remove the container
```

## Windows (PowerShell)

```powershell
.\scripts\start_windows.ps1           # build (if needed) and start the container
.\scripts\start_windows.ps1 -Build    # force a rebuild
.\scripts\stop_windows.ps1            # stop and remove the container
```

Both scripts are **idempotent** — re-running them on a healthy container is a
no-op. The start script waits up to 30 seconds for `/api/health` to respond
before printing the URL.

## Data persistence

The SQLite database is stored in the `finally-data` Docker volume mounted at
`/app/db` inside the container. Stopping the container preserves the volume;
deleting it (`docker volume rm finally-data`) resets the app to a fresh state
(empty watchlist, $10,000 cash).

## Configuration

Copy `.env.example` to `.env` and fill in:

| Variable | Required | Purpose |
|----------|----------|---------|
| `OPENROUTER_API_KEY` | Yes (for chat) | API key for the LLM chat assistant |
| `MASSIVE_API_KEY`    | No (default: simulator) | Real market data instead of built-in simulator |
| `LLM_MOCK`           | No (default: `false`)   | Set to `true` for deterministic mock LLM responses (used by E2E tests) |
