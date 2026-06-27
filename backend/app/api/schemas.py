"""Pydantic v2 request/response models for the public REST API.

All monetary values cross the wire as dollars (float). INTEGER cents are
confined to the database layer and the ``adjust_cash`` delta path.

Each model sets ``model_config = ConfigDict(extra="forbid")`` so malformed
client payloads are rejected with HTTP 422 by FastAPI's built-in validator
instead of being silently truncated.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator


# ---------------------------------------------------------------------------
# System
# ---------------------------------------------------------------------------


class HealthResponse(BaseModel):
    """Response body for the ``/api/health`` endpoint."""

    model_config = ConfigDict(extra="forbid")

    status: str


# ---------------------------------------------------------------------------
# Portfolio
# ---------------------------------------------------------------------------


class TradeRequest(BaseModel):
    """Request body for ``POST /api/portfolio/trade``."""

    model_config = ConfigDict(extra="forbid")

    ticker: str = Field(min_length=1, max_length=10)
    quantity: float = Field(gt=0)
    side: str

    @field_validator("ticker")
    @classmethod
    def _normalize_ticker(cls, value: str) -> str:
        """Normalize ticker to uppercase; reject whitespace-only / non-letter values."""
        cleaned = value.strip().upper()
        if not cleaned:
            raise ValueError("ticker must not be empty after normalization")
        if not cleaned.isalpha():
            raise ValueError("ticker must contain only letters")
        return cleaned

    @field_validator("side")
    @classmethod
    def _normalize_side(cls, value: str) -> str:
        """Normalize side to lowercase and validate membership."""
        normalized = value.strip().lower()
        if normalized not in {"buy", "sell"}:
            raise ValueError("side must be 'buy' or 'sell'")
        return normalized


class PositionResponse(BaseModel):
    """Response body element for a single position."""

    model_config = ConfigDict(extra="forbid")

    ticker: str
    quantity: float
    avg_cost: float
    current_price: float
    unrealized_pnl: float
    pnl_percent: float


class PortfolioResponse(BaseModel):
    """Response body for ``GET /api/portfolio``."""

    model_config = ConfigDict(extra="forbid")

    cash_balance: float
    positions: list[PositionResponse]
    total_value: float


class TradeResponse(BaseModel):
    """Response body for ``POST /api/portfolio/trade``."""

    model_config = ConfigDict(extra="forbid")

    trade: dict[str, Any]
    position: dict[str, Any] | None
    cash_balance: float


class SnapshotResponse(BaseModel):
    """Response body element for a single portfolio snapshot."""

    model_config = ConfigDict(extra="forbid")

    id: str
    total_value: float
    recorded_at: str


class PortfolioHistoryResponse(BaseModel):
    """Response body for ``GET /api/portfolio/history``."""

    model_config = ConfigDict(extra="forbid")

    snapshots: list[SnapshotResponse]


# ---------------------------------------------------------------------------
# Watchlist
# ---------------------------------------------------------------------------


class WatchlistAddRequest(BaseModel):
    """Request body for ``POST /api/watchlist``."""

    model_config = ConfigDict(extra="forbid")

    ticker: str = Field(min_length=1, max_length=10)

    @field_validator("ticker")
    @classmethod
    def _normalize_ticker(cls, value: str) -> str:
        """Normalize ticker to uppercase; reject whitespace-only / non-letter values."""
        cleaned = value.strip().upper()
        if not cleaned:
            raise ValueError("ticker must not be empty after normalization")
        if not cleaned.isalpha():
            raise ValueError("ticker must contain only letters")
        return cleaned


class WatchlistEntry(BaseModel):
    """Response body element for a single watchlist row."""

    model_config = ConfigDict(extra="forbid")

    ticker: str
    added_at: str
    price: float


class WatchlistResponse(BaseModel):
    """Response body for ``GET /api/watchlist``."""

    model_config = ConfigDict(extra="forbid")

    entries: list[WatchlistEntry]


class WatchlistMutationResponse(BaseModel):
    """Response body for ``POST`` and ``DELETE`` on ``/api/watchlist``."""

    model_config = ConfigDict(extra="forbid")

    ticker: str
    action: str  # "added" | "removed"
    already_present: bool