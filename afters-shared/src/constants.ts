import type { ScenarioDescriptor, AftersOutcome, AftersState } from "./types.js";

export const COLORS = {
  accent: "#FF6B5E",
  accentSoft: "#FFE5E1",
  iMessageBlue: "#007AFF",
  iMessageGrey: "#E9E9EB",
  bg: "#FAFAFA",
  fg: "#0A0A0A",
  muted: "#737373",
  border: "#E5E5E5",
  success: "#10B981",
  warning: "#F59E0B",
  danger: "#EF4444",
  info: "#3B82F6",
} as const;

export const CAMPUSES = [
  "UC Berkeley",
  "UC San Diego",
  "UCLA",
  "USC",
  "UC Davis",
  "San Jose State",
] as const;

export const OUTCOME_LABEL: Record<AftersOutcome, string> = {
  both_again: "Both Again",
  both_group: "Both Group",
  both_pass: "Both Pass",
  asymmetric_again_group: "Asymmetric: Again vs Group",
  asymmetric_again_pass: "Asymmetric: Again vs Pass",
  asymmetric_group_pass: "Asymmetric: Group vs Pass",
  timed_out: "Timed Out",
};

export const STATE_LABEL: Record<AftersState, string> = {
  awaiting_first_response: "Awaiting first response",
  awaiting_second_response: "Awaiting second response",
  mutual_reveal_ready: "Mutual reveal ready",
  resolving: "Resolving",
  resolved: "Resolved",
  closed: "Closed",
};

export const SCENARIOS: ScenarioDescriptor[] = [
  {
    name: "both_again",
    label: "Both Again",
    description: "Happy path. Both users pick Again, Venue Agent proposes second-date venues, Scheduler books a time, confirmation message goes out.",
    expected_outcome: "both_again",
  },
  {
    name: "both_group",
    label: "Both Group",
    description: "Both users pick Group. Rule-based batching adds them to the group queue with extracted tags.",
    expected_outcome: "both_group",
  },
  {
    name: "both_pass",
    label: "Both Pass",
    description: "Both users pick Pass. Session resolves silently; both parties get a brief acknowledgment. No Closure Agent, no Venue Agent, no Scheduler.",
    expected_outcome: "both_pass",
  },
  {
    name: "asymmetric_again_pass",
    label: "Asymmetric: Again vs Pass",
    description: "One user picks Again, the other picks Pass. Closure Agent drafts a dignified message for review in the human-in-the-loop queue.",
    expected_outcome: "asymmetric_again_pass",
  },
  {
    name: "asymmetric_again_group",
    label: "Asymmetric: Again vs Group",
    description: "One user picks Again, the other picks Group. Closure Agent drafts a message; the Again party is offered a reroute into the group queue.",
    expected_outcome: "asymmetric_again_group",
  },
  {
    name: "timeout",
    label: "Timeout",
    description: "One user never responds. After TIMEOUT_SECONDS_OVERRIDE seconds the session times out and a soft-close message goes to the responder.",
    expected_outcome: "timed_out",
  },
];

export const STATE_ORDER: AftersState[] = [
  "awaiting_first_response",
  "awaiting_second_response",
  "mutual_reveal_ready",
  "resolving",
  "resolved",
  "closed",
];

// Anthropic model IDs (spec says use these exactly).
export const MODELS = {
  reasoning: "claude-sonnet-4-5",
  extraction: "claude-haiku-4-5",
} as const;

// Rough per-million-token pricing (USD). Used for trace cost estimates.
// Source: Anthropic public pricing as of project start. Update here only.
export const PRICING_USD_PER_MTOK: Record<string, { input: number; output: number }> = {
  "claude-sonnet-4-5": { input: 3.0, output: 15.0 },
  "claude-haiku-4-5": { input: 1.0, output: 5.0 },
};
