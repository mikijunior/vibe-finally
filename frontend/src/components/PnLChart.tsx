/**
 * P&L Chart — area chart of total portfolio value over time, sourced from
 * /api/portfolio/history.
 *
 * Lightweight Charts areaSeries with the dark theme tuned to the FinAlly
 * color tokens. Uses series.update() so future snapshot records stream into
 * the chart without a full setData() reset.
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

import { usePortfolioHistory } from "@/lib/hooks/usePortfolio";

const COLOR_LINE = "#209dd7";
const COLOR_TOP = "rgba(32, 157, 215, 0.35)";
const COLOR_BOTTOM = "rgba(32, 157, 215, 0)";

export function PnLChart() {
  const { history, isLoading } = usePortfolioHistory();

  const containerRef = useRef<HTMLDivElement | null>(null);
  const chartRef = useRef<IChartApi | null>(null);
  const seriesRef = useRef<ISeriesApi<"Area"> | null>(null);
  const lastTimeRef = useRef<UTCTimestamp | null>(null);
  const seededTickerRef = useRef<number>(0);

  // Create the chart once on mount; tear it down on unmount.
  useEffect(() => {
    const container = containerRef.current;
    if (!container) return undefined;

    const chart = createChart(container, {
      width: container.clientWidth || 400,
      height: 240,
      layout: {
        background: { color: "transparent" },
        textColor: "#8b95a5",
      },
      grid: {
        vertLines: { color: "#2a2f3a" },
        horzLines: { color: "#2a2f3a" },
      },
      timeScale: {
        borderColor: "#2a2f3a",
        timeVisible: true,
        secondsVisible: true,
      },
      rightPriceScale: {
        borderColor: "#2a2f3a",
      },
      handleScroll: true,
      handleScale: true,
    });

    const series = chart.addSeries(AreaSeries, {
      lineColor: COLOR_LINE,
      topColor: COLOR_TOP,
      bottomColor: COLOR_BOTTOM,
      lineWidth: 2,
      priceLineVisible: false,
      lastValueVisible: true,
    });

    chartRef.current = chart;
    seriesRef.current = series;
    lastTimeRef.current = null;
    seededTickerRef.current = 0;

    const handleResize = () => {
      if (containerRef.current && chartRef.current) {
        chartRef.current.applyOptions({
          width: containerRef.current.clientWidth,
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
      seededTickerRef.current = 0;
    };
  }, []);

  // Seed / append the snapshot series whenever history changes.
  useEffect(() => {
    const series = seriesRef.current;
    if (!series || !history) return;

    const snapshots = history.snapshots;
    if (snapshots.length === 0) {
      return;
    }

    // Detect a brand-new fetch (data length grew past the previously-seeded
    // count OR the snapshots themselves changed in a way that re-orders).
    const seedKey = snapshots.length;
    const isFreshSeed = seededTickerRef.current !== seedKey;

    if (isFreshSeed) {
      seededTickerRef.current = seedKey;
      lastTimeRef.current = null;

      // Lightweight Charts requires strictly non-decreasing times. Snapshots
      // are already ASC by recorded_at but they can collide on the second,
      // so we synthesize a monotonic cursor and discard duplicates.
      const points: Array<{ time: UTCTimestamp; value: number }> = [];
      let cursor = 0 as UTCTimestamp;
      for (const snap of snapshots) {
        const t = Math.floor(new Date(snap.recorded_at).getTime() / 1000);
        if (!Number.isFinite(t)) continue;
        const safe = (Math.max(cursor + 1, t) as UTCTimestamp);
        if (safe <= cursor) continue;
        cursor = safe;
        points.push({ time: safe, value: snap.total_value });
      }

      if (points.length === 0) return;

      try {
        series.setData(points);
        chartRef.current?.timeScale().fitContent();
      } catch {
        // Defensive: fall back to incremental updates on the next tick.
      }
      lastTimeRef.current = points[points.length - 1].time;
      return;
    }

    // Live append path: add only points newer than what we've already drawn.
    const lastDrawn = lastTimeRef.current;
    if (lastDrawn === null) return;

    let cursor = lastDrawn;
    for (const snap of snapshots) {
      const t = Math.floor(new Date(snap.recorded_at).getTime() / 1000);
      if (!Number.isFinite(t)) continue;
      const safe = (Math.max(cursor + 1, t) as UTCTimestamp);
      if (safe <= cursor) continue;
      try {
        series.update({ time: safe, value: snap.total_value });
        cursor = safe;
      } catch {
        break;
      }
    }
    lastTimeRef.current = cursor;
  }, [history]);

  const hasData = (history?.snapshots.length ?? 0) > 0;

  return (
    <div className="bg-bg-elevated border-border-muted flex h-64 flex-col gap-2 rounded border p-2">
      <div className="flex items-baseline justify-between">
        <span className="text-text-muted font-mono text-[10px] uppercase tracking-wider">
          Portfolio Value Over Time
        </span>
        <span className="text-text-muted font-mono text-[10px] italic">
          {hasData ? `${history?.snapshots.length} snapshots` : "awaiting data"}
        </span>
      </div>
      <div className="relative min-h-0 flex-1">
        {!hasData ? (
          <div className="text-text-muted absolute inset-0 flex items-center justify-center font-mono text-xs italic">
            {isLoading ? "Loading history…" : "Waiting for first snapshot…"}
          </div>
        ) : null}
        <div
          ref={containerRef}
          className="h-full w-full"
          data-testid="pnl-chart"
        />
      </div>
    </div>
  );
}
