/**
 * Zustand store for the currently selected ticker — drives the main chart.
 *
 * Stored separately from the price store so selection state survives price
 * updates and re-renders. Default null (no selection; user must click).
 */

"use client";

import { create } from "zustand";

export interface SelectedTickerState {
  selectedTicker: string | null;
}

export interface SelectedTickerActions {
  set: (ticker: string) => void;
  clear: () => void;
}

export type SelectedTickerStore = SelectedTickerState & SelectedTickerActions;

export const useSelectedTicker = create<SelectedTickerStore>((set) => ({
  selectedTicker: null,
  set: (ticker) => set({ selectedTicker: ticker.trim().toUpperCase() }),
  clear: () => set({ selectedTicker: null }),
}));