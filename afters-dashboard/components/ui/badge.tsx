import * as React from "react";
import { cva, type VariantProps } from "class-variance-authority";
import { cn } from "@/lib/utils";

const badgeVariants = cva(
  "inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium transition-colors",
  {
    variants: {
      variant: {
        default: "bg-bg-subtle text-ink border border-line",
        accent: "bg-accent-soft text-accent-deep border border-accent/30",
        success: "bg-success/10 text-success border border-success/30",
        warning: "bg-warning/10 text-warning border border-warning/30",
        danger: "bg-danger/10 text-danger border border-danger/30",
        info: "bg-info/10 text-info border border-info/30",
        outline: "bg-white text-ink border border-line",
        solid: "bg-ink text-white",
      },
    },
    defaultVariants: { variant: "default" },
  },
);

export interface BadgeProps
  extends React.HTMLAttributes<HTMLSpanElement>,
    VariantProps<typeof badgeVariants> {}

export function Badge({ className, variant, ...props }: BadgeProps) {
  return (
    <span className={cn(badgeVariants({ variant }), className)} {...props} />
  );
}
