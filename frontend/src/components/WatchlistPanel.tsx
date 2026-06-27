/**
 * Watchlist panel — list of tracked tickers with live price + sparkline +
 * click-to-select + add/remove controls.
 *
 * Reads the watchlist via SWR (`useWatchlist`) and writes through the api.ts
 * wrappers. After each successful mutation, calls `mutate()` so the row
 * appears/disappears without a full reload.
 */

"use client";

import { useState } from "react";
import { X } from "lucide-react";

import { addWatchlistTicker, removeWatchlistTicker } from "@/lib/api";
import { useWatchlist } from "@/lib/hooks/useWatchlist";
import { useSelectedTicker } from "@/lib/hooks/useSelectedTicker";

import { PriceCell } from "./PriceCell";
import { Sparkline } from "./Sparkline";

const DEFAULT_INPUT_TICKER = "";

export function WatchlistPanel() {
  const { entries, isLoading, error, mutate } = useWatchlist();
  const selectedTicker = useSelectedTicker((s) => s.selectedTicker);
  const setSelectedTicker = useSelectedTicker((s) => s.set);
  const [newTicker, setNewTicker] = useState<string>(DEFAULT_INPUT_TICKER);
  const [addError, setAddError] = useState<string | null>(null);
  const [busy, setBusy] = useState<boolean>(false);

  const handleAdd = async (e: React.FormEvent) => {
    e.preventDefault();
    const ticker = newTicker.trim().toUpperCase();
    if (!ticker) return;
    setBusy(true);
    setAddError(null);
    try {
      await addWatchlistTicker(ticker);
      setNewTicker("");
      await mutate();
    } catch (err) {
      setAddError(err instanceof Error ? err.message : "Failed to add ticker");
    } finally {
      setBusy(false);
    }
  };

  const handleRemove = async (ticker: string) => {
    setBusy(true);
    try {
      await removeWatchlistTicker(ticker);
      await mutate();
      if (selectedTicker === ticker) {
        useSelectedTicker.getState().clear();
      }
    } catch (err) {
      // The button only appears on rows so a failure is unusual; surface
      // it inline next to the form for simplicity.
      setAddError(err instanceof Error ? err.message : "Failed to remove");
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="bg-bg-elevated border-border-muted flex flex-col gap-2 rounded border p-2">
      <form
        onSubmit={handleAdd}
        className="flex items-center gap-2"
        aria-label="Add ticker"
      >
        <input
          type="text"
          value={newTicker}
          onChange={(e) => setNewTicker(e.target.value)}
          placeholder="Add ticker"
          maxLength={10}
          disabled={busy}
          className="bg-bg-base text-text-primary border-border-muted focus:border-blue-primary w-full rounded border px-2 py-1 font-mono text-sm uppercase tracking-wide outline-none"
        />
        <button
          type="submit"
          disabled={busy || newTicker.trim().length === 0}
          className="bg-blue-primary text-bg-base rounded px-3 py-1 text-sm font-semibold uppercase tracking-wide transition-opacity hover:opacity-90 disabled:opacity-40"
        >
          Add
        </button>
      </form>

      {addError ? (
        <div className="text-pnl-down px-1 text-xs">{addError}</div>
      ) : null}

      {isLoading ? (
        <div className="text-text-muted px-1 text-xs">Loading watchlist…</div>
      ) : error ? (
        <div className="text-pnl-down px-1 text-xs">
          Failed to load watchlist: {error.message}
        </div>
      ) : entries.length === 0 ? (
        <div className="text-text-muted px-1 text-xs italic">
          No tickers yet — add one above to get started.
        </div>
      ) : (
        <ul className="flex flex-col gap-1">
          {entries.map((entry) => {
            const isSelected = selectedTicker === entry.ticker;
            return (
              <li
                key={entry.ticker}
                onClick={() => setSelectedTicker(entry.ticker)}
                className={`flex cursor-pointer items-center justify-between gap-2 rounded border px-2 py-1 transition-colors ${
                  isSelected
                    ? "border-blue-primary bg-bg-base"
                    : "border-border-muted bg-bg-base hover:border-blue-primary/50"
                }`}
                data-testid={`watchlist-row-${entry.ticker}`}
              >
                <span className="text-text-primary w-16 font-mono text-sm font-bold">
                  {entry.ticker}
                </span>
                <PriceCell ticker={entry.ticker} />
                <Sparkline ticker={entry.ticker} />
                <button
                  type="button"
                  onClick={(e) => {
                    e.stopPropagation();
                    void handleRemove(entry.ticker);
                  }}
                  disabled={busy}
                  aria-label={`Remove ${entry.ticker}`}
                  className="text-text-muted hover:text-pnl-down rounded p-1 transition-colors disabled:opacity-40"
                >
                  <X size={14} />
                </button>
              </li>
            );
          })}
        </ul>
      )}
    </div>
  );
}