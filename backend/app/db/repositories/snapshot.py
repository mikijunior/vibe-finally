"""Repository for portfolio_snapshots table."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from ..cents import from_cents, to_cents
from ..connection import get_db


class SnapshotRepository:
    """Repository for portfolio_snapshots operations.

    All total_value amounts cross the API boundary as dollars (float),
    but are stored in the DB as integer cents.
    """

    USER_ID = "default"

    async def insert(self, total_value_dollars: float) -> dict:
        """Record a new portfolio snapshot. Returns the inserted row with total_value in dollars."""
        db = await get_db()
        now = datetime.now(timezone.utc).isoformat()
        id_ = str(uuid.uuid4())
        await db.execute(
            "INSERT INTO portfolio_snapshots (id, user_id, total_value, recorded_at) VALUES (?, ?, ?, ?)",
            (id_, self.USER_ID, to_cents(total_value_dollars), now),
        )
        await db.commit()
        return {
            "id": id_,
            "user_id": self.USER_ID,
            "total_value": total_value_dollars,
            "recorded_at": now,
        }

    async def list_all(self) -> list[dict]:
        """Return all snapshots for the default user, oldest first."""
        db = await get_db()
        async with db.execute(
            "SELECT id, total_value, recorded_at FROM portfolio_snapshots WHERE user_id = ? ORDER BY recorded_at ASC",
            (self.USER_ID,),
        ) as cursor:
            rows = [dict(row) async for row in cursor]
        for row in rows:
            row["total_value"] = from_cents(row["total_value"])
        return rows
