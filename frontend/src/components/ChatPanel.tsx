/**
 * ChatPanel — conversation surface for the FinAlly AI assistant.
 *
 * Each assistant message renders inline action chips for every executed
 * trade ("Bought 10 AAPL @ $191.50") and watchlist change ("+ NVDA added").
 * Failed actions render red chips with the server's detail message.
 *
 * The panel is collapsible: clicking the chevron toggles a 32px rail with
 * just a chat icon so the dashboard can reclaim the right-hand column.
 */

"use client";

import { clsx } from "clsx";
import { ChevronLeft, ChevronRight, MessageSquare } from "lucide-react";
import { useEffect, useRef, useState } from "react";

import { formatQuantity } from "@/lib/format";
import { useChat } from "@/lib/hooks/useChat";
import type { ChatActionResult } from "@/lib/types";

import { Button } from "./ui/button";
import { Input } from "./ui/input";

const PANEL_WIDTH_EXPANDED = "w-80";
const PANEL_WIDTH_COLLAPSED = "w-8";

function ActionChip({ action }: { action: ChatActionResult }) {
  if (action.status === "failed") {
    return (
      <span
        className="bg-pnl-down inline-flex items-center gap-1 rounded px-2 py-0.5 font-mono text-[11px] font-semibold uppercase tracking-wider text-white"
        title={action.detail ?? "Action failed"}
        data-testid={`chat-action-failed-${action.ticker}`}
      >
        FAILED: {action.ticker}
        {action.detail ? <span className="font-normal normal-case opacity-90">— {action.detail}</span> : null}
      </span>
    );
  }

  if (action.type === "trade") {
    const verb = action.side === "buy" ? "Bought" : "Sold";
    const chipClass =
      action.side === "buy"
        ? "bg-pnl-up text-bg-base"
        : "bg-pnl-down text-white";
    // The price isn't returned by the executor (only side/quantity). The
    // formatted chip shows the verb, qty, and ticker; the dollar amount is
    // shown only if we ever extend the API to include it.
    return (
      <span
        className={clsx(
          "inline-flex items-center gap-1 rounded px-2 py-0.5 font-mono text-[11px] font-semibold uppercase tracking-wider",
          chipClass,
        )}
        data-testid={`chat-action-trade-${action.ticker}`}
      >
        {verb} {formatQuantity(action.quantity ?? 0)} {action.ticker}
      </span>
    );
  }

  // type === "watchlist"
  const label = action.action === "remove" ? `- ${action.ticker} removed` : `+ ${action.ticker} added`;
  return (
    <span
      className="bg-purple-secondary inline-flex items-center gap-1 rounded px-2 py-0.5 font-mono text-[11px] font-semibold uppercase tracking-wider text-white"
      data-testid={`chat-action-watchlist-${action.ticker}`}
    >
      {label}
    </span>
  );
}

export function ChatPanel() {
  const { messages, loading, sendMessage } = useChat();
  const [draft, setDraft] = useState<string>("");
  const [collapsed, setCollapsed] = useState<boolean>(false);

  const scrollRef = useRef<HTMLDivElement | null>(null);
  const inputRef = useRef<HTMLInputElement | null>(null);

  // Auto-scroll to the bottom whenever the message list grows.
  useEffect(() => {
    const node = scrollRef.current;
    if (!node) return;
    node.scrollTop = node.scrollHeight;
  }, [messages.length, loading]);

  const onSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    const value = draft.trim();
    if (!value || loading) return;
    setDraft("");
    await sendMessage(value);
    // Restore focus for the next message.
    inputRef.current?.focus();
  };

  if (collapsed) {
    return (
      <aside
        aria-label="Chat panel (collapsed)"
        className={clsx(
          "bg-bg-elevated border-border-muted flex h-full flex-col items-center justify-start gap-2 border-l py-2",
          PANEL_WIDTH_COLLAPSED,
        )}
      >
        <button
          type="button"
          aria-label="Expand chat panel"
          onClick={() => setCollapsed(false)}
          className="text-text-muted hover:text-blue-primary rounded p-1 transition-colors"
        >
          <MessageSquare size={16} />
        </button>
        <button
          type="button"
          aria-label="Expand chat panel"
          onClick={() => setCollapsed(false)}
          className="text-text-muted hover:text-blue-primary rounded p-1 transition-colors"
        >
          <ChevronLeft size={16} />
        </button>
      </aside>
    );
  }

  return (
    <aside
      aria-label="Chat panel"
      className={clsx(
        "bg-bg-elevated border-border-muted flex h-full flex-col border-l",
        PANEL_WIDTH_EXPANDED,
      )}
      data-testid="chat-panel"
    >
      <header className="border-border-muted flex items-center justify-between border-b px-3 py-2">
        <div className="flex items-baseline gap-2">
          <span className="text-text-primary font-mono text-sm font-bold uppercase tracking-wider">
            AI Assistant
          </span>
          <span className="text-text-muted font-mono text-[10px] italic">
            FinAlly
          </span>
        </div>
        <button
          type="button"
          aria-label="Collapse chat panel"
          onClick={() => setCollapsed(true)}
          className="text-text-muted hover:text-blue-primary rounded p-1 transition-colors"
        >
          <ChevronRight size={16} />
        </button>
      </header>

      <div
        ref={scrollRef}
        className="flex flex-1 flex-col gap-2 overflow-y-auto px-3 py-2"
        data-testid="chat-message-list"
      >
        {messages.length === 0 && !loading ? (
          <div className="text-text-muted flex flex-1 flex-col items-center justify-center gap-1 font-mono text-xs italic">
            <span>Ask the AI to analyze your portfolio,</span>
            <span>propose trades, or manage the watchlist.</span>
            <span className="mt-1 opacity-60">e.g. &ldquo;Buy 5 shares of NVDA&rdquo;</span>
          </div>
        ) : null}

        {messages.map((msg) => {
          const isUser = msg.role === "user";
          return (
            <div
              key={msg.id}
              className={clsx(
                "flex flex-col gap-1 rounded p-2",
                isUser
                  ? "bg-blue-primary text-bg-base self-end max-w-[85%]"
                  : "bg-bg-base border-border-muted border self-start max-w-[95%]",
              )}
              data-testid={`chat-message-${msg.role}`}
            >
              <div className="font-mono text-xs leading-relaxed whitespace-pre-wrap">
                {msg.content}
              </div>
              {!isUser && msg.actions.length > 0 ? (
                <div className="mt-1 flex flex-wrap gap-1">
                  {msg.actions.map((a, idx) => (
                    <ActionChip key={`${a.ticker}-${a.type}-${idx}`} action={a} />
                  ))}
                </div>
              ) : null}
            </div>
          );
        })}

        {loading ? (
          <div
            className="text-text-muted flex items-center gap-2 self-start font-mono text-xs italic"
            data-testid="chat-loading"
          >
            <span className="bg-blue-primary inline-block h-2 w-2 animate-pulse rounded-full" />
            FinAlly is thinking...
          </div>
        ) : null}
      </div>

      <form
        onSubmit={onSubmit}
        className="border-border-muted flex items-center gap-2 border-t px-3 py-2"
        aria-label="Send chat message"
      >
        <Input
          ref={inputRef}
          value={draft}
          onChange={(e) => setDraft(e.target.value)}
          placeholder="Ask FinAlly…"
          disabled={loading}
          className="placeholder:text-text-muted flex-1"
          data-testid="chat-input"
        />
        <Button
          variant="submit"
          type="submit"
          disabled={loading || !draft.trim()}
          data-testid="chat-send-button"
        >
          Send
        </Button>
      </form>
    </aside>
  );
}
