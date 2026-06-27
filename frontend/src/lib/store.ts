/**
 * Zustand store for live price data fed by the SSE stream.
 *
 * Components subscribe to slices of this store to avoid re-rendering on every
 * price update. The price-stream hook calls `bulkUpdate` once per SSE event.
 *
 * Each ticker keeps a rolling buffer of up to MAX_SPARKLINE_POINTS prices so
 * sparklines can fill in progressively from the moment the page loads.
 */

"use client";

import { create } from "zustand";

import type { PriceDirection, PriceUpdate } from "./types";

const MAX_SPARKLINE_POINTS = 60;

export interface PriceState {
  /** Latest price snapshot per ticker. */
  prices: Record<string, PriceUpdate>;
  /** Rolling buffer of price points per ticker (newest-last). */
  sparklines: Record<string, number[]>;
  /** Last direction per ticker ("up" | "down" | "flat" | "unchanged"). */
  lastDirection: Record<string, PriceDirection>;
  /** Monotonic counter incremented on every update — useful for memo busting. */
  version: number;
}

export interface PriceActions {
  /** Append a single PriceUpdate; updates sparklines + lastDirection + version. */
  update: (ticker: string, update: PriceUpdate) => void;
  /** Apply many updates at once — used by the price-stream SSE hook. */
  bulkUpdate: (updates: Record<string, PriceUpdate>) => void;
  /** Manually set the last direction (used by Sparkline for color decisions). */
  setDirection: (ticker: string, direction: PriceDirection) => void;
  /** Reset the entire store — primarily for tests. */
  reset: () => void;
}

export type PriceStore = PriceState & PriceActions;

const initialState: PriceState = {
  prices: {},
  sparklines: {},
  lastDirection: {},
  version: 0,
};

export const usePriceStore = create<PriceStore>((set) => ({
  ...initialState,

  update: (ticker, update) =>
    set((state) => {
      const existingSpark = state.sparklines[ticker] ?? [];
      const nextSpark = [...existingSpark, update.price];
      if (nextSpark.length > MAX_SPARKLINE_POINTS) {
        nextSpark.splice(0, nextSpark.length - MAX_SPARKLINE_POINTS);
      }
      return {
        prices: { ...state.prices, [ticker]: update },
        sparklines: { ...state.sparklines, [ticker]: nextSpark },
        lastDirection: { ...state.lastDirection, [ticker]: update.direction },
        version: state.version + 1,
      };
    }),

  bulkUpdate: (updates) =>
    set((state) => {
      const prices = { ...state.prices };
      const sparklines = { ...state.sparklines };
      const lastDirection = { ...state.lastDirection };

      for (const [ticker, update] of Object.entries(updates)) {
        prices[ticker] = update;
        const existing = sparklines[ticker] ?? [];
        const next = [...existing, update.price];
        if (next.length > MAX_SPARKLINE_POINTS) {
          next.splice(0, next.length - MAX_SPARKLINE_POINTS);
        }
        sparklines[ticker] = next;
        lastDirection[ticker] = update.direction;
      }

      return {
        prices,
        sparklines,
        lastDirection,
        version: state.version + 1,
      };
    }),

  setDirection: (ticker, direction) =>
    set((state) => ({
      lastDirection: { ...state.lastDirection, [ticker]: direction },
    })),

  reset: () => set(initialState),
}));

export { MAX_SPARKLINE_POINTS };