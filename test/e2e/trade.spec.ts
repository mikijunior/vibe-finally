/**
 * Trade execution E2E tests.
 *
 * Verifies:
 *  - Buy reduces cash and adds a position
 *  - Sell increases cash and removes the position
 *  - Buying more than cash allows surfaces the backend's "Insufficient cash"
 *    detail inline next to the trade bar
 */

import { test, expect } from "./fixtures";

interface PortfolioResponse {
  cash_balance: number;
  total_value: number;
  positions: Array<{
    ticker: string;
    quantity: number;
    avg_cost: number;
    current_price: number;
    unrealized_pnl: number;
    pnl_percent: number;
  }>;
}

async function getPortfolio(
  api: import("@playwright/test").APIRequestContext,
): Promise<PortfolioResponse> {
  const res = await api.get("/api/portfolio");
  return res.json();
}

test.describe("Trade bar", () => {
  test("buy reduces cash and adds a position", async ({ page, api }) => {
    await page.goto("/");
    await page.getByTestId("watchlist-row-AAPL").waitFor({ timeout: 10_000 });

    const before = await getPortfolio(api);

    await page.getByTestId("trade-ticker-input").fill("AAPL");
    await page.getByTestId("trade-quantity-input").fill("1");
    await page.getByTestId("trade-buy-button").click();

    // Wait for the success chip or the cash display to update.
    await expect
      .poll(async () => (await getPortfolio(api)).cash_balance, {
        timeout: 10_000,
      })
      .toBeLessThan(before.cash_balance);

    const after = await getPortfolio(api);
    const aapl = after.positions.find((p) => p.ticker === "AAPL");
    expect(aapl).toBeDefined();
    expect(aapl?.quantity).toBeCloseTo(1, 5);
  });

  test("sell increases cash and removes the position", async ({ page, api }) => {
    await page.goto("/");

    // First buy 1 share so we have something to sell.
    await page.getByTestId("trade-ticker-input").fill("AAPL");
    await page.getByTestId("trade-quantity-input").fill("1");
    await page.getByTestId("trade-buy-button").click();
    await expect
      .poll(
        async () =>
          (await getPortfolio(api)).positions.find((p) => p.ticker === "AAPL")
            ?.quantity ?? 0,
        { timeout: 10_000 },
      )
      .toBeGreaterThan(0);

    const beforeSell = await getPortfolio(api);

    await page.getByTestId("trade-ticker-input").fill("AAPL");
    await page.getByTestId("trade-quantity-input").fill("1");
    await page.getByTestId("trade-sell-button").click();

    await expect
      .poll(async () => (await getPortfolio(api)).cash_balance, {
        timeout: 10_000,
      })
      .toBeGreaterThan(beforeSell.cash_balance);

    const after = await getPortfolio(api);
    const aapl = after.positions.find((p) => p.ticker === "AAPL");
    expect(aapl).toBeUndefined();
  });

  test("insufficient cash surfaces inline error", async ({ page, api }) => {
    await page.goto("/");

    const before = await getPortfolio(api);

    await page.getByTestId("trade-ticker-input").fill("AAPL");
    await page.getByTestId("trade-quantity-input").fill("999999");
    await page.getByTestId("trade-buy-button").click();

    // Inline error text contains "Insufficient cash" (from backend detail).
    await expect(page.getByText(/insufficient cash/i)).toBeVisible({
      timeout: 5_000,
    });

    // Cash balance unchanged.
    const after = await getPortfolio(api);
    expect(after.cash_balance).toBeCloseTo(before.cash_balance, 2);
  });
});
