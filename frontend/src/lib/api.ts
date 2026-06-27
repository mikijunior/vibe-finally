/**
 * Thin fetch wrappers for the FinAlly REST API.
 *
 * All API calls go to the same origin (/api/*) so no CORS configuration is
 * needed. Errors carry the backend's `detail` message so the UI can show
 * server-side validation feedback directly.
 */

import type {
  ChatEndpointResponse,
  ChatRequest,
  HealthResponse,
  PortfolioHistoryResponse,
  PortfolioResponse,
  TradeRequest,
  TradeResponse,
  WatchlistMutationResponse,
  WatchlistResponse,
} from "./types";

const DEFAULT_USER_AGENT = "FinAlly-Frontend/0.1";

function apiBase(): string {
  // SSR-safe: use the current origin in the browser, fall back to "" for SSR.
  if (typeof window === "undefined") return "";
  return window.location.origin;
}

function normalizeTicker(ticker: string): string {
  return ticker.trim().toUpperCase();
}

class ApiError extends Error {
  readonly status: number;
  readonly detail: string;

  constructor(status: number, detail: string) {
    super(`${status}: ${detail}`);
    this.name = "ApiError";
    this.status = status;
    this.detail = detail;
  }
}

async function request<T>(
  path: string,
  init: RequestInit = {},
): Promise<T> {
  const url = `${apiBase()}${path}`;
  const response = await fetch(url, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      Accept: "application/json",
      "User-Agent": DEFAULT_USER_AGENT,
      ...(init.headers ?? {}),
    },
  });

  if (!response.ok) {
    let detail = response.statusText;
    try {
      const body = (await response.json()) as { detail?: string };
      if (body && typeof body.detail === "string") {
        detail = body.detail;
      }
    } catch {
      // Body wasn't JSON; fall back to statusText.
    }
    throw new ApiError(response.status, detail);
  }

  // 204 No Content — caller doesn't expect a body.
  if (response.status === 204) {
    return undefined as T;
  }

  return (await response.json()) as T;
}

// ---------------------------------------------------------------------------
// System
// ---------------------------------------------------------------------------

export function getHealth(): Promise<HealthResponse> {
  return request<HealthResponse>("/api/health");
}

// ---------------------------------------------------------------------------
// Portfolio
// ---------------------------------------------------------------------------

export function getPortfolio(): Promise<PortfolioResponse> {
  return request<PortfolioResponse>("/api/portfolio");
}

export function executeTrade(req: TradeRequest): Promise<TradeResponse> {
  const body: TradeRequest = {
    ticker: normalizeTicker(req.ticker),
    quantity: req.quantity,
    side: req.side,
  };
  return request<TradeResponse>("/api/portfolio/trade", {
    method: "POST",
    body: JSON.stringify(body),
  });
}

export function getPortfolioHistory(): Promise<PortfolioHistoryResponse> {
  return request<PortfolioHistoryResponse>("/api/portfolio/history");
}

// ---------------------------------------------------------------------------
// Watchlist
// ---------------------------------------------------------------------------

export function getWatchlist(): Promise<WatchlistResponse> {
  return request<WatchlistResponse>("/api/watchlist");
}

export function addWatchlistTicker(ticker: string): Promise<WatchlistMutationResponse> {
  return request<WatchlistMutationResponse>("/api/watchlist", {
    method: "POST",
    body: JSON.stringify({ ticker: normalizeTicker(ticker) }),
  });
}

export function removeWatchlistTicker(ticker: string): Promise<WatchlistMutationResponse> {
  return request<WatchlistMutationResponse>(
    `/api/watchlist/${encodeURIComponent(normalizeTicker(ticker))}`,
    { method: "DELETE" },
  );
}

// ---------------------------------------------------------------------------
// Chat (LLM)
// ---------------------------------------------------------------------------

export function sendChat(req: ChatRequest): Promise<ChatEndpointResponse> {
  return request<ChatEndpointResponse>("/api/chat", {
    method: "POST",
    body: JSON.stringify(req),
  });
}

export { ApiError };