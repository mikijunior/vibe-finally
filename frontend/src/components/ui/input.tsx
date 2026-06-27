/**
 * shadcn/ui-style Input primitive — a styled <input> for text fields.
 *
 * Local copy (no radix-ui dependency). Use via the React.forwardRef pattern so
 * forms can focus or reset the underlying element programmatically.
 */

"use client";

import { clsx } from "clsx";
import { forwardRef } from "react";

export type InputProps = React.InputHTMLAttributes<HTMLInputElement>;

const BASE_CLASSES =
  "bg-bg-base text-text-primary border-border-muted focus:border-blue-primary w-full rounded border px-2 py-1 font-mono text-sm uppercase tracking-wide outline-none transition-colors placeholder:text-text-muted placeholder:normal-case placeholder:opacity-60";

export const Input = forwardRef<HTMLInputElement, InputProps>(function Input(
  { className, type, ...rest },
  ref,
) {
  return (
    <input
      ref={ref}
      type={type ?? "text"}
      className={clsx(BASE_CLASSES, className)}
      {...rest}
    />
  );
});
