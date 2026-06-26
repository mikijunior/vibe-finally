"""Repository for users_profile table."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from ..cents import from_cents, to_cents
from ..connection import get_db


class UserRepository:
    """Repository for users_profile operations.

    All cash values cross the API boundary as dollars (float),
    but are stored in the DB as integer cents.
    """

    USER_ID = "default"

    async def get(self) -> dict | None:
        """Fetch the default user profile, or None if not found."""
        db = await get_db()
        async with db.execute(
            "SELECT id, cash_balance, created_at FROM users_profile WHERE id = ?",
            (self.USER_ID,),
        ) as cursor:
            row = await cursor.fetchone()
        if row is None:
            return None
        return {
            "id": row["id"],
            "cash_balance": from_cents(row["cash_balance"]),
            "created_at": row["created_at"],
        }

    async def update_cash(self, new_cash_dollars: float) -> None:
        """Update the user's cash balance to a new dollar amount."""
        db = await get_db()
        await db.execute(
            "UPDATE users_profile SET cash_balance = ? WHERE id = ?",
            (to_cents(new_cash_dollars), self.USER_ID),
        )
        await db.commit()

    async def adjust_cash(self, delta_cents: int) -> int:
        """Adjust cash by delta cents (positive or negative). Returns new raw cents."""
        db = await get_db()
        await db.execute(
            "UPDATE users_profile SET cash_balance = cash_balance + ? WHERE id = ?",
            (delta_cents, self.USER_ID),
        )
        await db.commit()
        async with db.execute(
            "SELECT cash_balance FROM users_profile WHERE id = ?",
            (self.USER_ID,),
        ) as cursor:
            row = await cursor.fetchone()
        return row["cash_balance"] if row else 0
