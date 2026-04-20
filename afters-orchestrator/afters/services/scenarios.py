"""Scenario runner.

Five one-click scenarios produce a fully legible demo: prompt goes out, chat
animates with realistic replies, LangGraph fires, dashboard reflects every
state transition and trace.

Each scenario creates a fresh completed date between two specific seeded users
so metric history is not polluted and each scenario is re-triggerable.
"""

from __future__ import annotations

import asyncio
import random
from datetime import datetime, timedelta
from typing import Any

from afters.agents.closure_agent import run_closure_agent  # noqa: F401 (ensures import graph)
from afters.db.mongo import collections, get_db
from afters.db.redis_client import publish_event
from afters.llm.mock import register_mock
from afters.messaging import send_message
from afters.models import (
    DateRecord,
    Match,
    Message,
    ScenarioName,
    User,
    Venue,
    now,
    oid,
)
from afters.services.session_service import create_session, submit_debrief


# Each scenario pins its pair by user-name-lookup. Keeps the demo stable even
# if ObjectIds drift after a reseed.
SCENARIOS: dict[ScenarioName, dict[str, Any]] = {
    "both_again": {
        "label": "Both Again",
        "pair_names": ("Maya Chen", "Jordan Park"),
        "campus": "UC Berkeley",
        "replies": {
            "a": (
                "honestly had so much fun. they're genuinely funny and we just got each "
                "other's weird food jokes. would 100% want to see them again. maybe "
                "somewhere we can walk around and keep talking"
            ),
            "b": (
                "super good vibe. laughed more than i expected. i'd see them again for "
                "sure. i think i'd be down for anything with more walking and less loud "
                "music though"
            ),
        },
        "a_voice_note": True,
        "b_voice_note": False,
    },
    "both_group": {
        "label": "Both Group",
        "pair_names": ("Rohan Gupta", "Aditi Shah"),
        "campus": "UC Berkeley",
        "replies": {
            "a": (
                "they were genuinely fun to hang out with but i think more as friends. "
                "would be down for a group hang though, i could see us all meshing at a "
                "brunch thing or coffee walk"
            ),
            "b": (
                "honestly i think a group vibe is where i land. liked them a lot but "
                "not quite second-date energy. would love to hang in a group, low key "
                "daytime kind of thing"
            ),
        },
    },
    "both_pass": {
        "label": "Both Pass",
        "pair_names": ("Lena Schmidt", "Noah Osei"),
        "campus": "UC San Diego",
        "replies": {
            "a": "not feeling a spark, thanks though",
            "b": (
                "they were nice but not for me. sweet energy, just not quite romantic "
                "for me. gonna pass on a second"
            ),
        },
    },
    "asymmetric_again_pass": {
        "label": "Asymmetric: Again vs Pass",
        "pair_names": ("Priya Patel", "Ethan Wu"),
        "campus": "UC San Diego",
        "replies": {
            "a": (
                "genuinely had the best time. they're really thoughtful and a great "
                "listener and i want to see them again for sure"
            ),
            "b": (
                "they were nice but honestly it felt more like a friendly coffee than "
                "a date. not a match for me romantically, gonna pass on a second one"
            ),
        },
    },
    "asymmetric_again_group": {
        "label": "Asymmetric: Again vs Group",
        "pair_names": ("Zoe Martinez", "Tyler Brooks"),
        "campus": "UC San Diego",
        "replies": {
            "a": (
                "really want another date with them. they had such a cool way of "
                "listening and i want to keep the conversation going one on one"
            ),
            "b": (
                "good energy all around. i think i vibe with them more as a friend "
                "though, would love to keep seeing them in a group hang if that's a thing"
            ),
        },
    },
    "timeout": {
        "label": "Timeout",
        "pair_names": ("Sam Rivera", "Lucas Kim"),
        "campus": "UC Berkeley",
        "replies": {
            "a": (
                "date was solid honestly. laughed a lot. would love to see them again"
            ),
            "b": None,  # never responds
        },
    },
}


async def _find_user_by_name(name: str) -> User:
    db = get_db()
    raw = await db[collections.users].find_one({"name": name})
    if raw is None:
        raise RuntimeError(f"seed missing user '{name}'")
    return User.model_validate(raw)


async def _pick_venue(campus: str) -> Venue:
    raw = await get_db()[collections.venues].find_one({"campus": campus})
    if raw is None:
        raise RuntimeError(f"no venues seeded for {campus}")
    return Venue.model_validate(raw)


async def _create_completed_date_for_scenario(
    name: str,
    campus: str,
    user_a: User,
    user_b: User,
) -> tuple[Match, DateRecord]:
    db = get_db()
    venue = await _pick_venue(campus)
    match = Match(
        user_a_id=user_a.id,
        user_b_id=user_b.id,
        campus=campus,  # type: ignore[arg-type]
        compatibility_score=0.82,
        explanation=f"seeded by scenario {name}",
        matched_at=now() - timedelta(days=7),
    )
    await db[collections.matches].insert_one(match.model_dump(by_alias=True))

    date = DateRecord(
        match_id=match.id,
        venue_id=venue.id,
        scheduled_for=now() - timedelta(days=1, hours=3),
        status="completed",
        completed_at=now() - timedelta(hours=2),
        campus=campus,  # type: ignore[arg-type]
    )
    await db[collections.dates].insert_one(date.model_dump(by_alias=True))
    return match, date


async def _fake_inbound(
    *, user_id: str, body: str, kind: str = "text", session_id: str | None = None
) -> Message:
    """Write an inbound message directly to mongo + push to chat channel, so the
    dashboard chat view shows the scenario's canned reply appearing."""
    msg = Message(
        user_id=user_id,
        direction="inbound",
        body=body,
        kind=kind,  # type: ignore[arg-type]
        session_id=session_id,
    )
    await get_db()[collections.messages].insert_one(msg.model_dump(by_alias=True))
    await publish_event(
        "message.inbound",
        {"user_id": user_id, "body": body, "session_id": session_id},
    )
    return msg


async def run_scenario(name: ScenarioName) -> dict[str, Any]:
    data = SCENARIOS[name]
    pair_names = data["pair_names"]
    user_a = await _find_user_by_name(pair_names[0])
    user_b = await _find_user_by_name(pair_names[1])
    match, date = await _create_completed_date_for_scenario(
        name, data["campus"], user_a, user_b
    )
    session = await create_session(date_id=date.id)

    await publish_event(
        "scenario.started",
        {"scenario": name, "session_id": session.id, "pair": list(pair_names)},
    )

    # Let the initial prompts render in chat.
    await asyncio.sleep(1.2)

    # User A replies.
    await _fake_inbound(
        user_id=user_a.id, body=data["replies"]["a"], session_id=session.id
    )
    await asyncio.sleep(0.4)
    await submit_debrief(
        session_id=session.id,
        user_id=user_a.id,
        reply_text=data["replies"]["a"],
        is_voice_note=bool(data.get("a_voice_note")),
        voice_note_ref=(f"vn_{user_a.id}_{name}" if data.get("a_voice_note") else None),
    )

    # Timeout scenario: bail out. The timeout watcher will flip the session.
    if data["replies"]["b"] is None:
        return {
            "scenario": name,
            "session_id": session.id,
            "note": "awaiting_timeout",
        }

    # Small pause so the dashboard has a visible "awaiting_second_response" window.
    await asyncio.sleep(1.6)

    await _fake_inbound(
        user_id=user_b.id, body=data["replies"]["b"], session_id=session.id
    )
    await asyncio.sleep(0.4)
    await submit_debrief(
        session_id=session.id,
        user_id=user_b.id,
        reply_text=data["replies"]["b"],
        is_voice_note=bool(data.get("b_voice_note")),
    )

    return {"scenario": name, "session_id": session.id}


async def start_live_session() -> dict[str, Any]:
    """Start a session the reviewer will drive by typing into the iMessage panes.

    Picks two users on the same campus who are not already in an active session,
    creates a fresh match + completed date, opens the afters_session, and sends
    the initial debrief prompt. Does NOT pre-fill any user replies. The rest of
    the flow is driven by the /messages/reply webhook path: user types, NestJS
    forwards, Debrief Intake runs against real Haiku, state machine advances.
    """
    db = get_db()
    active_states = [
        "awaiting_first_response",
        "awaiting_second_response",
        "mutual_reveal_ready",
        "resolving",
    ]
    busy_ids: set[str] = set()
    async for s in db[collections.sessions].find(
        {"state": {"$in": active_states}}, {"participants.user_id": 1}
    ):
        for p in s.get("participants", []):
            busy_ids.add(p["user_id"])

    by_campus: dict[str, list[User]] = {}
    async for raw in db[collections.users].find({}):
        u = User.model_validate(raw)
        if u.id in busy_ids:
            continue
        by_campus.setdefault(u.campus, []).append(u)

    eligible = [(c, us) for c, us in by_campus.items() if len(us) >= 2]
    if not eligible:
        raise RuntimeError(
            "no campus has two free users right now. "
            "resolve or close some in-flight sessions first."
        )

    campus, pool = random.choice(eligible)
    user_a, user_b = random.sample(pool, 2)

    match, date = await _create_completed_date_for_scenario(
        "live", campus, user_a, user_b
    )
    session = await create_session(date_id=date.id)

    await publish_event(
        "scenario.started",
        {
            "scenario": "live",
            "session_id": session.id,
            "pair": [user_a.name, user_b.name],
            "campus": campus,
        },
    )

    return {
        "scenario": "live",
        "session_id": session.id,
        "pair": [user_a.name, user_b.name],
        "campus": campus,
    }


async def reset_demo_data() -> dict[str, Any]:
    """Wipe sessions/messages/traces/closure reviews/second_dates/group_queue and
    re-run the seed. Users, matches, dates, and venues are left untouched unless
    the seed reasserts them."""
    from scripts.seed import run_seed  # lazy import to avoid circular

    db = get_db()
    for c in (
        collections.sessions,
        collections.traces,
        collections.messages,
        collections.closure_reviews,
        collections.second_dates,
        collections.group_queue,
    ):
        await db[c].delete_many({})

    summary = await run_seed(clear_core=True)
    await publish_event("demo.reset", {"summary": summary})
    return summary
