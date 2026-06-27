"""Pydantic v2 schemas for structured LLM output.

These models match the contract described in PLAN.md section 9: the LLM
must always respond with JSON containing a ``message`` field plus optional
``trades`` and ``watchlist_changes`` lists. All models forbid extra fields
so the SDK cannot silently smuggle in unexpected keys.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

# Strict base: reject any field not explicitly declared. Important for
# ``response_format`` validation — the LLM must conform exactly.
_BASE_CONFIG = ConfigDict(extra="forbid")


class TradeAction(BaseModel):
    """A single trade the LLM wants executed against the user's portfolio."""

    model_config = _BASE_CONFIG

    ticker: str = Field(min_length=1, max_length=10)
    side: Literal["buy", "sell"]
    quantity: float = Field(gt=0)

    @field_validator("ticker")
    @classmethod
    def _normalize_ticker(cls, value: str) -> str:
        """Uppercase ticker; reject whitespace-only values."""
        cleaned = value.strip().upper()
        if not cleaned:
            raise ValueError("ticker must not be empty after normalization")
        return cleaned


class WatchlistChange(BaseModel):
    """A single watchlist mutation the LLM wants executed."""

    model_config = _BASE_CONFIG

    ticker: str = Field(min_length=1, max_length=10)
    action: Literal["add", "remove"]

    @field_validator("ticker")
    @classmethod
    def _normalize_ticker(cls, value: str) -> str:
        """Uppercase ticker; reject whitespace-only values."""
        cleaned = value.strip().upper()
        if not cleaned:
            raise ValueError("ticker must not be empty after normalization")
        return cleaned


class ChatResponse(BaseModel):
    """Top-level structured output the LLM is required to produce.

    Matches PLAN.md section 9: ``message`` is required, ``trades`` and
    ``watchlist_changes`` default to empty lists if the model chooses not to
    propose any actions.
    """

    model_config = _BASE_CONFIG

    message: str = ""
    trades: list[TradeAction] = Field(default_factory=list)
    watchlist_changes: list[WatchlistChange] = Field(default_factory=list)