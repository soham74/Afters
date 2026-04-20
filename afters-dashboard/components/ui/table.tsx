import * as React from "react";
import { cn } from "@/lib/utils";

// Each subcomponent uses the React attribute type that matches its underlying
// HTML element so table-specific attributes (colSpan, rowSpan, scope, headers,
// align) flow through the prop spread instead of being rejected by the type
// checker. The previous version typed everything as React.HTMLAttributes<...>
// which is the generic shape and excludes those table-only props.

export const Table = ({
  className,
  ...props
}: React.TableHTMLAttributes<HTMLTableElement>) => (
  <div className="relative w-full overflow-auto">
    <table className={cn("w-full caption-bottom text-sm", className)} {...props} />
  </div>
);

export const TableHeader = ({
  className,
  ...props
}: React.HTMLAttributes<HTMLTableSectionElement>) => (
  <thead className={cn("[&_tr]:border-b border-line", className)} {...props} />
);

export const TableBody = ({
  className,
  ...props
}: React.HTMLAttributes<HTMLTableSectionElement>) => (
  <tbody className={cn(className)} {...props} />
);

export const TableRow = ({
  className,
  ...props
}: React.HTMLAttributes<HTMLTableRowElement>) => (
  <tr
    className={cn(
      "border-b border-line transition-colors hover:bg-bg-subtle data-[state=selected]:bg-bg-subtle",
      className,
    )}
    {...props}
  />
);

export const TableHead = ({
  className,
  ...props
}: React.ThHTMLAttributes<HTMLTableCellElement>) => (
  <th
    className={cn(
      "h-9 px-3 text-left align-middle text-xs font-medium text-ink-muted uppercase tracking-wider",
      className,
    )}
    {...props}
  />
);

export const TableCell = ({
  className,
  ...props
}: React.TdHTMLAttributes<HTMLTableCellElement>) => (
  <td className={cn("px-3 py-3 align-middle", className)} {...props} />
);
