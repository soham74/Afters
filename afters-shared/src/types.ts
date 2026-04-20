// Cross-service type surface for Afters.
// Canonical source is afters-shared/schemas/ (JSON Schema draft-07).
// The TypeScript side is this file (hand-written for ergonomics and to colocate
// enums with object shapes). The Python side regenerates Pydantic models from
// the same schemas via datamodel-code-generator. See root README for details.

export type Campus =
  | "UC Berkeley"
  | "UC San Diego"
  | "UCLA"
  | "USC"
  | "UC Davis"
  | "San Jose State";

export type DebriefChoice = "again" | "group" | "pass";

export type ResponseState = "pending" | "submitted" | "revealed";

export type AftersState =
  | "awaiting_first_response"
  | "awaiting_second_response"
  | "mutual_reveal_ready"
  | "resolving"
  | "resolved"
  | "closed";

export type AftersOutcome =
  | "both_again"
  | "both_group"
  | "both_pass"
  | "asymmetric_again_group"
  | "asymmetric_again_pass"
  | "asymmetric_group_pass"
  | "timed_out";

export type DateStatus = "scheduled" | "completed" | "canceled";

export type ScenarioName =
  | "both_again"
  | "both_group"
  | "both_pass"
  | "asymmetric_again_pass"
  | "asymmetric_again_group"
  | "timeout";

export type AgentKind = "llm" | "deterministic" | "human_feedback";

export type MessageDirection = "outbound" | "inbound";

export type MessageKind = "text" | "voice_note" | "card";

export type ClosureReviewStatus =
  | "pending"
  | "approved"
  | "edited"
  | "rejected_fallback";

export type GroupQueueStatus = "queued" | "matched" | "canceled";

export interface ParticipantDebrief {
  user_id: string;
  response_state: ResponseState;
  choice: DebriefChoice | null;
  interest_level: number | null;
  memorable_moments: string[];
  concerns: string[];
  wants_second_date: boolean | null;
  willing_to_group_hang: boolean | null;
  free_text_note: string | null;
  voice_note_ref: string | null;
  raw_reply_text: string | null;
  submitted_at: string | null;
}

export interface AftersSession {
  _id: string;
  date_id: string;
  match_id: string;
  campus: Campus;
  participants: [ParticipantDebrief, ParticipantDebrief];
  state: AftersState;
  resolved_outcome: AftersOutcome | null;
  resolved_at: string | null;
  timeout_at: string;
  created_at: string;
  updated_at: string | null;
  closure_review_id: string | null;
  second_date_id: string | null;
  group_queue_entry_ids: string[];
}

export interface UserProfile {
  preferences: string[];
  interests: string[];
  persona_summary: string;
}

export interface User {
  _id: string;
  name: string;
  edu_email: string;
  campus: Campus;
  year: "freshman" | "sophomore" | "junior" | "senior" | "grad";
  pronouns: string;
  profile: UserProfile;
  avatar_color: string;
  is_historical?: boolean;
}

export interface Match {
  _id: string;
  user_a_id: string;
  user_b_id: string;
  campus: Campus;
  compatibility_score: number;
  explanation: string;
  matched_at: string;
}

export interface DateRecord {
  _id: string;
  match_id: string;
  venue_id: string;
  scheduled_for: string;
  status: DateStatus;
  completed_at: string | null;
  canceled_reason: string | null;
  campus: Campus;
}

export interface Venue {
  _id: string;
  name: string;
  campus: Campus;
  type: string;
  tags: string[];
  vibe: string;
  address: string;
  price_level: 1 | 2 | 3;
  walking_distance_from_campus_min: number;
}

export interface AgentTrace {
  _id: string;
  session_id: string | null;
  agent_name: string;
  kind: AgentKind;
  model: string | null;
  input_summary: string;
  prompt: string | null;
  output: unknown;
  tokens_in: number;
  tokens_out: number;
  cost_usd: number;
  latency_ms: number;
  summary: string;
  tags: string[];
  created_at: string;
}

export interface Message {
  _id: string;
  user_id: string;
  direction: MessageDirection;
  body: string;
  kind: MessageKind;
  card_meta: Record<string, unknown> | null;
  session_id: string | null;
  created_at: string;
}

export interface SecondDateProposal {
  venue_id: string;
  reason: string;
}

export interface SecondDate {
  _id: string;
  session_id: string;
  proposed_venues: SecondDateProposal[];
  proposed_time_slots: string[];
  confirmed_venue_id: string | null;
  confirmed_time: string | null;
  user_a_confirmed: boolean;
  user_b_confirmed: boolean;
  created_at: string;
}

export interface GroupQueueEntry {
  _id: string;
  user_id: string;
  session_id: string;
  campus: Campus;
  tags: string[];
  status: GroupQueueStatus;
  group_event_id: string | null;
  created_at: string;
}

export interface ClosureReview {
  _id: string;
  session_id: string;
  recipient_user_id: string;
  recipient_name: string;
  draft_message: string;
  regeneration_count: number;
  status: ClosureReviewStatus;
  final_message: string | null;
  reviewer_action_at: string | null;
  created_at: string;
}

export interface FeedbackTrainingRow {
  session_id: string;
  match_id: string;
  campus: Campus;
  compatibility_score_pre: number;
  user_a_wanted_second: boolean;
  user_b_wanted_second: boolean;
  user_a_interest: number;
  user_b_interest: number;
  outcome: AftersOutcome;
  venue_tags: string[];
  time_to_resolution_hours: number | null;
  shared_moments: string[];
  concerns: string[];
  label_success: boolean;
  created_at: string;
}

export interface ScenarioDescriptor {
  name: ScenarioName;
  label: string;
  description: string;
  expected_outcome: AftersOutcome;
}
