"""System prompt and message-construction helpers for the FinAlly chat LLM.

Keeps the persona, instructions, and message-assembly logic in one place so
the chat endpoint stays focused on request/response flow.
"""

from __future__ import annotations

import json
from typing import Any


SYSTEM_PROMPT: str = """\
You are FinAlly, an AI trading assistant embedded in a simulated trading \
workstation. You help a single user analyze their portfolio, manage their \
watchlist, and execute trades using natural language.

Always respond with valid structured JSON matching the schema:
{
  "message": "<your conversational reply to the user>",
  "trades": [{"ticker": "<SYMBOL>", "side": "buy" | "sell", "quantity": <positive number>}],
  "watchlist_changes": [{"ticker": "<SYMBOL>", "action": "add" | "remove"}]
}

Rules:
- "message" must always be present and concise (one or two short paragraphs).
- Only include "trades" when the user asks you to trade or clearly agrees to a \
suggested trade. Each trade goes through the same validation as a manual trade \
(insufficient cash or shares is rejected and surfaced back to you).
- Only include "watchlist_changes" when the user asks you to add or remove a \
ticker from their watchlist.
- Use uppercase ticker symbols. Use fractional quantities for dollar-cost style \
instructions.
- When you have nothing to propose, return empty arrays for trades and \
watchlist_changes.

Example response:
{
  "message": "I bought 5 shares of AAPL at the current price and added MSFT to \
your watchlist.",
  "trades": [{"ticker": "AAPL", "side": "buy", "quantity": 5}],
  "watchlist_changes": [{"ticker": "MSFT", "action": "add"}]
}
"""


def build_messages(
    user_message: str,
    history: list[dict[str, Any]],
    portfolio_context: dict[str, Any],
) -> list[dict[str, Any]]:
    """Assemble the messages list sent to the LLM.

    Layout (in order):
        1. System: SYSTEM_PROMPT
        2. System: serialized portfolio context (so the model has live state)
        3. Recent chat history (oldest first), skipping rows with empty content
        4. User: the new user message

    Args:
        user_message: The latest user message text.
        history: List of prior chat rows with ``role`` and ``content`` keys
            (oldest first). Empty rows are dropped.
        portfolio_context: Dict produced by ``build_portfolio_context``;
            serialized via ``json.dumps``.

    Returns:
        A list of dicts suitable for ``litellm.completion(messages=...)``.
    """
    messages: list[dict[str, Any]] = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {
            "role": "system",
            "content": (
                "Current portfolio context (JSON):\n"
                + json.dumps(portfolio_context, indent=2)
            ),
        },
    ]

    for row in history:
        content = (row.get("content") or "").strip()
        if not content:
            continue
        role = row.get("role", "user")
        messages.append({"role": role, "content": content})

    messages.append({"role": "user", "content": user_message})
    return messages