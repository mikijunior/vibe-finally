/**
 * TradeBar — ticker + quantity inputs with Buy/Sell buttons.
 *
 * POSTs to /api/portfolio/trade with no confirmation dialog (matches the
 * product spec: simulated money, instant fill, friction-free UX). On
 * success the portfolio + watchlist SWR caches are mutated so the rest of
 * the UI reflects the new state immediately. On HTTP 4xx the server's
 * `detail` string is displayed inline next to the inputs.
 */

"use client";

import { useState } from "react";

import { executeTrade } from "@/lib/api";
import { formatDollars } from "@/lib/format";
import { usePortfolio } from "@/lib/hooks/usePortfolio";
import { useWatchlist } from "@/lib/hooks/useWatchlist";

import { Button } from "./ui/button";
import { Input } from "./ui/input";

type Side = "buy" | "sell";

const FLASH_DURATION_MS = 1500;

export function TradeBar() {
  const portfolio = usePortfolio();
  const watchlist = useWatchlist();

  const [ticker, setTicker] = useState<string>("");
  const [quantity, setQuantity] = useState<string>("");
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);
  const [loading, setLoading] = useState<boolean>(false);

  const submit = async (side: Side) => {
    setError(null);
    setSuccess(null);

    const t = ticker.trim().toUpperCase();
    const qtyRaw = quantity.trim();
    const qty = Number(qtyRaw);

    if (!t) {
      setError("Ticker is required");
      return;
    }
    if (!qtyRaw || Number.isNaN(qty) || qty <= 0) {
      setError("Quantity must be a positive number");
      return;
    }

    setLoading(true);
    try {
      const res = await executeTrade({ ticker: t, quantity: qty, side });
      setTicker("");
      setQuantity("");
      setSuccess(`Filled ${side} ${qty} ${t} • cash ${formatDollars(res.cash_balance)}`);

      // Best-effort cache refresh so the rest of the dashboard reflects the
      // new position and cash balance without waiting for the 5s polling tick.
      try {
        await Promise.all([
          portfolio.mutate?.() ?? Promise.resolve(),
          watchlist.mutate?.() ?? Promise.resolve(),
        ]);
      } catch {
        // Cache errors are non-fatal — SWR will revalidate.
      }

      window.setTimeout(() => setSuccess(null), FLASH_DURATION_MS);
    } catch (err) {
      // The ApiError carries the backend's `detail` string. Fall back to the
      // generic message for non-API errors.
      const detail = err instanceof Error ? err.message : "Trade failed";
      setError(detail);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="bg-bg-elevated border-border-muted flex flex-col gap-2 rounded border p-2">
      <div className="flex items-baseline justify-between">
        <span className="text-text-muted font-mono text-[10px] uppercase tracking-wider">
          Trade
        </span>
        <span className="text-text-muted font-mono text-[10px] italic">
          market order • instant fill
        </span>
      </div>
      <div className="flex items-center gap-2">
        <Input
          aria-label="Ticker"
          placeholder="TICKER"
          value={ticker}
          onChange={(e) => setTicker(e.target.value.toUpperCase())}
          onBlur={() => setTicker((v) => v.trim().toUpperCase())}
          maxLength={10}
          disabled={loading}
          className="w-28"
          data-testid="trade-ticker-input"
        />
        <Input
          aria-label="Quantity"
          placeholder="Qty"
          value={quantity}
          onChange={(e) => setQuantity(e.target.value)}
          inputMode="decimal"
          disabled={loading}
          className="w-24"
          data-testid="trade-quantity-input"
        />
        <Button
          variant="default"
          onClick={() => submit("buy")}
          disabled={loading}
          data-testid="trade-buy-button"
        >
          Buy
        </Button>
        <Button
          variant="destructive"
          onClick={() => submit("sell")}
          disabled={loading}
          data-testid="trade-sell-button"
        >
          Sell
        </Button>
      </div>
      {error ? (
        <div
          className="text-pnl-down px-1 font-mono text-xs"
          data-testid="trade-error"
        >
          {error}
        </div>
      ) : null}
      {success && !error ? (
        <div
          className="text-pnl-up px-1 font-mono text-xs"
          data-testid="trade-success"
        >
          {success}
        </div>
      ) : null}
    </div>
  );
}
