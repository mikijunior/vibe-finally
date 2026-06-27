/**
 * Live price display with brief green/red flash on direction change.
 *
 * Subscribes to two slices of the price store: the latest price and the last
 * direction. When direction changes, applies a 500ms CSS animation class.
 */

"use client";

import { useEffect, useRef, useState } from "react";

import { formatDollars, formatPercent } from "@/lib/format";
import { usePriceStore } from "@/lib/store";
import type { PriceDirection } from "@/lib/types";

interface PriceCellProps {
  ticker: string;
}

const FLASH_DURATION_MS = 500;

export function PriceCell({ ticker }: PriceCellProps) {
  const price = usePriceStore((s) => s.prices[ticker]);
  const direction = usePriceStore((s) => s.lastDirection[ticker]);
  const [flashClass, setFlashClass] = useState<string>("");
  const previousDirection = useRef<PriceDirection | undefined>(undefined);
  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  useEffect(() => {
    if (!direction) return;
    if (previousDirection.current === direction) return;
    previousDirection.current = direction;

    if (direction === "up") {
      setFlashClass("flash-up");
    } else if (direction === "down") {
      setFlashClass("flash-down");
    } else {
      return; // "flat" / "unchanged" — no animation
    }

    if (timerRef.current) clearTimeout(timerRef.current);
    timerRef.current = setTimeout(() => {
      setFlashClass("");
      timerRef.current = null;
    }, FLASH_DURATION_MS);
  }, [direction]);

  useEffect(() => {
    return () => {
      if (timerRef.current) clearTimeout(timerRef.current);
    };
  }, []);

  if (!price) {
    return (
      <div className="text-text-muted flex flex-col">
        <span className="font-mono text-sm">$--.--</span>
        <span className="font-mono text-xs">--</span>
      </div>
    );
  }

  const changePct = price.change_percent ?? 0;
  const isUp = changePct > 0;
  const isDown = changePct < 0;

  return (
    <div className={`flex flex-col rounded px-1 ${flashClass}`}>
      <span className="font-mono text-sm tabular-nums">
        {formatDollars(price.price)}
      </span>
      <span
        className={`font-mono text-xs tabular-nums ${
          isUp
            ? "text-pnl-up"
            : isDown
              ? "text-pnl-down"
              : "text-text-muted"
        }`}
      >
        {formatPercent(changePct)}
      </span>
    </div>
  );
}