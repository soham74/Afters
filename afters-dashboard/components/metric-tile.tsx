import { Card } from "./ui/card";
import { cn } from "@/lib/utils";

export function MetricTile({
  label,
  value,
  sublabel,
  accent,
  icon,
}: {
  label: string;
  value: string;
  sublabel?: string;
  accent?: boolean;
  icon?: React.ReactNode;
}) {
  return (
    <Card className={cn("p-5", accent && "border-accent/50 bg-accent-soft/30")}>
      <div className="flex items-center justify-between text-ink-muted">
        <div className="text-[11px] uppercase tracking-wider font-medium">
          {label}
        </div>
        {icon}
      </div>
      <div className={cn("mt-2 text-3xl font-semibold tabular-nums", accent && "text-accent-deep")}>
        {value}
      </div>
      {sublabel && (
        <div className="mt-1 text-xs text-ink-muted leading-snug">
          {sublabel}
        </div>
      )}
    </Card>
  );
}
