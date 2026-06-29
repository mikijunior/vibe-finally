/**
 * PositionsTable — tabular view of all open positions with live price
 * overrides from the price store. P&L cells are colored green/red.
 */

"use client";

import { clsx } from "clsx";

import { formatDollars, formatPercent, formatQuantity } from "@/lib/format";
import { usePortfolio } from "@/lib/hooks/usePortfolio";
import { usePriceStore } from "@/lib/store";

export function PositionsTable() {
  const { portfolio, isLoading } = usePortfolio();
  const prices = usePriceStore((s) => s.prices);

  if (isLoading && !portfolio) {
    return (
      <div className="bg-bg-elevated border-border-muted flex h-full min-h-0 items-center justify-center rounded border p-2">
        <span className="text-text-muted font-mono text-xs">Loading positions…</span>
      </div>
    );
  }

  const positions = portfolio?.positions ?? [];

  return (
    <div className="bg-bg-elevated border-border-muted flex h-full min-h-0 flex-col gap-2 rounded border p-2">
      <div className="flex items-baseline justify-between">
        <span className="text-text-muted font-mono text-[10px] uppercase tracking-wider">
          Positions
        </span>
        <span className="text-text-muted font-mono text-[10px] italic">
          {positions.length} open
        </span>
      </div>
      <div className="min-h-0 flex-1 overflow-y-auto">
        {positions.length === 0 ? (
          <div className="text-text-muted flex h-full items-center justify-center font-mono text-xs italic">
            No open positions.
          </div>
        ) : (
          <table className="w-full border-collapse text-left">
            <thead className="bg-bg-base text-text-muted sticky top-0">
              <tr className="border-border-muted border-b">
                <th className="px-2 py-1 font-mono text-[10px] font-semibold uppercase tracking-wider">
                  Ticker
                </th>
                <th className="px-2 py-1 text-right font-mono text-[10px] font-semibold uppercase tracking-wider">
                  Qty
                </th>
                <th className="px-2 py-1 text-right font-mono text-[10px] font-semibold uppercase tracking-wider">
                  Avg Cost
                </th>
                <th className="px-2 py-1 text-right font-mono text-[10px] font-semibold uppercase tracking-wider">
                  Price
                </th>
                <th className="px-2 py-1 text-right font-mono text-[10px] font-semibold uppercase tracking-wider">
                  P&amp;L
                </th>
                <th className="px-2 py-1 text-right font-mono text-[10px] font-semibold uppercase tracking-wider">
                  %
                </th>
              </tr>
            </thead>
            <tbody>
              {positions.map((p) => {
                const livePrice = prices[p.ticker]?.price;
                const price = livePrice ?? p.current_price;
                const pnl = (price - p.avg_cost) * p.quantity;
                const pnlPct =
                  p.avg_cost > 0
                    ? ((price - p.avg_cost) / p.avg_cost) * 100
                    : 0;
                const positive = pnl >= 0;
                const pnlColor = positive ? "text-pnl-up" : "text-pnl-down";
                return (
                  <tr
                    key={p.ticker}
                    className="border-border-muted border-b last:border-b-0"
                    data-testid={`position-row-${p.ticker}`}
                  >
                    <td className="text-text-primary px-2 py-1 font-mono text-sm font-bold">
                      {p.ticker}
                    </td>
                    <td className="px-2 py-1 text-right font-mono text-sm">
                      {formatQuantity(p.quantity)}
                    </td>
                    <td className="px-2 py-1 text-right font-mono text-sm">
                      {formatDollars(p.avg_cost)}
                    </td>
                    <td className="px-2 py-1 text-right font-mono text-sm">
                      {formatDollars(price)}
                    </td>
                    <td className={clsx("px-2 py-1 text-right font-mono text-sm", pnlColor)}>
                      {formatDollars(pnl)}
                    </td>
                    <td className={clsx("px-2 py-1 text-right font-mono text-sm", pnlColor)}>
                      {formatPercent(pnlPct, 2)}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}
