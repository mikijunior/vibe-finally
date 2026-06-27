"use client";

import { MainChart } from "@/components/MainChart";
import { WatchlistPanel } from "@/components/WatchlistPanel";

export default function HomePage() {
  return (
    <main className="bg-bg-base min-h-screen w-full p-4">
      <div className="mx-auto flex max-w-[1600px] flex-col gap-4">
        {/* Header placeholder — total value, connection status, and cash balance
            are added in plan 04-02. */}
        <header className="bg-bg-elevated border-border-muted flex items-center justify-between rounded border px-4 py-3">
          <div className="flex items-baseline gap-3">
            <span className="text-accent-yellow font-mono text-xl font-bold tracking-wider">
              FinAlly
            </span>
            <span className="text-text-muted font-mono text-xs uppercase">
              AI Trading Workstation
            </span>
          </div>
          <div className="text-text-muted font-mono text-xs italic">
            Header (portfolio + status) lands in 04-02
          </div>
        </header>

        <div className="grid grid-cols-1 gap-4 lg:grid-cols-[320px_1fr]">
          <aside aria-label="Watchlist">
            <WatchlistPanel />
          </aside>
          <section aria-label="Main chart" className="min-w-0">
            <MainChart />
          </section>
        </div>

        <footer className="bg-bg-elevated border-border-muted rounded border p-4">
          <div className="text-text-muted font-mono text-xs uppercase">
            Portfolio heatmap, P&amp;L chart, positions table, trade bar, and
            chat panel land in 04-02.
          </div>
        </footer>
      </div>
    </main>
  );
}