/**
 * shadcn/ui-style Button primitive — a styled <button> with color variants.
 *
 * Variants follow the FinAlly color contract:
 *   default    = blue-primary (primary action)
 *   secondary  = bg-elevated with border
 *   destructive= pnl-down (sell, danger)
 *   ghost      = transparent until hover
 *   submit     = purple-secondary (chat "Send")
 *
 * This is a local copy — no shadcn CLI or radix-ui dependency.
 */

"use client";

import { clsx } from "clsx";
import { forwardRef } from "react";

export type ButtonVariant =
  | "default"
  | "secondary"
  | "destructive"
  | "ghost"
  | "submit";

export interface ButtonProps
  extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: ButtonVariant;
}

const VARIANT_CLASSES: Record<ButtonVariant, string> = {
  default:
    "bg-blue-primary text-bg-base hover:opacity-90 disabled:opacity-40",
  secondary:
    "bg-bg-elevated text-text-primary border border-border-muted hover:border-blue-primary/60 disabled:opacity-40",
  destructive: "bg-pnl-down text-white hover:opacity-90 disabled:opacity-40",
  ghost:
    "bg-transparent text-text-primary hover:bg-bg-elevated disabled:opacity-40",
  submit:
    "bg-purple-secondary text-white hover:opacity-90 disabled:opacity-40",
};

const BASE_CLASSES =
  "inline-flex items-center justify-center gap-1 rounded px-3 py-1 font-mono text-sm font-semibold uppercase tracking-wide transition-opacity disabled:cursor-not-allowed";

export const Button = forwardRef<HTMLButtonElement, ButtonProps>(
  function Button({ className, variant = "default", type, ...rest }, ref) {
    return (
      <button
        ref={ref}
        type={type ?? "button"}
        className={clsx(BASE_CLASSES, VARIANT_CLASSES[variant], className)}
        {...rest}
      />
    );
  },
);
