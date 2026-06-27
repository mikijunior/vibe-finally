/**
 * Portfolio Heatmap — SVG treemap of positions sized by portfolio weight and
 * colored by P&L (green = profit, red = loss). Tiles overlap cleanly because
 * positions are laid out via a recursive slice-and-dice algorithm.
 *
 * Live price overrides the server-supplied current_price so the heatmap
 * updates between REST refreshes.
 */

"use client";

import { useMemo } from "react";

import { formatPercent } from "@/lib/format";
import { usePortfolio } from "@/lib/hooks/usePortfolio";
import { usePriceStore } from "@/lib/store";
import type { Position } from "@/lib/types";

interface Tile {
  ticker: string;
  x: number;
  y: number;
  width: number;
  height: number;
  weight: number;
  pnlPercent: number;
  pnlUp: boolean;
}

const COLOR_UP = "#22c55e";
const COLOR_DOWN = "#ef4444";

/**
 * Slice-and-dice treemap: split the rectangle alternately along the longer
 * axis. Each split divides the current row/column into a "this tile" slice
 * proportional to its weight and a remainder to recurse into.
 */
function layout(
  items: Array<{ ticker: string; weight: number; pnlPercent: number; pnlUp: boolean }>,
  x: number,
  y: number,
  width: number,
  height: number,
  vertical: boolean,
): Tile[] {
  if (items.length === 0) return [];
  if (items.length === 1) {
    const it = items[0];
    return [
      {
        ticker: it.ticker,
        x,
        y,
        width,
        height,
        weight: it.weight,
        pnlPercent: it.pnlPercent,
        pnlUp: it.pnlUp,
      },
    ];
  }

  const total = items.reduce((s, i) => s + i.weight, 0);
  if (total <= 0) {
    // Fall back to equal-area squares if all weights are zero/negative.
    return equalFallback(items, x, y, width, height);
  }

  // Pick a pivot so the first slice fills ~half of the area. This is a
  // simple "best split by accumulated weight" that gives a reasonable layout
  // without pulling in a full squarify implementation.
  let acc = 0;
  let splitIndex = 1;
  const target = total / 2;
  for (let i = 0; i < items.length - 1; i += 1) {
    acc += items[i].weight;
    if (acc >= target) {
      splitIndex = i + 1;
      break;
    }
  }

  const left = items.slice(0, splitIndex);
  const right = items.slice(splitIndex);
  const leftWeight = left.reduce((s, i) => s + i.weight, 0);

  if (vertical) {
    const leftWidth = (leftWeight / total) * width;
    return [
      ...layout(left, x, y, leftWidth, height, !vertical),
      ...layout(right, x + leftWidth, y, width - leftWidth, height, !vertical),
    ];
  }
  const leftHeight = (leftWeight / total) * height;
  return [
    ...layout(left, x, y, width, leftHeight, !vertical),
    ...layout(right, x, y + leftHeight, width, height - leftHeight, !vertical),
  ];
}

function equalFallback(
  items: Array<{ ticker: string; weight: number; pnlPercent: number; pnlUp: boolean }>,
  x: number,
  y: number,
  width: number,
  height: number,
): Tile[] {
  const perRow = Math.ceil(Math.sqrt(items.length));
  const cellW = width / perRow;
  const rows = Math.ceil(items.length / perRow);
  const cellH = height / rows;
  return items.map((it, idx) => {
    const col = idx % perRow;
    const row = Math.floor(idx / perRow);
    return {
      ticker: it.ticker,
      x: x + col * cellW,
      y: y + row * cellH,
      width: cellW,
      height: cellH,
      weight: 1,
      pnlPercent: it.pnlPercent,
      pnlUp: it.pnlUp,
    };
  });
}

function opacityFor(pnlPercent: number): number {
  const mag = Math.min(Math.abs(pnlPercent) / 10, 1);
  // Clamp into [0.2, 1.0] so even flat positions remain visible.
  return Math.max(0.2, 0.2 + 0.8 * mag);
}

export function PortfolioHeatmap() {
  const { portfolio } = usePortfolio();
  const prices = usePriceStore((s) => s.prices);

  const tiles: Tile[] = useMemo(() => {
    if (!portfolio || portfolio.positions.length === 0) return [];
    const enriched = portfolio.positions
      .map((p: Position) => {
        const live = prices[p.ticker]?.price;
        const price = live ?? p.current_price;
        return {
          ticker: p.ticker,
          weight: p.quantity * price,
          pnlPercent: p.pnl_percent,
          pnlUp: p.unrealized_pnl >= 0,
        };
      })
      // Largest weight first — improves the slice-and-dice layout.
      .sort((a, b) => b.weight - a.weight);

    return layout(enriched, 0, 0, 100, 100, true);
  }, [portfolio, prices]);

  if (!portfolio) {
    return (
      <div className="bg-bg-elevated border-border-muted flex h-64 items-center justify-center rounded border p-2">
        <span className="text-text-muted font-mono text-xs">Loading portfolio…</span>
      </div>
    );
  }

  if (tiles.length === 0) {
    return (
      <div
        className="bg-bg-elevated border-border-muted flex h-64 flex-col items-center justify-center rounded border p-2"
        data-testid="portfolio-heatmap-empty"
      >
        <span className="text-text-muted font-mono text-xs uppercase tracking-wider">
          No positions yet
        </span>
        <span className="text-text-muted mt-1 font-mono text-[10px] italic">
          Use the trade bar below to open a position.
        </span>
      </div>
    );
  }

  return (
    <div className="bg-bg-elevated border-border-muted flex h-64 flex-col gap-2 rounded border p-2">
      <div className="flex items-baseline justify-between">
        <span className="text-text-muted font-mono text-[10px] uppercase tracking-wider">
          Portfolio Heatmap
        </span>
        <span className="text-text-muted font-mono text-[10px] italic">
          weight × P&amp;L
        </span>
      </div>
      <div className="min-h-0 flex-1">
        <svg
          viewBox="0 0 100 100"
          preserveAspectRatio="none"
          className="h-full w-full"
          role="img"
          aria-label="Portfolio heatmap"
          data-testid="portfolio-heatmap"
        >
          {tiles.map((tile) => {
            const fill = tile.pnlUp ? COLOR_UP : COLOR_DOWN;
            return (
              <g key={tile.ticker}>
                <rect
                  x={tile.x}
                  y={tile.y}
                  width={Math.max(tile.width - 0.4, 0)}
                  height={Math.max(tile.height - 0.4, 0)}
                  fill={fill}
                  fillOpacity={opacityFor(tile.pnlPercent)}
                  stroke="#0d1117"
                  strokeWidth={0.2}
                />
                {tile.width > 8 && tile.height > 6 ? (
                  <text
                    x={tile.x + tile.width / 2}
                    y={tile.y + tile.height / 2}
                    textAnchor="middle"
                    dominantBaseline="middle"
                    fill="#0d1117"
                    fontFamily="ui-monospace, SFMono-Regular, Menlo, monospace"
                    fontSize={Math.max(2.4, Math.min(4, tile.width / 4))}
                    fontWeight="700"
                  >
                    {tile.ticker} {formatPercent(tile.pnlPercent, 1)}
                  </text>
                ) : null}
              </g>
            );
          })}
        </svg>
      </div>
    </div>
  );
}
