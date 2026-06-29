/**
 * Main chart area — Lightweight Charts areaSeries for the currently selected
 * ticker. Subscribes to the price + sparkline slices of the store and feeds
 * new points via `series.update()`.
 *
 * The chart recreates whenever the selected ticker changes so the time
 * scale resets cleanly to the new instrument's history.
 */

"use client";

import { useEffect, useRef } from "react";
import {
  AreaSeries,
  createChart,
  type IChartApi,
  type ISeriesApi,
  type UTCTimestamp,
} from "lightweight-charts";

import { usePriceStore } from "@/lib/store";
import { useSelectedTicker } from "@/lib/hooks/useSelectedTicker";

const COLOR_UP = "#22c55e";
const COLOR_DOWN = "#ef4444";

// Stable empty-array reference — returning a fresh `[]` literal here would
// trigger React 19's "getServerSnapshot should be cached" infinite-loop guard
// because Zustand would see a new reference on every render.
const EMPTY_SPARKLINE: number[] = [];

export function MainChart() {
  const selectedTicker = useSelectedTicker((s) => s.selectedTicker);
  const prices = usePriceStore((s) =>
    selectedTicker ? s.prices[selectedTicker] : undefined,
  );
  const sparkline = usePriceStore((s) =>
    selectedTicker ? s.sparklines[selectedTicker] ?? EMPTY_SPARKLINE : EMPTY_SPARKLINE,
  );

  const containerRef = useRef<HTMLDivElement | null>(null);
  const chartRef = useRef<IChartApi | null>(null);
  const seriesRef = useRef<ISeriesApi<"Area"> | null>(null);
  const lastTimeRef = useRef<UTCTimestamp | null>(null);
  const initialBufferAppliedRef = useRef<string | null>(null);

  // Create the chart when the ticker changes; destroy on unmount.
  useEffect(() => {
    const container = containerRef.current;
    if (!container) return undefined;

    const chart = createChart(container, {
      width: container.clientWidth || 600,
      height: container.clientHeight || 360,
      layout: {
        background: { color: "#0b0e14" },
        textColor: "#7d8a9b",
        attributionLogo: false,
      },
      grid: {
        vertLines: { color: "#243043" },
        horzLines: { color: "#243043" },
      },
      timeScale: {
        borderColor: "#243043",
        timeVisible: true,
        secondsVisible: true,
      },
      rightPriceScale: {
        borderColor: "#243043",
      },
    });

    const series = chart.addSeries(AreaSeries, {
      lineColor: COLOR_UP,
      topColor: "rgba(34, 197, 94, 0.25)",
      bottomColor: "rgba(34, 197, 94, 0)",
      lineWidth: 2,
      priceLineVisible: false,
      lastValueVisible: true,
    });

    chartRef.current = chart;
    seriesRef.current = series;
    lastTimeRef.current = null;
    initialBufferAppliedRef.current = null;

    const handleResize = () => {
      if (containerRef.current && chartRef.current) {
        chartRef.current.applyOptions({
          width: containerRef.current.clientWidth,
          height: containerRef.current.clientHeight,
        });
      }
    };
    window.addEventListener("resize", handleResize);

    return () => {
      window.removeEventListener("resize", handleResize);
      chart.remove();
      chartRef.current = null;
      seriesRef.current = null;
      lastTimeRef.current = null;
      initialBufferAppliedRef.current = null;
    };
  }, [selectedTicker]);

  // Replay the existing sparkline buffer once when the ticker (re)selects,
  // and append new points as they arrive.
  useEffect(() => {
    const series = seriesRef.current;
    if (!series || !selectedTicker) return;

    const ticker = selectedTicker;

    // First time we see this ticker in this chart: seed with the buffer.
    if (initialBufferAppliedRef.current !== ticker) {
      initialBufferAppliedRef.current = ticker;
      lastTimeRef.current = null;

      if (sparkline.length > 0) {
        let cursor = 0 as UTCTimestamp;
        // Anchor the seeded buffer to "now" minus one tick per point so the
        // curve fills the visible window right-to-left.
        const now = Math.floor(Date.now() / 1000);
        const startTime = (now - sparkline.length) as UTCTimestamp;

        const points = sparkline.map((value, i) => ({
          time: (startTime + i) as UTCTimestamp,
          value,
        }));

        // Track monotonic lastTime so live updates don't collide with the seed.
        cursor = points[points.length - 1].time;

        try {
          series.setData(points);
        } catch {
          // Defensive: lightweight-charts throws if points are not strictly
          // increasing. Drop and start fresh on the next live update.
        }

        const first = points[0].value;
        const last = points[points.length - 1].value;
        series.applyOptions({
          lineColor: last >= first ? COLOR_UP : COLOR_DOWN,
          topColor:
            last >= first ? "rgba(34, 197, 94, 0.25)" : "rgba(239, 68, 68, 0.25)",
        });

        try {
          chartRef.current?.timeScale().fitContent();
        } catch {
          // No-op if the chart is mid-render.
        }

        lastTimeRef.current = cursor;
      }
      return;
    }

    // Live update path: append the latest point only (the buffer grows by
    // exactly one point per SSE event in steady state).
    if (!prices) return;

    const now = Math.floor(prices.timestamp || Date.now() / 1000) as UTCTimestamp;
    const cursor = (lastTimeRef.current ?? now - 1) as UTCTimestamp;
    const t = (Math.max(cursor + 1, now) as UTCTimestamp);

    if (t <= cursor) return; // skip duplicates

    try {
      series.update({ time: t, value: prices.price });
    } catch {
      return; // Out-of-order; the next tick will catch up.
    }
    lastTimeRef.current = t;

    // Recolor based on the latest change.
    const isUp = prices.change >= 0;
    series.applyOptions({
      lineColor: isUp ? COLOR_UP : COLOR_DOWN,
      topColor: isUp ? "rgba(34, 197, 94, 0.25)" : "rgba(239, 68, 68, 0.25)",
    });
  }, [sparkline, prices, selectedTicker]);

  if (!selectedTicker) {
    return (
      <div className="bg-bg-elevated border-border-muted flex h-full min-h-0 w-full items-center justify-center rounded border">
        <span className="text-text-muted font-mono text-sm">
          Select a ticker from the watchlist to view its chart.
        </span>
      </div>
    );
  }

  return (
    <div className="bg-bg-elevated border-border-muted flex h-full min-h-0 w-full flex-col gap-2 rounded border p-3">
      <div className="flex items-baseline justify-between">
        <span className="text-text-primary font-mono text-lg font-bold">
          {selectedTicker}
        </span>
        {prices ? (
          <span className="text-text-muted font-mono text-sm">
            Live • {Math.round(prices.price * 100) / 100}
          </span>
        ) : (
          <span className="text-text-muted font-mono text-sm italic">
            Waiting for first tick…
          </span>
        )}
      </div>
      <div ref={containerRef} className="min-h-0 flex-1" />
    </div>
  );
}