"""Monetary conversion helpers.

All DB columns store integer cents. API boundaries use float dollars.
"""

from __future__ import annotations


def to_cents(dollars: float) -> int:
    """Convert a dollar float to integer cents. Rounds half-to-even (banker's rounding)."""
    return round(dollars * 100)


def from_cents(cents: int) -> float:
    """Convert integer cents back to a dollar float."""
    return cents / 100.0


def format_dollars(cents: int) -> str:
    """Format cents as a human-readable dollar string, e.g. 123456 -> '$1,234.56'."""
    return f"${from_cents(cents):,.2f}"
