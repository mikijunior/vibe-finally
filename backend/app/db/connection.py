"""Lazy SQLite connection management with WAL mode and schema bootstrap."""

from __future__ import annotations

import asyncio
import uuid
from datetime import datetime, timezone
from pathlib import Path

import aiosqlite

from . import seed


def _project_root() -> Path:
    """Return the project root directory.

    The file lives at backend/app/db/connection.py.
    parents[3] = backend/app/db/ -> backend/app/ -> backend/ -> project root.
    """
    return Path(__file__).resolve().parents[3].parent


DB_PATH = _project_root() / "db" / "finally.db"

_connection: aiosqlite.Connection | None = None
_init_lock = asyncio.Lock()


async def _enable_wal(db: aiosqlite.Connection) -> None:
    """Enable WAL mode. Called once on first connection."""
    await db.execute("PRAGMA journal_mode=WAL")
    async with db.execute("PRAGMA journal_mode") as cursor:
        row = await cursor.fetchone()
        mode = row[0].lower() if row else ""
        if mode != "wal":
            raise RuntimeError(f"Failed to enable WAL mode, got: {mode}")


async def _seed_defaults(db: aiosqlite.Connection) -> None:
    """Seed default user and watchlist tickers. Idempotent — skips if already seeded."""
    # Check if already seeded
    async with db.execute(
        "SELECT 1 FROM users_profile WHERE id = ?", (seed.DEFAULT_USER_ID,)
    ) as cursor:
        if await cursor.fetchone() is not None:
            return  # Already seeded

    now = datetime.now(timezone.utc).isoformat()

    # Insert default user
    await db.execute(
        "INSERT INTO users_profile (id, cash_balance, created_at) VALUES (?, ?, ?)",
        (seed.DEFAULT_USER_ID, seed.DEFAULT_CASH_CENTS, now),
    )

    # Insert default watchlist tickers
    for ticker in seed.DEFAULT_TICKERS:
        await db.execute(
            "INSERT INTO watchlist (id, user_id, ticker, added_at) VALUES (?, ?, ?, ?)",
            (str(uuid.uuid4()), seed.DEFAULT_USER_ID, ticker, now),
        )

    await db.commit()


async def _ensure_schema(db: aiosqlite.Connection) -> None:
    """Create all tables if they don't exist, then seed defaults."""
    async with db.execute(
        "SELECT name FROM sqlite_master WHERE type='table'"
    ) as cursor:
        existing = {row[0] async for row in cursor}

    if "users_profile" not in existing:
        schema_sql = (Path(__file__).parent / "schema.sql").read_text()
        await db.executescript(schema_sql)
        await db.commit()

    await _seed_defaults(db)


async def get_db() -> aiosqlite.Connection:
    """Get the shared DB connection, initializing schema if needed.

    Uses double-checked locking for thread-safe lazy initialization.
    """
    global _connection

    if _connection is None:
        async with _init_lock:
            if _connection is None:
                DB_PATH.parent.mkdir(parents=True, exist_ok=True)
                db = await aiosqlite.connect(str(DB_PATH))
                db.row_factory = aiosqlite.Row
                await _enable_wal(db)
                await _ensure_schema(db)
                _connection = db

    return _connection


async def init_db() -> aiosqlite.Connection:
    """Public API: initialize DB and return the shared connection."""
    return await get_db()


async def close_db() -> None:
    """Public API: close the shared connection."""
    global _connection
    if _connection is not None:
        await _connection.close()
        _connection = None
