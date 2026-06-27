/**
 * Dashboard layout — composes the six new components (Header,
 * PortfolioHeatmap, PnLChart, PositionsTable, TradeBar, ChatPanel) alongside
 * the WatchlistPanel + MainChart from Plan 04-01.
 *
 * The page is a single full-height CSS grid:
 *   row 1: Header (auto height)
 *   row 2: WatchlistPanel + MainChart (1fr)
 *   row 3: PortfolioHeatmap + PnLChart + PositionsTable (auto, h-64)
 *   row 4: TradeBar + ChatPanel (auto)
 * `h-screen overflow-hidden` keeps each region scrolling independently so
 * the dashboard never grows past the viewport.
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

export default function HomePage() {
  return (
    <main className="bg-bg-base text-text-primary grid h-screen grid-rows-[auto_1fr_auto_auto] overflow-hidden">
      {/* Row 1 — header */}
      <div className="p-2 pb-0">
        <Header />
      </div>

      {/* Row 2 — watchlist + main chart */}
      <div className="grid min-h-0 grid-cols-1 gap-2 p-2 lg:grid-cols-[320px_1fr]">
        <aside aria-label="Watchlist" className="min-h-0">
          <WatchlistPanel />
        </aside>
        <section aria-label="Main chart" className="min-h-0">
          <MainChart />
        </section>
      </div>

      {/* Row 3 — portfolio visualizations */}
      <div className="grid min-h-0 grid-cols-1 gap-2 px-2 md:grid-cols-3">
        <PortfolioHeatmap />
        <PnLChart />
        <PositionsTable />
      </div>

      {/* Row 4 — trade bar + chat panel */}
      <div className="grid min-h-0 grid-cols-1 gap-2 p-2 lg:grid-cols-[1fr_320px]">
        <TradeBar />
        <ChatPanel />
      </div>
    </main>
  );
}
