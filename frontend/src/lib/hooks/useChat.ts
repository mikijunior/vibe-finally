/**
 * useChat — local conversation state + sendMessage helper.
 *
 * Chat history is session-local by design (the backend persists
 * chat_messages rows for audit + future replay, but the v1 UI does not
 * rehydrate on mount — each session starts with an empty conversation).
 *
 * On a successful response the caller is expected to refresh
 * portfolio + watchlist caches so executed actions are reflected in the
 * heatmap / positions table immediately.
 */

"use client";

import { useCallback, useState } from "react";

import { sendChat } from "@/lib/api";
import type { ChatActionResult } from "@/lib/types";

import { usePortfolio } from "./usePortfolio";
import { useWatchlist } from "./useWatchlist";

export interface ChatMessage {
  id: string;
  role: "user" | "assistant";
  content: string;
  actions: ChatActionResult[];
}

export interface UseChatResult {
  messages: ChatMessage[];
  loading: boolean;
  error: string | null;
  sendMessage: (content: string) => Promise<void>;
}

function randomId(): string {
  // crypto.randomUUID exists in modern browsers and Node 19+. Fall back to a
  // timestamped random string if the API is unavailable (older runtimes).
  if (typeof crypto !== "undefined" && typeof crypto.randomUUID === "function") {
    return crypto.randomUUID();
  }
  return `msg-${Date.now()}-${Math.floor(Math.random() * 1e6)}`;
}

export function useChat(): UseChatResult {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const portfolio = usePortfolio();
  const watchlist = useWatchlist();

  const sendMessage = useCallback(
    async (content: string): Promise<void> => {
      const trimmed = content.trim();
      if (!trimmed) return;

      const userMsg: ChatMessage = {
        id: randomId(),
        role: "user",
        content: trimmed,
        actions: [],
      };

      setMessages((prev) => [...prev, userMsg]);
      setLoading(true);
      setError(null);

      try {
        const response = await sendChat({ message: trimmed });
        const assistantMsg: ChatMessage = {
          id: randomId(),
          role: "assistant",
          content: response.message,
          actions: response.actions_executed ?? [],
        };
        setMessages((prev) => [...prev, assistantMsg]);

        // Best-effort refresh so trades/watchlist changes are reflected.
        try {
          await Promise.all([
            portfolio.mutate?.() ?? Promise.resolve(),
            watchlist.mutate?.() ?? Promise.resolve(),
          ]);
        } catch {
          // Cache mutation errors are non-fatal — the next SWR refresh tick
          // (5s for portfolio) will reconcile.
        }
      } catch (err) {
        const detail =
          err instanceof Error ? err.message : "Chat request failed";
        setError(detail);
        // Surface the failure as an assistant message so the user sees it in
        // the conversation history even after the spinner disappears.
        setMessages((prev) => [
          ...prev,
          {
            id: randomId(),
            role: "assistant",
            content: `Error: ${detail}`,
            actions: [],
          },
        ]);
      } finally {
        setLoading(false);
      }
    },
    [portfolio, watchlist],
  );

  return { messages, loading, error, sendMessage };
}
