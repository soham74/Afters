import { Badge } from "./ui/badge";

const MAP: Record<
  string,
  { label: string; variant: "success" | "info" | "default" | "warning" | "danger" | "accent" }
> = {
  both_again: { label: "Both Again", variant: "success" },
  both_group: { label: "Both Group", variant: "info" },
  both_pass: { label: "Both Pass", variant: "default" },
  asymmetric_again_group: { label: "Asymmetric: Again vs Group", variant: "warning" },
  asymmetric_again_pass: { label: "Asymmetric: Again vs Pass", variant: "warning" },
  asymmetric_group_pass: { label: "Asymmetric: Group vs Pass", variant: "warning" },
  timed_out: { label: "Timed Out", variant: "danger" },
};

export function OutcomeBadge({ outcome }: { outcome: string | null | undefined }) {
  if (!outcome) {
    return <Badge variant="outline">pending</Badge>;
  }
  const entry = MAP[outcome] ?? { label: outcome, variant: "default" as const };
  return <Badge variant={entry.variant}>{entry.label}</Badge>;
}

const STATE_VARIANT: Record<string, "accent" | "default" | "success" | "warning"> = {
  awaiting_first_response: "warning",
  awaiting_second_response: "warning",
  mutual_reveal_ready: "accent",
  resolving: "accent",
  resolved: "success",
  closed: "default",
};

const STATE_LABEL: Record<string, string> = {
  awaiting_first_response: "Awaiting first",
  awaiting_second_response: "Awaiting second",
  mutual_reveal_ready: "Reveal ready",
  resolving: "Resolving",
  resolved: "Resolved",
  closed: "Closed",
};

export function StateBadge({ state }: { state: string }) {
  return (
    <Badge variant={STATE_VARIANT[state] ?? "default"}>
      {STATE_LABEL[state] ?? state}
    </Badge>
  );
}
