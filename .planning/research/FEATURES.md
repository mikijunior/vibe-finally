# Feature Research

**Domain:** AI-Powered Trading Workstation
**Researched:** 2026-06-26
**Confidence:** HIGH

## Feature Landscape

### Table Stakes (Users Expect These)

Features users assume exist. Missing these = product feels incomplete or broken.

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| Live price streaming | Core premise of a trading platform; without real-time updates it feels like a static website | MEDIUM | SSE architecture already designed; simulator is the default |
| Watchlist display | Every trading platform has one; users expect to see symbols they care about | LOW | Grid with ticker, price, change % — straightforward |
| Buy/sell execution | The fundamental action; users cannot trade without it | LOW | Market orders only, instant fill, no confirmation — simplest possible model |
| Portfolio value display | Users need to see their total account value | LOW | Cash + positions value, updates with each price tick |
| Position tracking (ticker, qty, avg cost, current price, P&L) | Users must see what they own and whether they are winning or losing | LOW | All data available in database; rendering is trivial |
| Connection status indicator | Users need confidence the system is live; disconnections should be visible | LOW | SSE EventSource has built-in reconnect; just surface the state |
| Dark terminal aesthetic | Implied by "Bloomberg terminal" framing; a light theme would break immersion | LOW | Tailwind dark theme, specific hex colors defined in plan |
| Cash balance display | Users need to know how much buying power they have | LOW | Displayed in header alongside portfolio value |

### Differentiators (Competitive Advantage)

Features that set the product apart. Not required, but valued — these are where FinAlly competes.

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| AI chat that executes trades via natural language | The core differentiator — user asks "buy 10 AAPL" and it happens; no forms, no confirmation dialogs | MEDIUM | Requires LLM structured output, portfolio context injection, auto-execution, and inline confirmation display |
| AI that proactively manages the watchlist | Extends the "AI as copilot" narrative beyond trading into monitoring | MEDIUM | Same mechanism as trade execution, just with watchlist CRUD |
| Portfolio heatmap (treemap) | Visually striking way to see position sizing and P&L at a glance; most simulators use boring tables | MEDIUM | Treemap library (e.g., D3 or recharts treemap); sizing by weight, coloring by P&L |
| Sparkline mini-charts in watchlist | Prices accumulate visually since page load; gives a sense of momentum without opening a full chart | MEDIUM | Frontend accumulates SSE price points; canvas-based or SVG sparklines |
| Price flash animations (green/red) | Adds life to the terminal; price changes feel immediate and visceral | LOW | CSS transitions, ~500ms fade; class toggled on each SSE update |
| P&L chart (portfolio value over time) | Shows performance narrative; users want to see their portfolio grow or shrink | MEDIUM | Line chart from portfolio_snapshots; recorded every 30s + after each trade |
| Main ticker chart (click to expand) | Lets users inspect a symbol's behavior in detail without leaving the page | MEDIUM | Lightweight Charts or Recharts; SSE stream also carries enough data |
| Chat inline trade confirmations | Makes AI actions visible and trustworthy; user sees exactly what the AI did | LOW | Render the actions array from structured output in the chat panel |

### Anti-Features (Commonly Requested, Often Problematic)

Features that seem appealing but create complexity, confusion, or misalignment with the product goals.

| Feature | Why Requested | Why Problematic | Alternative |
|---------|---------------|-----------------|-------------|
| Real brokerage integration | "Make it feel like a real trading platform" | Introduces regulatory compliance, OAuth brokerage connections, and real financial risk; completely opposite of zero-stakes demo | Keep it as simulated — the fake money is a feature, not a limitation |
| Limit orders | "I want to set a price at which to buy" | Requires order book logic, partial fill handling, cancellation, and expiry; undermines the "dramatically simpler" design principle | Market orders only; the simulator's random events create drama organically |
| Multi-user authentication | "What if two people want to use it?" | Adds login flows, session management, per-user database isolation, and complexity to every API call; goes against single-Docker zero-setup goal | Schema already has user_id — multi-user is a future v2 consideration, not a launch feature |
| Mobile app | "Everyone wants mobile" | Mobile trading terminals are a niche use case; adds native development burden; desktop-first is explicitly the design intent | Responsive browser layout that works on tablet; mobile is explicitly out of scope |
| WebSocket upgrade | "WebSockets are more real-time than SSE" | Bidirectional communication is unnecessary — the server only pushes; WebSockets add connection management complexity, ping/pong keepalives, and reconnection logic | SSE is correct for one-way server→client push; EventSource handles reconnection automatically |
| Order book visualization | "Show me the bid/ask depth" | Requires market data that includes order book (not just last trade price); conflicts with market-order-only model and simulator's price-only approach | Not applicable to last-trade-price data; would confuse more than it helps |
| Multiple chart types (candlestick, volume, indicators) | "Real traders use candlesticks" | Candlestick charts require OHLCV data, not just price; volume requires trade tick data; adds charting library complexity for marginal value | Lightweight Charts for price-over-time is sufficient; simulator generates price only |

## Feature Dependencies

```
[Live Price Streaming (SSE)]
    ├──powers ──> [Watchlist Display]
    │                 └──click ──> [Main Ticker Chart]
    │
    ├──powers ──> [Portfolio Value Display]
    ├──enables ──> [Position P&L Calculation]
    │
    └──feeds ──────> [AI Chat (portfolio context)]
                         ├──executes ──> [Buy/Sell Execution]
                         └──executes ──> [Watchlist Management]

[Portfolio Data]
    ├──renders ──> [Positions Table]
    ├──renders ──> [Portfolio Heatmap (treemap)]
    └──renders ──> [P&L Chart (time series)]

[SSE Price History (frontend)] ──accumulates──> [Sparkline Mini-Charts]

[AI Chat Response (structured output)]
    ├──includes ──> [Chat Inline Trade Confirmations]
    └──includes ──> [Chat Inline Watchlist Confirmations]
```

### Dependency Notes

- **Live Price Streaming enables everything else:** All real-time updates flow from SSE. No streaming = no flash animations, no sparklines, no live P&L. This is Phase 1 infrastructure.
- **Buy/sell execution is independent of AI:** The trade bar (manual trading) should work regardless of whether the AI chat is implemented. These are separate UX paths to the same backend.
- **AI chat requires portfolio context:** The LLM needs current positions, cash, and watchlist prices to give useful responses. This means the chat endpoint must call portfolio + watchlist endpoints first.
- **Heatmap and P&L chart both require portfolio data:** Both are views over the same positions + cash calculation. Build once, surface twice.
- **Sparklines require SSE client-side accumulation:** The server sends only the current price; the frontend must store price history since page load. No additional backend work.

## MVP Definition

### Launch With (v1)

Minimum viable product — what's needed to validate the concept and demonstrate the core AI trading narrative.

- [ ] Live price streaming (SSE) — the entire platform is built on this; nothing else feels alive without it
- [ ] Watchlist grid with ticker, price, daily change % — first thing users see on launch
- [ ] Trade bar (buy/sell with quantity) + position tracking — the fundamental trading loop; must work manually before AI automates it
- [ ] Portfolio value display + positions table — user needs to see their P&L
- [ ] AI chat with trade execution via natural language — the headline differentiator; "ask the AI to buy something and watch it happen"
- [ ] Dark terminal aesthetic with price flash animations — the Bloomberg-style presentation is part of the product identity

### Add After Validation (v1.x)

Features that become obvious gaps once users interact with the MVP.

- [ ] Sparkline mini-charts in watchlist — users will want to see price momentum without clicking through
- [ ] P&L chart (portfolio value over time) — users will ask "how am I doing today?"
- [ ] Main ticker chart (click to expand) — watchlist click should open a real chart
- [ ] Portfolio heatmap (treemap) — adds visual wow factor; good for demos
- [ ] Watchlist management via AI chat — natural extension once chat is live

### Future Consideration (v2+)

Features that require either product-market fit validation or significant new infrastructure.

- [ ] Real market data (Massive API) — simulator is fine for demo; real data becomes relevant if users want genuine analysis
- [ ] Multi-user authentication — only if the platform moves beyond a course capstone
- [ ] Limit orders — only if users consistently ask for price control; market orders are intentional simplicity
- [ ] Mobile layout refinement — tablet is the floor; mobile is aspirational

## Feature Prioritization Matrix

| Feature | User Value | Implementation Cost | Priority |
|---------|------------|---------------------|----------|
| Live price streaming (SSE) | HIGH | MEDIUM | P1 |
| Watchlist display | HIGH | LOW | P1 |
| Trade bar + execution | HIGH | LOW | P1 |
| Portfolio value + positions table | HIGH | LOW | P1 |
| Connection status indicator | MEDIUM | LOW | P1 |
| Dark terminal aesthetic | HIGH | LOW | P1 |
| AI chat with trade execution | HIGH | MEDIUM | P1 |
| Price flash animations | MEDIUM | LOW | P1 |
| Main ticker chart | MEDIUM | MEDIUM | P2 |
| P&L chart (time series) | MEDIUM | MEDIUM | P2 |
| Sparkline mini-charts | MEDIUM | MEDIUM | P2 |
| Portfolio heatmap (treemap) | MEDIUM | MEDIUM | P2 |
| AI watchlist management | MEDIUM | MEDIUM | P2 |
| LLM mock mode for testing | MEDIUM | LOW | P1 |
| Massive API integration | LOW | MEDIUM | P3 |
| Limit orders | LOW | HIGH | P3 |
| Multi-user authentication | LOW | HIGH | P3 |

**Priority key:**
- P1: Must have for launch
- P2: Should have, add when core is stable
- P3: Nice to have, deprioritize until explicit demand

## Competitor Feature Analysis

| Feature | TradingView (Free Tier) | Webull | Robinhood | Our Approach |
|---------|-------------------------|--------|-----------|--------------|
| Live price streaming | YES (with delay on free) | YES | YES | YES — SSE, 500ms, simulator by default |
| Watchlist | YES, highly customizable | YES | YES | YES, 10 default tickers, add/remove |
| Buy/sell execution | NO (paper trading separate) | YES (real) | YES (real) | YES (simulated, fake cash) |
| AI chat | NO | NO | NO | YES — core differentiator |
| Portfolio heatmap | NO | NO | NO | YES — treemap visualization |
| Sparklines in watchlist | NO | NO | NO | YES — progressive accumulation from SSE |
| Price flash animations | NO | Basic | Basic | YES — polished CSS transitions |
| Chart types | Candlestick, line, etc. | Candlestick, line | Candlestick | Line chart only (price-over-time) |
| P&L chart over time | YES (premium feature) | YES | YES | YES — free, from snapshots |
| Market orders only | YES | YES | YES | YES — intentional simplicity |
| Single Docker container | N/A | N/A | N/A | YES — zero-setup for course students |

### Competitive Positioning

FinAlly does not compete with brokerages on trading features. It competes on:
1. **AI integration** — no competitor in this space (retail brokerages have basic chatbots, not trade-executing AI assistants)
2. **Visual polish** — Bloomberg-style aesthetic with flash animations and sparklines is distinctive among simulators
3. **Zero friction** — one Docker command vs. account creation + funding a brokerage account

The target user (coding course student) is not trying to make money — they are demonstrating an AI-powered full-stack application. The fake money and single-container deployment are features that serve this goal.

## Sources

- TradingView.com — competitor feature mapping
- Webull app — competitor feature mapping
- Robinhood app — competitor feature mapping
- planning/PLAN.md — full product specification
- planning/MARKET_DATA_SUMMARY.md — completed market data component
- .planning/PROJECT.md — project context and requirements

---
*Feature research for: AI-Powered Trading Workstation*
*Researched: 2026-06-26*
