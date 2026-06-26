"""Repository for positions table."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from ..cents import from_cents, to_cents
from ..connection import get_db


class PositionRepository:
    """Repository for positions operations.

    Quantity is stored as integer shares (not cents). avg_cost is stored
    as integer cents per share.
    """

    USER_ID = "default"

    async def get_all(self) -> list[dict]:
        """Return all positions for the default user."""
        db = await get_db()
        async with db.execute(
            "SELECT id, ticker, quantity, avg_cost, updated_at FROM positions WHERE user_id = ?",
            (self.USER_ID,),
        ) as cursor:
            rows = [dict(row) async for row in cursor]
        for row in rows:
            row["avg_cost"] = from_cents(row["avg_cost"])
        return rows

    async def get_one(self, ticker: str) -> dict | None:
        """Return a single position for a ticker, or None if not found."""
        db = await get_db()
        async with db.execute(
            "SELECT id, ticker, quantity, avg_cost, updated_at FROM positions WHERE user_id = ? AND ticker = ?",
            (self.USER_ID, ticker.upper()),
        ) as cursor:
            row = await cursor.fetchone()
        if row is None:
            return None
        result = dict(row)
        result["avg_cost"] = from_cents(result["avg_cost"])
        return result

    async def upsert(self, ticker: str, quantity: float, avg_cost_dollars: float) -> dict:
        """Insert or replace a position. Commits immediately."""
        db = await get_db()
        now = datetime.now(timezone.utc).isoformat()
        id_ = str(uuid.uuid4())
        await db.execute(
            "INSERT OR REPLACE INTO positions (id, user_id, ticker, quantity, avg_cost, updated_at) VALUES (?, ?, ?, ?, ?, ?)",
            (id_, self.USER_ID, ticker.upper(), quantity, to_cents(avg_cost_dollars), now),
        )
        await db.commit()
        return {
            "id": id_,
            "user_id": self.USER_ID,
            "ticker": ticker.upper(),
            "quantity": quantity,
            "avg_cost": avg_cost_dollars,
            "updated_at": now,
        }

    async def delete(self, ticker: str) -> bool:
        """Delete a position. Returns True if a row was deleted."""
        db = await get_db()
        cursor = await db.execute(
            "DELETE FROM positions WHERE user_id = ? AND ticker = ?",
            (self.USER_ID, ticker.upper()),
        )
        await db.commit()
        return cursor.rowcount > 0
