/**
 * Frontend TypeScript types mirroring backend Pydantic schemas.
 *
 * The backend is the source of truth — when in doubt, the FastAPI auto-generated
 * OpenAPI docs (or `backend/app/api/schemas.py`) define the wire format.
 */

// ---------------------------------------------------------------------------
// System
// ---------------------------------------------------------------------------

export interface HealthResponse {
  status: string;
}

// ---------------------------------------------------------------------------
// Price updates (SSE stream payload element)
// ---------------------------------------------------------------------------

/** Direction of the latest price change. */
export type PriceDirection = "up" | "down" | "flat" | "unchanged";

export interface PriceUpdate {
  ticker: string;
  price: number;
  previous_price: number;
  timestamp: number; // epoch seconds (UTCTimestamp for lightweight-charts)
  change: number;
  change_percent: number;
  direction: PriceDirection;
}

// ---------------------------------------------------------------------------
// Watchlist
// ---------------------------------------------------------------------------

export interface WatchlistEntry {
  ticker: string;
  added_at: string;
  price: number;
}

export interface WatchlistResponse {
  entries: WatchlistEntry[];
}

export interface WatchlistMutationResponse {
  ticker: string;
  action: "added" | "removed";
  already_present: boolean;
}

// ---------------------------------------------------------------------------
// Portfolio
// ---------------------------------------------------------------------------

export interface Position {
  ticker: string;
  quantity: number;
  avg_cost: number;
  current_price: number;
  unrealized_pnl: number;
  pnl_percent: number;
}

export interface PortfolioResponse {
  cash_balance: number;
  positions: Position[];
  total_value: number;
}

export interface TradeRequest {
  ticker: string;
  quantity: number;
  side: "buy" | "sell";
}

/** Trade record returned by the backend (rows from `trades` table). */
export interface TradeRecord {
  id: string;
  user_id: string;
  ticker: string;
  side: "buy" | "sell";
  quantity: number;
  price: number;
  executed_at: string;
}

/** Position record returned by the backend (rows from `positions` table). */
export interface PositionRecord {
  id: string;
  user_id: string;
  ticker: string;
  quantity: number;
  avg_cost: number;
  updated_at: string;
}

export interface TradeResponse {
  trade: TradeRecord;
  position: PositionRecord | null;
  cash_balance: number;
}

// ---------------------------------------------------------------------------
// Portfolio history
// ---------------------------------------------------------------------------

export interface Snapshot {
  id: string;
  total_value: number;
  recorded_at: string;
}

export interface PortfolioHistoryResponse {
  snapshots: Snapshot[];
}

// ---------------------------------------------------------------------------
// Chat (LLM)
// ---------------------------------------------------------------------------

export interface ChatRequest {
  message: string;
}

/** Auto-executed action reported by /api/chat. */
export interface ChatActionResult {
  type: "trade" | "watchlist";
  ticker: string;
  status: "executed" | "failed";
  detail: string | null;
  side: "buy" | "sell" | null;
  quantity: number | null;
  action: "add" | "remove" | null;
}

export interface ChatEndpointResponse {
  message: string;
  trades: Array<{ ticker: string; side: string; quantity: number }>;
  watchlist_changes: Array<{ ticker: string; action: string }>;
  actions_executed: ChatActionResult[];
}

// ---------------------------------------------------------------------------
// Connection status (SSE)
// ---------------------------------------------------------------------------

export type ConnectionStatus = "connected" | "reconnecting" | "disconnected";