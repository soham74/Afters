"""LangGraph state shape.

The graph is invoked AFTER the Mutual Reveal Gate has run and both participants
have submitted. The gate is deliberately not inside the graph: it's a
deterministic prerequisite that we model in plain FastAPI so the post-reveal
fan-out (the interesting agent-orchestration surface) is what LangGraph
visualizes. See root README for the rationale."""

from __future__ import annotations

from typing import Any, TypedDict

from afters.models import AftersOutcome, AftersSession


class GraphState(TypedDict, total=False):
    session_id: str
    outcome: AftersOutcome
    session: dict[str, Any]  # AftersSession as dict for JSON-round-trippability

    # Populated by branch nodes:
    venue_pick_ids: list[str]
    venue_reasons: list[str]
    proposed_time_slots: list[str]
    second_date_id: str

    group_queue_entry_ids: list[str]

    closure_review_id: str
    closure_draft: str

    timed_out_user_id: str | None

    # Populated by Scoring Agent:
    score_pre: float
    score_post: float

    # Populated by any node:
    errors: list[str]
