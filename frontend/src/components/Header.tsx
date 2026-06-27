/**
 * Header bar — wordmark + live portfolio total value + cash balance +
 * connection-status dot.
 *
 * The total value recomputes on every SSE price tick (sum of position.qty *
 * live price + cash). The status dot reflects EventSource.readyState via the
 * singleton price-stream hook.
 */

"use client";

import { useMemo } from "react";

import { formatDollars } from "@/lib/format";
import { usePriceStream } from "@/lib/price-stream";
import { usePriceStore } from "@/lib/store";
import { usePortfolio } from "@/lib/hooks/usePortfolio";

const STATUS_DOT_COLORS = {
  connected: "bg-pnl-up",
  reconnecting: "bg-accent-yellow",
  disconnected: "bg-pnl-down",
} as const;

const STATUS_LABELS = {
  connected: "LIVE",
  reconnecting: "RECONNECTING",
  disconnected: "OFFLINE",
} as const;

export function Header() {
  const { connectionStatus } = usePriceStream();
  const { portfolio, isLoading } = usePortfolio();

  // Subscribe to the entire prices map so total-value recomputes on every tick.
  // The slice returns a new reference each tick; useMemo below filters to
  // tickers present in our positions.
  const prices = usePriceStore((s) => s.prices);

  const totalValue = useMemo(() => {
    if (!portfolio) return null;
    const positionsValue = portfolio.positions.reduce((sum, p) => {
      const live = prices[p.ticker]?.price;
      const price = live ?? p.current_price;
      return sum + p.quantity * price;
    }, 0);
    return portfolio.cash_balance + positionsValue;
  }, [portfolio, prices]);

  const dotColor = STATUS_DOT_COLORS[connectionStatus];
  const statusLabel = STATUS_LABELS[connectionStatus];

  return (
    <header className="bg-bg-elevated border-border-muted flex items-center justify-between rounded border px-4 py-2">
      <div className="flex items-baseline gap-3">
        <span className="text-accent-yellow font-mono text-xl font-bold tracking-wider">
          FinAlly
        </span>
        <span className="text-text-muted font-mono text-xs uppercase tracking-wide">
          AI Trading Workstation
        </span>
      </div>

      <div className="flex items-baseline gap-6">
        <div className="flex flex-col items-end">
          <span className="text-text-muted font-mono text-[10px] uppercase tracking-wider">
            Total Value
          </span>
          <span
            className="text-text-primary font-mono text-lg font-bold"
            data-testid="header-total-value"
          >
            {totalValue !== null ? formatDollars(totalValue) : isLoading ? "…" : "$0.00"}
          </span>
        </div>
        <div className="flex flex-col items-end">
          <span className="text-text-muted font-mono text-[10px] uppercase tracking-wider">
            Cash
          </span>
          <span
            className="text-text-primary font-mono text-sm"
            data-testid="header-cash"
          >
            {portfolio ? formatDollars(portfolio.cash_balance) : "—"}
          </span>
        </div>
        <div
          className="flex items-center gap-2"
          data-testid="header-connection-status"
          data-status={connectionStatus}
        >
          <span
            aria-hidden
            className={`inline-block h-2 w-2 rounded-full ${dotColor}`}
          />
          <span className="text-text-muted font-mono text-[10px] uppercase tracking-wider">
            {statusLabel}
          </span>
        </div>
      </div>
    </header>
  );
}
