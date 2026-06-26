"""Repository for chat_messages table."""
from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone

from ..connection import get_db


class ChatRepository:
    """Repository for chat_messages operations."""

    USER_ID = "default"

    async def insert(self, role: str, content: str, actions: dict | None = None) -> dict:
        """Insert a new chat message. Returns the inserted row."""
        db = await get_db()
        now = datetime.now(timezone.utc).isoformat()
        id_ = str(uuid.uuid4())
        actions_json = json.dumps(actions) if actions is not None else None
        await db.execute(
            "INSERT INTO chat_messages (id, user_id, role, content, actions, created_at) VALUES (?, ?, ?, ?, ?, ?)",
            (id_, self.USER_ID, role, content, actions_json, now),
        )
        await db.commit()
        return {
            "id": id_,
            "user_id": self.USER_ID,
            "role": role,
            "content": content,
            "actions": actions,
            "created_at": now,
        }

    async def list_all(self) -> list[dict]:
        """Return all chat messages for the default user, oldest first."""
        db = await get_db()
        async with db.execute(
            "SELECT id, role, content, actions, created_at FROM chat_messages WHERE user_id = ? ORDER BY created_at ASC",
            (self.USER_ID,),
        ) as cursor:
            rows = [dict(row) async for row in cursor]
        for row in rows:
            if row["actions"] is not None:
                row["actions"] = json.loads(row["actions"])
        return rows

    async def list_recent(self, limit: int = 50) -> list[dict]:
        """Return the most recent chat messages, newest first."""
        db = await get_db()
        async with db.execute(
            "SELECT id, role, content, actions, created_at FROM chat_messages WHERE user_id = ? ORDER BY created_at DESC LIMIT ?",
            (self.USER_ID, limit),
        ) as cursor:
            rows = [dict(row) async for row in cursor]
        for row in rows:
            if row["actions"] is not None:
                row["actions"] = json.loads(row["actions"])
        return rows
