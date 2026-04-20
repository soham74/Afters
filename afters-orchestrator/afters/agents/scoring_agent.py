"""Scoring Agent.

Runs at the end of every resolved session. Updates the match compatibility re-score
using a small deterministic formula (to keep the demo auditable) and emits a row
to feedback_training.jsonl.

The prompt for a real LLM re-scorer would go here, but for the demo the value is
in showing that the feedback loop *exists* and the training data accumulates.
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

from afters.db.mongo import collections, get_db
from afters.llm.tracing import write_trace
from afters.models import (
    AftersOutcome,
    AftersSession,
    FeedbackTrainingRow,
    Match,
    ParticipantDebrief,
)

FEEDBACK_FILE = Path(__file__).resolve().parents[2] / "feedback_training.jsonl"


# Outcome-driven score adjustment. Small nudges; real model would learn this.
OUTCOME_DELTA: dict[AftersOutcome, float] = {
    "both_again": +0.05,
    "both_group": +0.02,
    "both_pass": -0.03,
    "asymmetric_again_group": -0.01,
    "asymmetric_again_pass": -0.05,
    "asymmetric_group_pass": -0.04,
    "timed_out": -0.02,
}


def _label_success(outcome: AftersOutcome) -> bool:
    return outcome in {"both_again", "both_group"}


async def run_scoring_agent(
    *,
    session: AftersSession,
    match: Match,
    venue_tags: list[str],
) -> dict:
    """Writes one row to feedback_training.jsonl, returns the updated score.
    Writes a deterministic agent_trace."""
    outcome = session.resolved_outcome or "timed_out"
    delta = OUTCOME_DELTA.get(outcome, 0.0)
    pre = match.compatibility_score
    post = round(max(0.0, min(1.0, pre + delta)), 4)

    a, b = session.participants[0], session.participants[1]

    ttr_hours: float | None = None
    if session.resolved_at and session.created_at:
        ttr_hours = round(
            (session.resolved_at - session.created_at).total_seconds() / 3600, 3
        )

    row = FeedbackTrainingRow(
        session_id=session.id,
        match_id=match.id,
        campus=session.campus,
        compatibility_score_pre=pre,
        user_a_wanted_second=bool(a.wants_second_date),
        user_b_wanted_second=bool(b.wants_second_date),
        user_a_interest=a.interest_level or 0,
        user_b_interest=b.interest_level or 0,
        outcome=outcome,
        venue_tags=venue_tags,
        time_to_resolution_hours=ttr_hours,
        shared_moments=_intersect(a, b),
        concerns=list({*a.concerns, *b.concerns}),
        label_success=_label_success(outcome),
    )

    # Append to the JSONL file that lives next to the orchestrator package.
    with FEEDBACK_FILE.open("a") as fh:
        fh.write(json.dumps(row.model_dump(), default=str) + "\n")

    # Update the match compatibility score in Mongo.
    await get_db()[collections.matches].update_one(
        {"_id": match.id},
        {"$set": {"compatibility_score": post}},
    )

    await write_trace(
        session_id=session.id,
        agent_name="Scoring Agent",
        kind="deterministic",
        input_summary=f"outcome={outcome}; pre={pre}; delta={delta:+.3f}",
        output={"pre": pre, "post": post, "delta": delta},
        summary=(
            f"Scoring Agent {'raised' if delta >= 0 else 'lowered'} match compatibility "
            f"from {pre:.2f} to {post:.2f} after {outcome} "
            f"and wrote 1 row to feedback_training.jsonl."
        ),
        tags=["scoring_agent", outcome],
    )
    return {"pre": pre, "post": post, "delta": delta, "row": row.model_dump()}


def _intersect(a: ParticipantDebrief, b: ParticipantDebrief) -> list[str]:
    sa = {m.lower() for m in a.memorable_moments}
    sb = {m.lower() for m in b.memorable_moments}
    return sorted(sa & sb) or sorted(sa | sb)[:3]
