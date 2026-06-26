"""Database package — lazy SQLite connection and schema bootstrap."""

from .connection import close_db, get_db, init_db

__all__ = ["init_db", "get_db", "close_db"]
