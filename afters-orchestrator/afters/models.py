"""Pydantic models for the orchestrator.

These are hand-written for DX and kept deliberately aligned with the JSON Schemas in
afters-shared/schemas/. The codegen path (datamodel-code-generator) exists for diffing
to catch drift, not for runtime regeneration. See root README.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from bson import ObjectId
from pydantic import BaseModel, ConfigDict, Field

Campus = Literal[
    "UC Berkeley",
    "UC San Diego",
    "UCLA",
    "USC",
    "UC Davis",
    "San Jose State",
]
DebriefChoice = Literal["again", "group", "pass"]
ResponseState = Literal["pending", "submitted", "revealed"]
AftersState = Literal[
    "awaiting_first_response",
    "awaiting_second_response",
    "mutual_reveal_ready",
    "resolving",
    "resolved",
    "closed",
]
AftersOutcome = Literal[
    "both_again",
    "both_group",
    "both_pass",
    "asymmetric_again_group",
    "asymmetric_again_pass",
    "asymmetric_group_pass",
    "timed_out",
]
DateStatus = Literal["scheduled", "completed", "canceled"]
AgentKind = Literal["llm", "deterministic", "human_feedback"]
MessageDirection = Literal["outbound", "inbound"]
MessageKind = Literal["text", "voice_note", "card"]
ClosureReviewStatus = Literal["pending", "approved", "edited", "rejected_fallback"]
GroupQueueStatus = Literal["queued", "matched", "canceled"]

ScenarioName = Literal[
    "both_again",
    "both_group",
    "both_pass",
    "asymmetric_again_pass",
    "asymmetric_again_group",
    "timeout",
]


def oid() -> str:
    """New Mongo-compatible ObjectId as hex string. We store ids as strings throughout."""
    return str(ObjectId())


def now() -> datetime:
    return datetime.utcnow()


class Base(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True, populate_by_name=True)


# Static entities


class UserProfile(Base):
    preferences: list[str] = Field(default_factory=list)
    interests: list[str] = Field(default_factory=list)
    persona_summary: str = ""


class User(Base):
    id: str = Field(default_factory=oid, alias="_id")
    name: str
    edu_email: str
    campus: Campus
    year: Literal["freshman", "sophomore", "junior", "senior", "grad"]
    pronouns: str
    profile: UserProfile
    avatar_color: str
    is_historical: bool = False


class Match(Base):
    id: str = Field(default_factory=oid, alias="_id")
    user_a_id: str
    user_b_id: str
    campus: Campus
    compatibility_score: float
    explanation: str
    matched_at: datetime = Field(default_factory=now)


class DateRecord(Base):
    id: str = Field(default_factory=oid, alias="_id")
    match_id: str
    venue_id: str
    scheduled_for: datetime
    status: DateStatus
    completed_at: datetime | None = None
    canceled_reason: str | None = None
    campus: Campus


class Venue(Base):
    id: str = Field(default_factory=oid, alias="_id")
    name: str
    campus: Campus
    type: str
    tags: list[str]
    vibe: str
    address: str
    price_level: int = Field(ge=1, le=3)
    walking_distance_from_campus_min: int = Field(ge=0)


# The core session


class ParticipantDebrief(Base):
    user_id: str
    response_state: ResponseState = "pending"
    choice: DebriefChoice | None = None
    interest_level: int | None = Field(default=None, ge=0, le=10)
    memorable_moments: list[str] = Field(default_factory=list)
    concerns: list[str] = Field(default_factory=list)
    wants_second_date: bool | None = None
    willing_to_group_hang: bool | None = None
    free_text_note: str | None = None
    voice_note_ref: str | None = None
    raw_reply_text: str | None = None
    submitted_at: datetime | None = None


class AftersSession(Base):
    id: str = Field(default_factory=oid, alias="_id")
    date_id: str
    match_id: str
    campus: Campus
    participants: list[ParticipantDebrief]
    state: AftersState = "awaiting_first_response"
    resolved_outcome: AftersOutcome | None = None
    resolved_at: datetime | None = None
    timeout_at: datetime
    created_at: datetime = Field(default_factory=now)
    updated_at: datetime | None = None
    closure_review_id: str | None = None
    second_date_id: str | None = None
    group_queue_entry_ids: list[str] = Field(default_factory=list)


# Agent traces (the heart of the observability story)


class AgentTrace(Base):
    id: str = Field(default_factory=oid, alias="_id")
    session_id: str | None = None
    agent_name: str
    kind: AgentKind
    model: str | None = None
    input_summary: str
    prompt: str | None = None
    output: Any = None
    tokens_in: int = 0
    tokens_out: int = 0
    cost_usd: float = 0.0
    latency_ms: int = 0
    summary: str
    tags: list[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=now)


# Messaging


class Message(Base):
    id: str = Field(default_factory=oid, alias="_id")
    user_id: str
    direction: MessageDirection
    body: str
    kind: MessageKind = "text"
    card_meta: dict[str, Any] | None = None
    session_id: str | None = None
    created_at: datetime = Field(default_factory=now)


# Downstream artifacts


class VenueProposal(Base):
    venue_id: str
    reason: str


class SecondDate(Base):
    id: str = Field(default_factory=oid, alias="_id")
    session_id: str
    proposed_venues: list[VenueProposal]
    proposed_time_slots: list[str]
    confirmed_venue_id: str | None = None
    confirmed_time: str | None = None
    user_a_confirmed: bool = False
    user_b_confirmed: bool = False
    created_at: datetime = Field(default_factory=now)


class GroupQueueEntry(Base):
    id: str = Field(default_factory=oid, alias="_id")
    user_id: str
    session_id: str
    campus: Campus
    tags: list[str]
    status: GroupQueueStatus = "queued"
    group_event_id: str | None = None
    created_at: datetime = Field(default_factory=now)


class ClosureReview(Base):
    id: str = Field(default_factory=oid, alias="_id")
    session_id: str
    recipient_user_id: str
    recipient_name: str
    draft_message: str
    regeneration_count: int = 0
    status: ClosureReviewStatus = "pending"
    final_message: str | None = None
    reviewer_action_at: datetime | None = None
    created_at: datetime = Field(default_factory=now)


class FeedbackTrainingRow(Base):
    session_id: str
    match_id: str
    campus: Campus
    compatibility_score_pre: float
    user_a_wanted_second: bool
    user_b_wanted_second: bool
    user_a_interest: int
    user_b_interest: int
    outcome: AftersOutcome
    venue_tags: list[str]
    time_to_resolution_hours: float | None
    shared_moments: list[str]
    concerns: list[str]
    label_success: bool
    created_at: datetime = Field(default_factory=now)


# Structured outputs used by agents (Anthropic tool input schemas)


class DebriefExtraction(Base):
    """Structured output from the Debrief Intake Agent."""

    interest_level: int = Field(ge=0, le=10, description="0 bored to 10 sparks")
    choice: DebriefChoice = Field(description="again, group, or pass")
    wants_second_date: bool
    willing_to_group_hang: bool
    memorable_moments: list[str] = Field(
        description="1 to 4 short phrases capturing specific things the user mentioned",
        max_length=6,
    )
    concerns: list[str] = Field(
        description="0 to 3 short phrases summarizing anything that gave them pause",
        max_length=4,
    )
    free_text_note: str = Field(
        description="one-sentence paraphrase of what the user said",
        max_length=280,
    )


class VenueRanking(Base):
    """Structured output from the Venue Agent."""

    picks: list[VenueProposal] = Field(
        description="exactly 3 venue picks ranked best first with a one-sentence reason each",
        min_length=3,
        max_length=3,
    )


class ClosureDraft(Base):
    """Structured output from the Closure Agent."""

    message: str = Field(
        description="Gen Z casual closure message addressed to the recipient, lowercase, no em dashes, no exclamation points unless genuinely warm",
        max_length=400,
    )
