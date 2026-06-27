"use client";

import useSWR from "swr";

import { getPortfolio, getPortfolioHistory } from "@/lib/api";
import type {
  PortfolioHistoryResponse,
  PortfolioResponse,
} from "@/lib/types";

/** Live portfolio snapshot (cash, positions, total value). */
export function usePortfolio() {
  const { data, error, isLoading, mutate } = useSWR<PortfolioResponse>(
    "portfolio",
    getPortfolio,
    {
      refreshInterval: 5000,
      revalidateOnFocus: true,
      dedupingInterval: 1000,
    },
  );

  return {
    portfolio: data,
    error,
    isLoading,
    mutate,
  };
}

/** Historical portfolio value snapshots (for P&L chart). */
export function usePortfolioHistory() {
  const { data, error, isLoading, mutate } = useSWR<PortfolioHistoryResponse>(
    "portfolio-history",
    getPortfolioHistory,
    {
      refreshInterval: 30000,
      revalidateOnFocus: false,
      dedupingInterval: 5000,
    },
  );

  return {
    history: data,
    error,
    isLoading,
    mutate,
  };
}