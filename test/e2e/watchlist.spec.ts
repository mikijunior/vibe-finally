/**
 * Watchlist E2E tests.
 *
 * Verifies:
 *  - 10 default tickers render on the dashboard
 *  - At least one price changes over a 3-second window (SSE is live)
 *  - Adding a ticker via the inline form inserts a new row
 *  - Removing a ticker via the row's delete button removes the row
 */

import { test, expect, DEFAULT_TICKERS } from "./fixtures";

test.describe("Watchlist", () => {
  test("renders the 10 default tickers", async ({ page, resetWatchlist }) => {
    await page.goto("/");

    // Each default ticker should render as a watchlist row.
    for (const ticker of DEFAULT_TICKERS) {
      await expect(page.getByTestId(`watchlist-row-${ticker}`)).toBeVisible({
        timeout: 10_000,
      });
    }
  });

  test("prices change over time", async ({ page }) => {
    await page.goto("/");
    // Wait for the watchlist to settle.
    const firstRow = page.getByTestId("watchlist-row-AAPL");
    await expect(firstRow).toBeVisible({ timeout: 10_000 });

    // Capture all rendered price cells (text inside the price element).
    // Then wait a few seconds and capture again.
    const captures: string[] = [];
    for (let i = 0; i < 6; i += 1) {
      const text = await page
        .locator('[data-testid^="watchlist-row-"]')
        .allInnerTexts();
      captures.push(text.join("|"));
      await page.waitForTimeout(800);
    }

    // At least one capture must differ from another.
    const unique = new Set(captures);
    expect(unique.size).toBeGreaterThan(1);
  });

  test("can add a ticker via the inline form", async ({ page }) => {
    await page.goto("/");

    // The ticker to add is NOT in the default list (so resetWatchlist
    // won't add it back). BA = Boeing — a real ticker symbol.
    const ticker = "BA";

    const input = page.getByPlaceholder("Add ticker");
    await expect(input).toBeVisible();
    await input.fill(ticker);
    await page.getByRole("button", { name: "Add" }).click();

    await expect(page.getByTestId(`watchlist-row-${ticker}`)).toBeVisible({
      timeout: 5_000,
    });
  });

  test("can remove a ticker via the row's delete button", async ({
    page,
  }) => {
    await page.goto("/");

    const row = page.getByTestId("watchlist-row-AAPL");
    await expect(row).toBeVisible({ timeout: 10_000 });

    // Each watchlist row has a remove button with aria-label="Remove AAPL".
    await page.getByRole("button", { name: /Remove AAPL/i }).click();

    await expect(page.getByTestId("watchlist-row-AAPL")).toHaveCount(0, {
      timeout: 5_000,
    });
  });
});
