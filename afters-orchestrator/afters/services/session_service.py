"""Session lifecycle.

create_session          : called when a first date transitions to completed.
submit_debrief          : one user's reply. Runs Debrief Intake, updates participant,
                          then calls mutual_reveal_gate.
mutual_reveal_gate      : deterministic. Writes a trace row (kind=deterministic).
                          When both sides are submitted, computes the outcome and
                          hands off to the LangGraph state machine.
run_timeout_pass        : scanned on an interval; flips overdue sessions to timed_out
                          and runs the LangGraph timeout branch.
"""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Iterable

from afters.agents import run_debrief_intake
from afters.config import get_settings
from afters.db.mongo import collections, get_db
from afters.db.redis_client import publish_event
from afters.graph import run_resolution
from afters.llm.tracing import write_trace
from afters.messaging import send_message
from afters.models import (
    AftersOutcome,
    AftersSession,
    DateRecord,
    Match,
    ParticipantDebrief,
    User,
)


# ----- creation -----


async def create_session(*, date_id: str) -> AftersSession:
    """Create an afters_session for a date that just transitioned to completed.
    Sends the initial debrief prompt to both participants."""
    db = get_db()
    raw_date = await db[collections.dates].find_one({"_id": date_id})
    if raw_date is None:
        raise RuntimeError(f"date {date_id} not found")
    date = DateRecord.model_validate(raw_date)
    raw_match = await db[collections.matches].find_one({"_id": date.match_id})
    match = Match.model_validate(raw_match)

    # If a session already exists, return it (idempotent).
    existing = await db[collections.sessions].find_one({"date_id": date.id})
    if existing is not None:
        return AftersSession.model_validate(existing)

    settings = get_settings()
    now = datetime.utcnow()
    timeout_at = now + timedelta(seconds=settings.timeout_seconds_override)

    session = AftersSession(
        date_id=date.id,
        match_id=match.id,
        campus=match.campus,
        participants=[
            ParticipantDebrief(user_id=match.user_a_id),
            ParticipantDebrief(user_id=match.user_b_id),
        ],
        state="awaiting_first_response",
        timeout_at=timeout_at,
        created_at=now,
    )
    await db[collections.sessions].insert_one(session.model_dump(by_alias=True))

    await publish_event(
        "session.created",
        {"session_id": session.id, "match_id": match.id, "date_id": date.id},
    )
    await write_trace(
        session_id=session.id,
        agent_name="Session Service",
        kind="deterministic",
        input_summary=f"date={date.id}",
        output={"timeout_at": timeout_at.isoformat()},
        summary=(
            f"Session Service created a new afters_session at {match.campus} "
            f"with a {settings.timeout_seconds_override}s timeout."
        ),
        tags=["session.created"],
    )

    # Send the debrief prompt to both users.
    user_a = User.model_validate(
        await db[collections.users].find_one({"_id": match.user_a_id})
    )
    user_b = User.model_validate(
        await db[collections.users].find_one({"_id": match.user_b_id})
    )
    for u in (user_a, user_b):
        first = u.name.split()[0].lower()
        await send_message(
            user_id=u.id,
            body=(
                f"hey {first}. quick check in from afters. "
                "how did it go? you can reply three ways: "
                "again (want another date), group (chill group hang), or "
                "pass (no second date). or just talk to me in your own words "
                "and i'll read between the lines."
            ),
            session_id=session.id,
        )

    return session


# ----- reply path -----


async def submit_debrief(
    *,
    session_id: str,
    user_id: str,
    reply_text: str,
    is_voice_note: bool = False,
    voice_note_ref: str | None = None,
    scenario_mock_tag: str | None = None,
) -> AftersSession:
    """Process one user's reply. Runs Debrief Intake, updates the participant,
    then passes through mutual_reveal_gate which may advance the session."""
    db = get_db()
    raw = await db[collections.sessions].find_one({"_id": session_id})
    if raw is None:
        raise RuntimeError(f"session {session_id} not found")
    session = AftersSession.model_validate(raw)

    # Find the participant.
    part_idx = next(
        (i for i, p in enumerate(session.participants) if p.user_id == user_id),
        None,
    )
    if part_idx is None:
        raise RuntimeError(f"user {user_id} not in session {session_id}")
    participant = session.participants[part_idx]
    if participant.response_state == "submitted":
        # idempotent: ignore duplicate replies during scenario drives.
        return session

    user = User.model_validate(await db[collections.users].find_one({"_id": user_id}))
    extraction = await run_debrief_intake(
        session_id=session.id,
        user_id=user.id,
        user_name=user.name,
        reply_text=reply_text,
        is_voice_note=is_voice_note,
        scenario_mock_tag=scenario_mock_tag,
    )

    participant.choice = extraction.choice
    participant.interest_level = extraction.interest_level
    participant.memorable_moments = extraction.memorable_moments
    participant.concerns = extraction.concerns
    participant.wants_second_date = extraction.wants_second_date
    participant.willing_to_group_hang = extraction.willing_to_group_hang
    participant.free_text_note = extraction.free_text_note
    participant.raw_reply_text = reply_text
    participant.voice_note_ref = voice_note_ref
    participant.response_state = "submitted"
    participant.submitted_at = datetime.utcnow()
    session.participants[part_idx] = participant

    submitted = sum(1 for p in session.participants if p.response_state == "submitted")
    new_state = (
        "awaiting_second_response" if submitted == 1 else "mutual_reveal_ready"
    )
    session.state = new_state
    session.updated_at = datetime.utcnow()

    await db[collections.sessions].update_one(
        {"_id": session.id},
        {
            "$set": {
                "participants": [p.model_dump() for p in session.participants],
                "state": new_state,
                "updated_at": session.updated_at,
            }
        },
    )
    await publish_event(
        "session.debrief_submitted",
        {
            "session_id": session.id,
            "user_id": user_id,
            "state": new_state,
            "choice": extraction.choice,
        },
    )

    if new_state == "mutual_reveal_ready":
        session = await mutual_reveal_gate(session.id, scenario_mock_tag=scenario_mock_tag)

    return session


# ----- gate -----


def determine_outcome(participants: list[ParticipantDebrief]) -> AftersOutcome:
    choices = sorted([p.choice for p in participants if p.choice])
    if choices == ["again", "again"]:
        return "both_again"
    if choices == ["group", "group"]:
        return "both_group"
    if choices == ["pass", "pass"]:
        return "both_pass"
    if choices == ["again", "group"]:
        return "asymmetric_again_group"
    if choices == ["again", "pass"]:
        return "asymmetric_again_pass"
    if choices == ["group", "pass"]:
        return "asymmetric_group_pass"
    raise RuntimeError(f"unknown outcome for choices {choices}")


async def mutual_reveal_gate(
    session_id: str, scenario_mock_tag: str | None = None
) -> AftersSession:
    """Deterministic router. Writes a trace of kind=deterministic and hands the
    session off to the LangGraph state machine for the outcome branch."""
    db = get_db()
    session = AftersSession.model_validate(
        await db[collections.sessions].find_one({"_id": session_id})
    )
    if session.state != "mutual_reveal_ready":
        raise RuntimeError(
            f"gate called on session {session_id} with state {session.state}"
        )

    outcome = determine_outcome(list(session.participants))
    for p in session.participants:
        p.response_state = "revealed"

    await db[collections.sessions].update_one(
        {"_id": session.id},
        {
            "$set": {
                "participants": [p.model_dump() for p in session.participants],
                "state": "resolving",
                "resolved_outcome": outcome,
                "updated_at": datetime.utcnow(),
            }
        },
    )
    await write_trace(
        session_id=session.id,
        agent_name="Mutual Reveal Gate",
        kind="deterministic",
        input_summary=(
            f"{session.participants[0].choice} / "
            f"{session.participants[1].choice}"
        ),
        output={"outcome": outcome},
        summary=(
            f"Mutual Reveal Gate resolved choices "
            f"({session.participants[0].choice}, "
            f"{session.participants[1].choice}) to outcome={outcome}."
        ),
        tags=["mutual_reveal_gate", outcome],
    )
    await publish_event(
        "session.reveal",
        {"session_id": session.id, "outcome": outcome},
    )

    # Kick off LangGraph.
    await run_resolution(session.id, outcome, scenario_mock_tag=scenario_mock_tag)

    # Reload after graph ran.
    return AftersSession.model_validate(
        await db[collections.sessions].find_one({"_id": session.id})
    )


# ----- timeout -----


async def run_timeout_pass() -> list[str]:
    """Scan for sessions past their timeout still awaiting responses.
    Flip them to timed_out, run the LangGraph timeout branch. Returns the
    list of session ids that just timed out."""
    db = get_db()
    now = datetime.utcnow()
    cursor = db[collections.sessions].find(
        {
            "state": {
                "$in": ["awaiting_first_response", "awaiting_second_response"]
            },
            "timeout_at": {"$lte": now},
        }
    )
    timed_out: list[str] = []
    async for raw in cursor:
        session = AftersSession.model_validate(raw)
        await db[collections.sessions].update_one(
            {"_id": session.id},
            {
                "$set": {
                    "state": "resolving",
                    "resolved_outcome": "timed_out",
                    "updated_at": now,
                }
            },
        )
        await write_trace(
            session_id=session.id,
            agent_name="Timeout Watcher",
            kind="deterministic",
            input_summary=f"overdue at {now.isoformat()}",
            output={"outcome": "timed_out"},
            summary=(
                f"Timeout Watcher flipped session {session.id[-6:]} to timed_out "
                f"after missing the {session.timeout_at.isoformat()} deadline."
            ),
            tags=["timeout"],
        )
        await publish_event(
            "session.timeout",
            {"session_id": session.id},
        )
        await run_resolution(session.id, "timed_out")
        timed_out.append(session.id)
    return timed_out
