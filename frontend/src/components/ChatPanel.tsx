/**
 * ChatPanel — conversation surface for the FinAlly AI assistant.
 *
 * The panel is a full-height right rail of the dashboard. Its collapsed state
 * is owned by `useChatPanelCollapsed` (zustand store) so the page-level
 * grid can react — collapsed width is 48px, expanded is whatever the right
 * column gives it (currently 400px).
 *
 * Each assistant message renders inline action chips for every executed
 * trade ("Bought 10 AAPL") and watchlist change ("+ NVDA added"). Failed
 * actions render red chips with the server's detail message.
 */

"use client";

import { clsx } from "clsx";
import { ChevronRight, MessageSquare } from "lucide-react";
import { useEffect, useRef, useState } from "react";

import { formatQuantity } from "@/lib/format";
import { useChat } from "@/lib/hooks/useChat";
import { useChatPanelCollapsed } from "@/lib/hooks/useChatPanelCollapsed";
import type { ChatActionResult } from "@/lib/types";

import { Button } from "./ui/button";
import { Input } from "./ui/input";

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
  const label =
    action.action === "remove" ? `- ${action.ticker} removed` : `+ ${action.ticker} added`;
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
  const collapsed = useChatPanelCollapsed((s) => s.collapsed);
  const setCollapsed = useChatPanelCollapsed((s) => s.set);
  const toggle = useChatPanelCollapsed((s) => s.toggle);

  const [draft, setDraft] = useState<string>("");

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
    inputRef.current?.focus();
  };

  if (collapsed) {
    return (
      <aside
        aria-label="Chat panel (collapsed)"
        className="bg-bg-elevated border-border-muted flex h-full w-full flex-col items-center justify-start gap-3 rounded border py-3"
        data-testid="chat-panel-collapsed"
      >
        <button
          type="button"
          aria-label="Expand chat panel"
          onClick={() => setCollapsed(false)}
          className="text-text-muted hover:text-accent-yellow rounded p-1 transition-colors"
        >
          <MessageSquare size={18} />
        </button>
      </aside>
    );
  }

  return (
    <aside
      aria-label="Chat panel"
      className="bg-bg-elevated border-border-muted flex h-full w-full flex-col rounded border"
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
          onClick={toggle}
          className="text-text-muted hover:text-accent-yellow rounded p-1 transition-colors"
        >
          <ChevronRight size={16} />
        </button>
      </header>

      <div
        ref={scrollRef}
        className="flex min-h-0 flex-1 flex-col gap-2 overflow-y-auto px-3 py-2"
        data-testid="chat-message-list"
      >
        {messages.length === 0 && !loading ? (
          <div className="text-text-muted flex flex-1 flex-col items-center justify-center gap-1 px-2 text-center font-mono text-xs italic">
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
                "flex flex-col gap-1 rounded p-2 text-sm leading-relaxed",
                isUser
                  ? "bg-blue-primary text-bg-base self-end max-w-[90%]"
                  : "bg-bg-base border-border-muted border self-start max-w-[95%]",
              )}
              data-testid={`chat-message-${msg.role}`}
            >
              <div className="whitespace-pre-wrap">{msg.content}</div>
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
          className="placeholder:text-text-muted h-10 flex-1"
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