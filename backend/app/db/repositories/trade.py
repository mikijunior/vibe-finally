"""Repository for trades table."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from ..cents import from_cents, to_cents
from ..connection import get_db


class TradeRepository:
    """Repository for trades operations.

    All price values cross the API boundary as dollars (float),
    but are stored in the DB as integer cents.
    """

    USER_ID = "default"

    async def insert(self, ticker: str, side: str, quantity: float, price_dollars: float) -> dict:
        """Record a new trade. Returns the inserted row with price in dollars."""
        db = await get_db()
        now = datetime.now(timezone.utc).isoformat()
        id_ = str(uuid.uuid4())
        await db.execute(
            "INSERT INTO trades (id, user_id, ticker, side, quantity, price, executed_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (id_, self.USER_ID, ticker.upper(), side, quantity, to_cents(price_dollars), now),
        )
        await db.commit()
        return {
            "id": id_,
            "user_id": self.USER_ID,
            "ticker": ticker.upper(),
            "side": side,
            "quantity": quantity,
            "price": price_dollars,
            "executed_at": now,
        }

    async def list_all(self) -> list[dict]:
        """Return all trades for the default user, newest first."""
        db = await get_db()
        async with db.execute(
            "SELECT id, ticker, side, quantity, price, executed_at FROM trades WHERE user_id = ? ORDER BY executed_at DESC",
            (self.USER_ID,),
        ) as cursor:
            rows = [dict(row) async for row in cursor]
        for row in rows:
            row["price"] = from_cents(row["price"])
        return rows

    async def list_recent(self, limit: int = 50) -> list[dict]:
        """Return the most recent trades, newest first."""
        db = await get_db()
        async with db.execute(
            "SELECT id, ticker, side, quantity, price, executed_at FROM trades WHERE user_id = ? ORDER BY executed_at DESC LIMIT ?",
            (self.USER_ID, limit),
        ) as cursor:
            rows = [dict(row) async for row in cursor]
        for row in rows:
            row["price"] = from_cents(row["price"])
        return rows
