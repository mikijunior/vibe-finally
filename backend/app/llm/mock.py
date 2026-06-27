"""Deterministic MockLLMClient for tests and ``LLM_MOCK=true``.

Routes on keywords in the last user message. No network calls. The same
constructor signature as ``LLMClient`` so the factory in ``client.py`` can
return either polymorphically.
"""

from __future__ import annotations

import json
import re
from typing import Any, TypeVar

from pydantic import BaseModel

from .schemas import ChatResponse

T = TypeVar("T", bound=BaseModel)


# Patterns evaluated in priority order against the last user message.
# Each pattern group 1 is the numeric quantity (when applicable) and
# group 2 is the ticker symbol (uppercased by the regex flag).
_BUY_PATTERN = re.compile(
    r"(?i)\bbuy\s+([\d.]+)\s*(?:shares?\s+of\s+)?([A-Z]{1,5})\b"
)
_SELL_PATTERN = re.compile(
    r"(?i)\bsell\s+([\d.]+)\s*(?:shares?\s+of\s+)?([A-Z]{1,5})\b"
)
_ADD_PATTERN = re.compile(r"(?i)\b(?:add|watch)\s+([A-Z]{1,5})\b")
_REMOVE_PATTERN = re.compile(r"(?i)\b(?:remove|drop)\s+([A-Z]{1,5})\b")


class MockLLMClient:
    """Deterministic mock LLM with keyword routing.

    Returns a JSON-serialized ``ChatResponse`` for every call. The response
    is determined by regex matching against the most recent user message:

    - ``buy <qty> [shares of] <TICKER>``  -> trade buy
    - ``sell <qty> [shares of] <TICKER>`` -> trade sell
    - ``(add|watch) <TICKER>``            -> watchlist add
    - ``(remove|drop) <TICKER>``          -> watchlist remove
    - anything else                        -> default summary, no actions

    The class accepts the same constructor signature as ``LLMClient`` so the
    factory in ``client.py`` can return either polymorphically.
    """

    DEFAULT_MODEL = "mock"
    DEFAULT_EXTRA_BODY: dict[str, Any] = {}

    def __init__(
        self,
        model: str | None = None,
        extra_body: dict[str, Any] | None = None,
    ) -> None:
        self.model = model or self.DEFAULT_MODEL
        self.extra_body = extra_body if extra_body is not None else dict(self.DEFAULT_EXTRA_BODY)
        self.api_key = None

    async def complete(
        self,
        messages: list[dict[str, Any]],
        *,
        reasoning_effort: str = "low",
    ) -> str:
        """Return a JSON string built by routing on the last user message."""
        last_user = next(
            (m for m in reversed(messages) if m.get("role") == "user"), None
        )
        if last_user is None:
            return json.dumps(
                {
                    "message": "Mock: no user message found",
                    "trades": [],
                    "watchlist_changes": [],
                }
            )

        text = (last_user.get("content") or "").strip()

        buy_match = _BUY_PATTERN.search(text)
        if buy_match:
            qty = float(buy_match.group(1))
            ticker = buy_match.group(2).upper()
            return json.dumps(
                {
                    "message": f"Mock buy {qty:g} {ticker}",
                    "trades": [{"ticker": ticker, "side": "buy", "quantity": qty}],
                    "watchlist_changes": [],
                }
            )

        sell_match = _SELL_PATTERN.search(text)
        if sell_match:
            qty = float(sell_match.group(1))
            ticker = sell_match.group(2).upper()
            return json.dumps(
                {
                    "message": f"Mock sell {qty:g} {ticker}",
                    "trades": [{"ticker": ticker, "side": "sell", "quantity": qty}],
                    "watchlist_changes": [],
                }
            )

        add_match = _ADD_PATTERN.search(text)
        if add_match:
            ticker = add_match.group(1).upper()
            return json.dumps(
                {
                    "message": f"Mock add {ticker}",
                    "trades": [],
                    "watchlist_changes": [{"ticker": ticker, "action": "add"}],
                }
            )

        remove_match = _REMOVE_PATTERN.search(text)
        if remove_match:
            ticker = remove_match.group(1).upper()
            return json.dumps(
                {
                    "message": f"Mock remove {ticker}",
                    "trades": [],
                    "watchlist_changes": [{"ticker": ticker, "action": "remove"}],
                }
            )

        return json.dumps(
            {
                "message": f"Mock portfolio summary for: {text}",
                "trades": [],
                "watchlist_changes": [],
            }
        )

    async def complete_structured(
        self,
        messages: list[dict[str, Any]],
        response_model: type[T],
        *,
        reasoning_effort: str = "low",
    ) -> T:
        """Parse the JSON returned by ``complete`` into the given Pydantic model."""
        content = await self.complete(messages, reasoning_effort=reasoning_effort)
        return response_model.model_validate_json(content)


__all__ = ["MockLLMClient"]