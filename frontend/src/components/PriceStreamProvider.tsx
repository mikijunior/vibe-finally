/**
 * Mounts the SSE price-stream connection at the root of the app tree.
 *
 * Render once near the top of the layout so the EventSource is opened as
 * soon as React hydrates. Components elsewhere read from `usePriceStore`
 * to access live prices.
 */

"use client";

import { usePriceStream } from "@/lib/price-stream";

interface PriceStreamProviderProps {
  children: React.ReactNode;
}

export function PriceStreamProvider({ children }: PriceStreamProviderProps) {
  // Side effect-only hook — opens the singleton EventSource and tracks
  // connection status. The return value is unused here; consumers can call
  // usePriceStream() if they need the status, or read prices from
  // usePriceStore directly.
  usePriceStream();
  return <>{children}</>;
}