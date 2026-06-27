"""LLM integration package: client, schemas, prompts, executor, and context.

Public API re-exported here:

- ``LLMClient``, ``MockLLMClient``, ``create_llm_client`` — chat clients
- ``LLMError``, ``LLMValidationError`` — exceptions raised by clients
- ``RetryingLLMClient``, ``CORRECTIVE_SYSTEM_MESSAGE``,
  ``retry_structured_completion`` — retry-on-validation wrapper
- ``ChatResponse``, ``TradeAction``, ``WatchlistChange`` — structured output
- ``build_portfolio_context`` — assembles the JSON context for the prompt
- ``build_messages``, ``SYSTEM_PROMPT`` — prompt construction helpers
- ``execute_actions``, ``ExecutionResult``, ``ExecutorRepos``,
  ``TradeActionResult``, ``WatchlistActionResult`` — executor for trades
  and watchlist changes returned by the LLM
"""

from __future__ import annotations

from .client import LLMClient, LLMError, LLMValidationError, MockLLMClient, create_llm_client
from .context import build_portfolio_context
from .executor import (
    ExecutionResult,
    ExecutorRepos,
    TradeActionResult,
    WatchlistActionResult,
    execute_actions,
)
from .prompts import SYSTEM_PROMPT, build_messages
from .retry import CORRECTIVE_SYSTEM_MESSAGE, RetryingLLMClient, retry_structured_completion
from .schemas import ChatResponse, TradeAction, WatchlistChange

__all__ = [
    # Client
    "LLMClient",
    "LLMError",
    "LLMValidationError",
    "MockLLMClient",
    "create_llm_client",
    # Retry
    "RetryingLLMClient",
    "CORRECTIVE_SYSTEM_MESSAGE",
    "retry_structured_completion",
    # Schemas
    "ChatResponse",
    "TradeAction",
    "WatchlistChange",
    # Context
    "build_portfolio_context",
    # Prompts
    "build_messages",
    "SYSTEM_PROMPT",
    # Executor
    "execute_actions",
    "ExecutionResult",
    "ExecutorRepos",
    "TradeActionResult",
    "WatchlistActionResult",
]