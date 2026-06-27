/**
 * EventSource hook for the live price SSE stream at /api/stream/prices.
 *
 * Mounts a module-level singleton EventSource so reconnects across hot reloads
 * don't leak listeners. Exposes a `connectionStatus` derived from
 * `EventSource.readyState` so the header can show a green/yellow/red dot.
 */

"use client";

import { useEffect, useState } from "react";

import { usePriceStore } from "./store";
import type { ConnectionStatus, PriceUpdate } from "./types";

const STREAM_PATH = "/api/stream/prices";

let singletonSource: EventSource | null = null;
let subscriberCount = 0;
let lastStatus: ConnectionStatus = "disconnected";

function statusFromReadyState(readyState: number): ConnectionStatus {
  // EventSource constants: CONNECTING=0, OPEN=1, CLOSED=2
  if (readyState === 1) return "connected";
  if (readyState === 0) return "reconnecting";
  return "disconnected";
}

function notifyStatus(status: ConnectionStatus): void {
  if (status === lastStatus) return;
  lastStatus = status;
  // Dispatch a custom event so all subscribers re-read on the next render.
  if (typeof window !== "undefined") {
    window.dispatchEvent(new CustomEvent("finally:price-status", { detail: status }));
  }
}

function startStream(): void {
  if (typeof window === "undefined") return;
  if (singletonSource) return;

  const source = new EventSource(STREAM_PATH);
  singletonSource = source;

  source.onopen = () => notifyStatus(statusFromReadyState(source.readyState));
  source.onerror = () => notifyStatus(statusFromReadyState(source.readyState));
  source.onmessage = (event) => {
    try {
      const data = JSON.parse(event.data) as Record<string, PriceUpdate>;
      usePriceStore.getState().bulkUpdate(data);
    } catch (err) {
      // Malformed event — log and skip; the next tick will recover.
      // eslint-disable-next-line no-console
      console.warn("Failed to parse SSE price event", err);
    }
  };

  notifyStatus(statusFromReadyState(source.readyState));
}

function stopStream(): void {
  if (!singletonSource) return;
  singletonSource.close();
  singletonSource = null;
  notifyStatus("disconnected");
}

function readStatus(): ConnectionStatus {
  if (typeof window === "undefined") return "disconnected";
  if (!singletonSource) return "disconnected";
  return statusFromReadyState(singletonSource.readyState);
}

export interface UsePriceStreamResult {
  connectionStatus: ConnectionStatus;
}

/**
 * React hook that opens the SSE connection on first mount and returns the
 * current connection status. Price data is read directly from `usePriceStore`
 * by individual components — this hook only manages the connection.
 */
export function usePriceStream(): UsePriceStreamResult {
  const [connectionStatus, setConnectionStatus] = useState<ConnectionStatus>(
    () => readStatus(),
  );

  useEffect(() => {
    if (typeof window === "undefined") return undefined;

    subscriberCount += 1;
    startStream();
    setConnectionStatus(readStatus());

    const onStatus = (event: Event) => {
      const detail = (event as CustomEvent<ConnectionStatus>).detail;
      setConnectionStatus(detail);
    };
    window.addEventListener("finally:price-status", onStatus);

    // The browser's EventSource auto-reconnects when the server emits
    // `retry: 1000` (which our backend does). We rely on that built-in
    // behavior rather than manual reconnect logic.

    const handleBeforeUnload = () => stopStream();

    // We intentionally do NOT close the singleton on unmount because the
    // provider mounts once at the app root and never unmounts in normal
    // usage. The beforeunload handler covers the page-leave case.
    window.addEventListener("beforeunload", handleBeforeUnload);

    return () => {
      window.removeEventListener("finally:price-status", onStatus);
      window.removeEventListener("beforeunload", handleBeforeUnload);
      subscriberCount = Math.max(0, subscriberCount - 1);
      // Only close when explicitly told (e.g. tests). The page unload handler
      // closes the source as well, so ordinary navigation tears it down.
    };
  }, []);

  return { connectionStatus };
}