/**
 * Mini canvas sparkline using Lightweight Charts.
 *
 * Reads the rolling sparkline buffer from the price store and appends new
 * points via `series.update()` (NOT `setData()` — see TradingView guidance on
 * real-time performance). The chart is sized to 80x32 and has all chrome
 * hidden so it composes cleanly inside a table row.
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

interface SparklineProps {
  ticker: string;
  width?: number;
  height?: number;
  timestamp?: number; // epoch seconds — defaults to wall clock for new points
}

const COLOR_UP = "#22c55e";
const COLOR_DOWN = "#ef4444";

export function Sparkline({
  ticker,
  width = 80,
  height = 32,
  timestamp,
}: SparklineProps) {
  const containerRef = useRef<HTMLDivElement | null>(null);
  const chartRef = useRef<IChartApi | null>(null);
  const seriesRef = useRef<ISeriesApi<"Area"> | null>(null);
  const lastTimeRef = useRef<UTCTimestamp | null>(null);
  const bufferRef = useRef<number[]>([]);

  const points = usePriceStore((s) => s.sparklines[ticker] ?? []);

  // Create the chart once per ticker. Remove on unmount or ticker change.
  useEffect(() => {
    const container = containerRef.current;
    if (!container) return undefined;

    const chart = createChart(container, {
      width,
      height,
      layout: {
        background: { color: "transparent" },
        textColor: "transparent",
      },
      grid: {
        vertLines: { visible: false },
        horzLines: { visible: false },
      },
      timeScale: {
        visible: false,
        borderVisible: false,
      },
      rightPriceScale: {
        visible: false,
        borderVisible: false,
      },
      handleScroll: false,
      handleScale: false,
      crosshair: {
        vertLine: { visible: false },
        horzLine: { visible: false },
      },
    });

    const series = chart.addSeries(AreaSeries, {
      lineColor: COLOR_UP,
      topColor: "rgba(34, 197, 94, 0.3)",
      bottomColor: "transparent",
      lineWidth: 1,
      priceLineVisible: false,
      lastValueVisible: false,
    });

    chartRef.current = chart;
    seriesRef.current = series;
    lastTimeRef.current = null;
    bufferRef.current = [];

    return () => {
      chart.remove();
      chartRef.current = null;
      seriesRef.current = null;
      lastTimeRef.current = null;
      bufferRef.current = [];
    };
  }, [ticker, width, height]);

  // Append new points whenever the buffer grows.
  useEffect(() => {
    const series = seriesRef.current;
    if (!series) return;

    const buffer = bufferRef.current;
    const existingLen = buffer.length;
    const newPoints = points.length > existingLen ? points.slice(existingLen) : [];

    if (newPoints.length === 0) return;

    // Recolor the line based on overall direction in the visible window.
    const first = buffer[0] ?? points[0];
    const last = points[points.length - 1];
    const lineColor = last >= first ? COLOR_UP : COLOR_DOWN;
    series.applyOptions({
      lineColor,
      topColor:
        last >= first ? "rgba(34, 197, 94, 0.3)" : "rgba(239, 68, 68, 0.3)",
    });

    // Synthesize monotonically-increasing timestamps for the sparkline so
    // lightweight-charts accepts the points (it requires non-decreasing
    // times). The backend sends epoch seconds per tick; we use them when
    // provided, otherwise derive from the SSE rate (~500ms).
    let cursor = (lastTimeRef.current ?? 0) as UTCTimestamp;
    const now = timestamp ?? Math.floor(Date.now() / 1000);

    for (const value of newPoints) {
      // Ensure strictly non-decreasing times. If a point arrives with the
      // same timestamp as the previous one, skip the update.
      const t = Math.max(cursor + 1, now) as UTCTimestamp;
      if (t <= cursor) continue;
      try {
        series.update({ time: t, value });
        cursor = t;
      } catch {
        // Defensive: ignore out-of-order updates; lightweight-charts will
        // accept the next valid tick.
        break;
      }
    }

    lastTimeRef.current = cursor;
    bufferRef.current = points.slice();
  }, [points, timestamp]);

  return (
    <div
      ref={containerRef}
      style={{ width, height }}
      className="rounded"
      data-testid={`sparkline-${ticker}`}
    />
  );
}