/**
 * SSE resilience E2E tests.
 *
 * Verifies:
 *  - Status dot reads "connected" (LIVE / green) within a few seconds of
 *    page load
 *  - Forcing a disconnect via request interception flips the dot to a
 *    non-connected state (reconnecting or disconnected)
 *
 * The status dot exposes data-status="connected" | "reconnecting" |
 * "disconnected" via data-testid="header-connection-status".
 */

import { test, expect } from "./fixtures";

test.describe("SSE resilience", () => {
  test("status dot is connected after page load", async ({ page }) => {
    await page.goto("/");

    const status = page.getByTestId("header-connection-status");
    await expect(status).toBeVisible({ timeout: 10_000 });

    // The EventSource opens within ~1s of mount and the price-stream
    // hook reports connected.
    await expect(status).toHaveAttribute("data-status", "connected", {
      timeout: 10_000,
    });
  });

  test("status reflects forced disconnect via route abort", async ({
    page,
  }) => {
    // Intercept the SSE endpoint and abort every request — the
    // EventSource will fire onerror and the hook flips the status.
    await page.route("**/api/stream/prices", (route) => route.abort());

    await page.goto("/");

    const status = page.getByTestId("header-connection-status");
    await expect(status).toBeVisible({ timeout: 10_000 });

    // Eventually the connection should NOT be in the "connected" state.
    // We allow up to 10s for the EventSource error path to propagate.
    await expect(status).not.toHaveAttribute("data-status", "connected", {
      timeout: 10_000,
    });
  });
});
