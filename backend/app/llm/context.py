"""Build the portfolio context dict that gets injected into the LLM prompt.

This is the data the LLM sees alongside the user's message so it can answer
portfolio questions, suggest trades, and manage the watchlist in a way that
reflects current state. All monetary values are dollars (float) — not cents.
"""

from __future__ import annotations

from typing import Any


async def build_portfolio_context(
    price_cache: Any,
    user_repo: Any,
    position_repo: Any,
    trade_repo: Any,
    watchlist_repo: Any,
) -> dict[str, Any]:
    """Assemble a JSON-serializable snapshot of the user's portfolio.

    Returns a dict with these keys:

    - ``cash_balance_dollars`` (float)
    - ``total_value_dollars`` (float) — cash + mark-to-market of all positions
    - ``positions`` (list of dicts) — one row per held ticker with live price,
      unrealized P&L, and percent return.
    - ``watchlist`` (list of dicts) — ticker + current price.
    - ``recent_trades`` (list of dicts) — up to 5 most recent trades.

    Missing prices default to ``0.0`` so the LLM always sees a numeric value.
    """
    # 1. Cash balance
    user = await user_repo.get()
    if user is None:
        cash_balance_dollars = 0.0
    else:
        cash_balance_dollars = float(user["cash_balance"])

    # 2. Positions with live mark-to-market
    positions_data: list[dict[str, Any]] = []
    positions_value = 0.0
    pos_rows = await position_repo.get_all()
    for pos in pos_rows:
        ticker = pos["ticker"]
        quantity = float(pos["quantity"])
        avg_cost = float(pos["avg_cost"])
        current_price = price_cache.get_price(ticker) or 0.0

        if avg_cost > 0:
            unrealized_pnl = (current_price - avg_cost) * quantity
            pnl_percent = (current_price - avg_cost) / avg_cost * 100.0
        else:
            unrealized_pnl = 0.0
            pnl_percent = 0.0

        positions_value += current_price * quantity
        positions_data.append(
            {
                "ticker": ticker,
                "quantity": quantity,
                "avg_cost": avg_cost,
                "current_price": current_price,
                "unrealized_pnl": unrealized_pnl,
                "pnl_percent": pnl_percent,
            }
        )

    # 3. Watchlist with current prices
    watchlist_rows = await watchlist_repo.get_all()
    watchlist_data: list[dict[str, Any]] = [
        {
            "ticker": row["ticker"],
            "price": price_cache.get_price(row["ticker"]) or 0.0,
        }
        for row in watchlist_rows
    ]

    # 4. Recent trades (last 5, newest first from the repo)
    recent_trades = await trade_repo.list_recent(limit=5)

    # 5. Total portfolio value
    total_value_dollars = cash_balance_dollars + positions_value

    return {
        "cash_balance_dollars": cash_balance_dollars,
        "total_value_dollars": total_value_dollars,
        "positions": positions_data,
        "watchlist": watchlist_data,
        "recent_trades": recent_trades,
    }