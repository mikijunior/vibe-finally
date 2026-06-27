/**
 * Portfolio visualization E2E tests.
 *
 * Verifies:
 *  - Heatmap renders at least one colored rectangle after a position is opened
 *  - P&L chart canvas exists and snapshots are recorded
 */

import { test, expect } from "./fixtures";

test.describe("Portfolio visualizations", () => {
  test("heatmap renders after a position is opened", async ({ page, api }) => {
    // Pre-condition: ensure at least one position exists.
    const portfolio = await api.get("/api/portfolio").then((r) => r.json());
    if (!portfolio.positions?.some((p: { ticker: string }) => p.ticker === "AAPL")) {
      await api.post("/api/portfolio/trade", {
        data: { ticker: "AAPL", quantity: 1, side: "buy" },
      });
    }

    await page.goto("/");
    await page.getByTestId("watchlist-row-AAPL").waitFor({ timeout: 10_000 });

    // The heatmap is an SVG with at least one <rect> having a non-empty fill.
    const heatmap = page.locator("svg").first();
    await expect(heatmap).toBeVisible({ timeout: 10_000 });

    const rects = heatmap.locator("rect");
    const count = await rects.count();
    expect(count).toBeGreaterThan(0);

    // At least one rect must have a fill that's a hex color (the heatmap
    // tints rectangles green/red by P&L).
    const fills = await rects.evaluateAll((els) =>
      els.map((el) => (el as SVGElement).getAttribute("fill") ?? ""),
    );
    const coloredFills = fills.filter((f) => /^#[0-9a-fA-F]{3,8}$/.test(f));
    expect(coloredFills.length).toBeGreaterThan(0);
  });

  test("P&L chart renders the canvas after a snapshot", async ({ page, api }) => {
    // Trigger an immediate snapshot by executing a trade (which records one
    // inline). The portfolio_snapshots table will have at least one row.
    await api.post("/api/portfolio/trade", {
      data: { ticker: "AAPL", quantity: 1, side: "buy" },
    });

    await page.goto("/");
    await page.getByTestId("watchlist-row-AAPL").waitFor({ timeout: 10_000 });

    // The PnLChart renders a <canvas> element. Allow time for the
    // lightweight-charts library to paint at least one frame.
    const canvas = page.locator("canvas").first();
    await expect(canvas).toBeVisible({ timeout: 10_000 });

    // Confirm the canvas has been drawn to (non-zero dimensions).
    const box = await canvas.boundingBox();
    expect(box).not.toBeNull();
    expect((box?.width ?? 0) * (box?.height ?? 0)).toBeGreaterThan(0);
  });
});
