const MISSING = "·";

export function formatRelative(iso: string | Date | null | undefined): string {
  if (!iso) return MISSING;
  const d = typeof iso === "string" ? new Date(iso) : iso;
  const diff = Date.now() - d.getTime();
  const mins = Math.round(diff / 60000);
  if (mins < 1) return "just now";
  if (mins < 60) return `${mins}m ago`;
  const hrs = Math.round(mins / 60);
  if (hrs < 24) return `${hrs}h ago`;
  const days = Math.round(hrs / 24);
  return `${days}d ago`;
}

export function formatDuration(seconds: number | null | undefined): string {
  if (seconds == null) return MISSING;
  if (seconds < 60) return `${seconds.toFixed(1)}s`;
  const mins = seconds / 60;
  if (mins < 60) return `${mins.toFixed(1)}m`;
  const hrs = mins / 60;
  if (hrs < 24) return `${hrs.toFixed(1)}h`;
  return `${(hrs / 24).toFixed(1)}d`;
}

export function formatPct(n: number | null | undefined): string {
  if (n == null) return MISSING;
  return `${(n * 100).toFixed(1)}%`;
}

export function formatCost(n: number | null | undefined): string {
  if (n == null || n === 0) return "$0.000";
  return `$${n.toFixed(4)}`;
}

export function formatTime(iso: string | Date | null | undefined): string {
  if (!iso) return MISSING;
  const d = typeof iso === "string" ? new Date(iso) : iso;
  return d.toLocaleTimeString([], { hour: "numeric", minute: "2-digit" });
}

export function formatDate(iso: string | Date | null | undefined): string {
  if (!iso) return MISSING;
  const d = typeof iso === "string" ? new Date(iso) : iso;
  return d.toLocaleDateString(undefined, {
    month: "short",
    day: "numeric",
    year: "2-digit",
  });
}

export function initials(name: string): string {
  return name
    .split(/\s+/)
    .map((s) => s.charAt(0))
    .join("")
    .slice(0, 2)
    .toUpperCase();
}
