"use client";

import useSWR from "swr";

import { getWatchlist } from "@/lib/api";
import type { WatchlistResponse } from "@/lib/types";

export interface UseWatchlistResult {
  entries: WatchlistResponse["entries"];
  error: Error | undefined;
  isLoading: boolean;
  mutate: () => Promise<WatchlistResponse | undefined>;
}

export function useWatchlist(): UseWatchlistResult {
  const { data, error, isLoading, mutate } = useSWR<WatchlistResponse>(
    "watchlist",
    getWatchlist,
    {
      refreshInterval: 0,
      revalidateOnFocus: true,
      dedupingInterval: 1000,
    },
  );

  return {
    entries: data?.entries ?? [],
    error,
    isLoading,
    mutate: async () => mutate(),
  };
}