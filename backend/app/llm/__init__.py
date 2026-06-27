"""LLM integration package: client, schemas, prompts, and portfolio context.

Public API re-exported here:

- ``LLMClient``, ``MockLLMClient``, ``create_llm_client`` — chat clients
- ``LLMError`` — exception raised on bad responses
- ``ChatResponse``, ``TradeAction``, ``WatchlistChange`` — structured output
- ``build_portfolio_context`` — assembles the JSON context for the prompt
- ``build_messages``, ``SYSTEM_PROMPT`` — prompt construction helpers

The optional ``app.llm.executor`` module (auto-execution of trades and
watchlist changes) is provided by Plan 03-02 and intentionally NOT imported
here so this package remains usable without it.
"""

from __future__ import annotations

from .client import LLMClient, LLMError, MockLLMClient, create_llm_client
from .context import build_portfolio_context
from .prompts import SYSTEM_PROMPT, build_messages
from .schemas import ChatResponse, TradeAction, WatchlistChange

__all__ = [
    "LLMClient",
    "LLMError",
    "MockLLMClient",
    "create_llm_client",
    "ChatResponse",
    "TradeAction",
    "WatchlistChange",
    "build_portfolio_context",
    "build_messages",
    "SYSTEM_PROMPT",
]