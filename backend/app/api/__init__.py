"""Public REST API surface for FinAlly.

This package exposes three FastAPI routers:

- ``portfolio_router`` — portfolio snapshot, market-order execution, and history
- ``watchlist_router`` — watchlist CRUD with cache/source sync
- ``system_router`` — public ``/api/health`` alias

Each router is mounted in ``app.main`` under its declared prefix. Repositories
live in ``app.db.repositories`` and are wired in via ``deps.py`` so handlers
stay small and testable.

The router imports are lazy to allow partial package construction during
development (e.g. importing ``schemas`` without all router modules present).
"""

from __future__ import annotations

from importlib import import_module
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from fastapi import APIRouter

__all__ = ["portfolio_router", "watchlist_router", "system_router"]


def __getattr__(name: str):
    """Lazy import router modules so partial packages import cleanly."""
    if name == "portfolio_router":
        return import_module("app.api.portfolio").router
    if name == "watchlist_router":
        return import_module("app.api.watchlist").router
    if name == "system_router":
        return import_module("app.api.system").router
    raise AttributeError(f"module 'app.api' has no attribute {name!r}")