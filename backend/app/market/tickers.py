"""Ticker normalization helpers for market data providers."""

from __future__ import annotations


def normalize_ticker(ticker: str) -> str:
    """Return the canonical ticker key used throughout market data."""
    return ticker.upper().strip()


def normalize_tickers(tickers: list[str]) -> list[str]:
    """Normalize, drop blanks, and preserve first-seen order."""
    normalized: list[str] = []
    seen: set[str] = set()

    for ticker in tickers:
        value = normalize_ticker(ticker)
        if not value or value in seen:
            continue
        normalized.append(value)
        seen.add(value)

    return normalized
