/**
 * AI chat E2E tests (LLM_MOCK=true).
 *
 * The chat endpoint, when LLM_MOCK=true, returns deterministic responses
 * keyed off keywords in the user message. "buy 1 AAPL" produces a trade
 * action that the executor then persists, and the chat panel renders an
 * inline trade chip for it.
 */

import { test, expect } from "./fixtures";

test.describe("Chat panel", () => {
  test("send message and receive mocked response with inline trade chip", async ({
    page,
  }) => {
    await page.goto("/");

    // Wait for the chat panel to mount.
    await expect(page.getByTestId("chat-panel")).toBeVisible({
      timeout: 10_000,
    });

    // Type the message and submit via the Send button.
    await page.getByPlaceholder(/Ask the AI/i).fill("buy 1 AAPL");
    await page.getByRole("button", { name: /send/i }).click();

    // Assistant message bubble appears with deterministic mock content.
    const assistantMsg = page.getByTestId("chat-message-assistant").last();
    await expect(assistantMsg).toBeVisible({ timeout: 10_000 });

    // The mock LLM always returns a message starting with "Mock:" — that's
    // the deterministic marker we assert against. (See backend/app/llm/mock.py.)
    await expect(assistantMsg).toContainText(/mock/i);

    // Inline trade chip for AAPL is rendered.
    await expect(
      page.getByTestId("chat-action-trade-AAPL"),
    ).toBeVisible({ timeout: 5_000 });
  });
});
