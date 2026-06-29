/**
 * Zustand store for the chat panel's collapsed state.
 *
 * Stored at module level so the page-level CSS grid can react — when the
 * chat is collapsed, the right column shrinks from 400px to 48px and the
 * workspace reflows to fill the freed space.
 */

"use client";

import { create } from "zustand";

export interface ChatPanelCollapsedState {
  collapsed: boolean;
}

export interface ChatPanelCollapsedActions {
  toggle: () => void;
  set: (collapsed: boolean) => void;
}

export type ChatPanelCollapsedStore = ChatPanelCollapsedState &
  ChatPanelCollapsedActions;

export const useChatPanelCollapsed = create<ChatPanelCollapsedStore>((set) => ({
  collapsed: false,
  toggle: () => set((s) => ({ collapsed: !s.collapsed })),
  set: (collapsed) => set({ collapsed }),
}));
