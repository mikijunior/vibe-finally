/**
 * Dashboard layout — single-viewport trading terminal.
 *
 *   ┌──────────────────────────────────────────────────────────────────┐
 *   │ Header (auto)                                                    │
 *   ├─────────────────────────────┬────────────────────────────────────┤
 *   │   Workspace (1fr column)    │   Chat panel                       │
 *   │   row1: WL | Chart          │     — 400px tall, full body height │
 *   │   row2: Analytics band 220  │                                    │
 *   │   row3: Trade bar auto      │                                    │
 *   │                             │     — collapsed: 48px rail         │
 *   └─────────────────────────────┴────────────────────────────────────┘
 *
 * Whole dashboard: 2-row grid (header / body). Body: 2-column grid
 * (workspace | chat). Workspace: 2-col × 3-row grid. Chat: single column
 * spanning the full body height.
 */

"use client";

import { ChatPanel } from "@/components/ChatPanel";
import { Header } from "@/components/Header";
import { MainChart } from "@/components/MainChart";
import { PnLChart } from "@/components/PnLChart";
import { PortfolioHeatmap } from "@/components/PortfolioHeatmap";
import { PositionsTable } from "@/components/PositionsTable";
import { TradeBar } from "@/components/TradeBar";
import { WatchlistPanel } from "@/components/WatchlistPanel";
import { useChatPanelCollapsed } from "@/lib/hooks/useChatPanelCollapsed";

export default function HomePage() {
  const chatCollapsed = useChatPanelCollapsed((s) => s.collapsed);
  const chatColClass = chatCollapsed
    ? "grid-cols-[1fr_48px]"
    : "grid-cols-[1fr_400px]";

  return (
    <main className="text-text-primary grid h-screen grid-rows-[auto_1fr] overflow-hidden bg-[#0b0e14]">
      {/* Header band — single full-width row */}
      <header className="px-3 pt-2 pb-1.5">
        <Header />
      </header>

      {/* Body — workspace | chat. Both columns are min-h-0 so their inner
          regions can scroll/use fractional heights without expanding. */}
      <div className={`grid min-h-0 gap-2 px-3 pb-3 ${chatColClass}`}>
        {/* Workspace: 2 cols × 3 rows.
            Row 1: Watchlist (260) | MainChart (1fr, fills remaining)
            Row 2: Analytics band 220px tall — Heatmap / PnLChart / Positions
            Row 3: TradeBar (auto height, full width) */}
        <section
          aria-label="Workspace"
          className="grid min-h-0 grid-cols-[260px_1fr] grid-rows-[minmax(0,1fr)_220px_auto] gap-2"
        >
          {/* Row 1 */}
          <div className="col-start-1 row-start-1 min-h-0">
            <WatchlistPanel />
          </div>
          <div className="col-start-2 row-start-1 min-h-0">
            <MainChart />
          </div>

          {/* Row 2 — analytics band spans both columns; three equal widgets */}
          <div className="col-span-2 col-start-1 row-start-2 grid min-h-0 grid-cols-3 gap-2">
            <PortfolioHeatmap />
            <PnLChart />
            <PositionsTable />
          </div>

          {/* Row 3 — trade bar spans both columns */}
          <div className="col-span-2 col-start-1 row-start-3">
            <TradeBar />
          </div>
        </section>

        {/* Chat column — full-height of body row */}
        <aside aria-label="Chat panel" className="min-h-0 overflow-hidden">
          <ChatPanel />
        </aside>
      </div>
    </main>
  );
}