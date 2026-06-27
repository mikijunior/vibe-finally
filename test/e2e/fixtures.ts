/**
 * Custom test fixture with reset helpers.
 *
 * The `resetWatchlist` fixture restores the default 10-ticker watchlist
 * before each test, so individual specs can mutate the watchlist without
 * leaking state across tests. Uses the backend's TESTING=1 endpoints
 * (`/watchlist/test-add/{ticker}`, `/watchlist/test-remove/{ticker}`)
 * declared in backend/app/main.py.
 */

import { test as base, request, type APIRequestContext } from "@playwright/test";

export const DEFAULT_TICKERS = [
  "AAPL",
  "GOOGL",
  "MSFT",
  "AMZN",
  "TSLA",
  "NVDA",
  "META",
  "JPM",
  "V",
  "NFLX",
] as const;

/**
 * Reset the watchlist to the 10 default tickers using the backend
 * TESTING=1 endpoints. Idempotent: tests calling this fixture get a
 * clean slate before they run.
 */
async function resetWatchlist(api: APIRequestContext): Promise<void> {
  // Probe the current state and converge to DEFAULT_TICKERS.
  const current = await api.get("/api/watchlist").then((r) => r.json());
  const currentTickers: string[] = (current.entries ?? []).map(
    (e: { ticker: string }) => e.ticker,
  );

  // Remove anything not in the default list.
  for (const t of currentTickers) {
    if (!(DEFAULT_TICKERS as readonly string[]).includes(t)) {
      await api.post(`/watchlist/test-remove/${t}`);
    }
  }
  // Add anything from the default list that's missing.
  for (const t of DEFAULT_TICKERS) {
    if (!currentTickers.includes(t)) {
      await api.post(`/watchlist/test-add/${t}`);
    }
  }
}

export const test = base.extend<{
  api: APIRequestContext;
  resetWatchlist: void;
}>({
  api: async ({ baseURL }, use) => {
    const ctx = await request.newContext({ baseURL });
    await use(ctx);
    await ctx.dispose();
  },
  resetWatchlist: [
    async ({ api }, use) => {
      await resetWatchlist(api);
      await use();
    },
    { auto: true },
  ],
});

export { expect } from "@playwright/test";
