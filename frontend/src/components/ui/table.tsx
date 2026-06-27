/**
 * shadcn/ui-style Table primitives — table/thead/tbody/tr/th/td.
 *
 * Local copy (no radix-ui dependency). Headers get an elevated background;
 * rows get a muted bottom border for the trading-terminal aesthetic.
 */

"use client";

import { clsx } from "clsx";
import { forwardRef } from "react";

export const Table = forwardRef<
  HTMLTableElement,
  React.TableHTMLAttributes<HTMLTableElement>
>(function Table({ className, ...rest }, ref) {
  return (
    <table
      ref={ref}
      className={clsx("w-full border-collapse text-left", className)}
      {...rest}
    />
  );
});

export const TableHeader = forwardRef<
  HTMLTableSectionElement,
  React.HTMLAttributes<HTMLTableSectionElement>
>(function TableHeader({ className, ...rest }, ref) {
  return (
    <thead
      ref={ref}
      className={clsx("bg-bg-elevated text-text-muted", className)}
      {...rest}
    />
  );
});

export const TableBody = forwardRef<
  HTMLTableSectionElement,
  React.HTMLAttributes<HTMLTableSectionElement>
>(function TableBody({ className, ...rest }, ref) {
  return (
    <tbody ref={ref} className={clsx("", className)} {...rest} />
  );
});

export const TableRow = forwardRef<
  HTMLTableRowElement,
  React.HTMLAttributes<HTMLTableRowElement>
>(function TableRow({ className, ...rest }, ref) {
  return (
    <tr
      ref={ref}
      className={clsx("border-border-muted border-b", className)}
      {...rest}
    />
  );
});

export const TableHead = forwardRef<
  HTMLTableCellElement,
  React.ThHTMLAttributes<HTMLTableCellElement>
>(function TableHead({ className, ...rest }, ref) {
  return (
    <th
      ref={ref}
      className={clsx(
        "px-2 py-1 font-mono text-xs font-semibold uppercase tracking-wide",
        className,
      )}
      {...rest}
    />
  );
});

export const TableCell = forwardRef<
  HTMLTableCellElement,
  React.TdHTMLAttributes<HTMLTableCellElement>
>(function TableCell({ className, ...rest }, ref) {
  return (
    <td
      ref={ref}
      className={clsx("px-2 py-1 font-mono text-sm", className)}
      {...rest}
    />
  );
});
