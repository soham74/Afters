"""Backfill historical chat threads with Claude.

Old seed rows (before the in-seed message generator shipped) have empty chat
panes. This service calls sonnet-4-5 for each such session to produce a
believable iMessage thread: Ditto's debrief prompt to each user, each user's
inbound reply shaped by their known choice + memorable moments, and an
outcome-appropriate confirmation. Side effect: updates each participant's
`raw_reply_text` to the generated inbound reply so the structured debrief
panel stops reading as "[historical, synthesized]".

Every call writes one `agent_traces` row via the LLM client, so backfill
activity is visible in the Traces view alongside normal agent traffic.
"""

from __future__ import annotations

import asyncio
from datetime import timedelta
from typing import Literal

from pydantic import Field

from afters.db.mongo import collections, get_db
from afters.llm.client import get_llm
from afters.models import AftersSession, Base, Message, User


class BackfilledMessage(Base):
    who: Literal["a", "b"] = Field(
        description="Which participant this message is FOR. Outbound = Ditto -> that user, inbound = that user -> Ditto."
    )
    direction: Literal["outbound", "inbound"]
    body: str = Field(max_length=500)


class BackfilledThread(Base):
    messages: list[BackfilledMessage] = Field(
        min_length=4,
        max_length=8,
        description=(
            "4 to 8 messages: one outbound prompt to user a, one inbound reply from a, "
            "one outbound prompt to user b, one inbound reply from b, and optional "
            "outbound confirmation(s) per outcome (skip for asymmetric outcomes since "
            "those are pending human review)."
        ),
    )


SYSTEM = """You are the Afters post-date chat historian. Given a resolved session between two college students, write the iMessage thread that would have played out between Ditto's AI assistant and both users.

Voice rules (hard):
- lowercase only, apostrophes kept in contractions (don't, you'll, i'd, we'll, aren't, that's).
- Gen Z casual. Short sentences. No em dashes. No exclamation points unless genuinely warm (rare here).
- Each message fits in a text bubble, under 60 words.
- Never invert the interest signal. If a user picked "group", they wanted a lower-stakes group hang (not rejection). If they picked "pass", they opted out.

What to include:
- One outbound message from Ditto to user A asking how the date went.
- One inbound reply from user A shaped by their choice, interest_level, and memorable_moments.
- One outbound message from Ditto to user B asking how the date went.
- One inbound reply from user B.
- For outcome both_again: one outbound confirmation to each user saying the second date is being set up at the venue they already went to or nearby.
- For outcome both_group: one outbound confirmation to each user saying they are in the group queue.
- For outcome both_pass: one outbound gentle acknowledgment to each user.
- For outcome timed_out: one outbound soft-close to whichever user actually replied; no outbound to the one who did not.
- For asymmetric outcomes (asymmetric_again_pass, asymmetric_again_group, asymmetric_group_pass): STOP after the two replies. Closure is pending human review.

Each message has a `who` field ("a" or "b") telling the caller which participant it is for, and a `direction` ("outbound" from Ditto to that user, or "inbound" from that user to Ditto).
"""


async def _load_user(user_id: str) -> User:
    raw = await get_db()[collections.users].find_one({"_id": user_id})
    return User.model_validate(raw)


async def backfill_messages_for_session(
    session: AftersSession,
    *,
    force: bool = False,
) -> int:
    """Generate and insert a Claude-written iMessage thread for one session.

    No-op if the session already has messages and `force` is False. Returns
    the number of messages written.
    """
    db = get_db()
    existing = await db[collections.messages].count_documents({"session_id": session.id})
    if existing > 0 and not force:
        return 0
    if existing > 0 and force:
        await db[collections.messages].delete_many({"session_id": session.id})

    user_a = await _load_user(session.participants[0].user_id)
    user_b = await _load_user(session.participants[1].user_id)

    date_raw = await db[collections.dates].find_one({"_id": session.date_id})
    venue_name = "the first-date venue"
    if date_raw:
        venue_raw = await db[collections.venues].find_one({"_id": date_raw["venue_id"]})
        if venue_raw:
            venue_name = venue_raw["name"]

    p_a = session.participants[0]
    p_b = session.participants[1]

    user_msg = (
        f"Campus: {session.campus}\n"
        f"First-date venue: {venue_name}\n"
        f"Outcome: {session.resolved_outcome}\n\n"
        f"User A ({user_a.name}, {user_a.year} {user_a.pronouns}): "
        f"persona = {user_a.profile.persona_summary}. "
        f"They picked '{p_a.choice}' with interest {p_a.interest_level}/10. "
        f"Memorable moments: {p_a.memorable_moments or 'none recorded'}. "
        f"Concerns: {p_a.concerns or 'none'}.\n\n"
        f"User B ({user_b.name}, {user_b.year} {user_b.pronouns}): "
        f"persona = {user_b.profile.persona_summary}. "
        f"They picked '{p_b.choice}' with interest {p_b.interest_level}/10. "
        f"Memorable moments: {p_b.memorable_moments or 'none recorded'}. "
        f"Concerns: {p_b.concerns or 'none'}.\n\n"
        "Write the thread."
    )

    def summary(parsed: BackfilledThread, latency_ms: int) -> str:
        return (
            f"Backfill Agent generated a {len(parsed.messages)}-message thread "
            f"for session {session.id[-6:]} ({session.resolved_outcome}) "
            f"in {latency_ms}ms using sonnet."
        )

    thread = await get_llm().structured(
        agent_name="Backfill Agent",
        session_id=session.id,
        model="claude-sonnet-4-5",
        system=SYSTEM,
        user=user_msg,
        schema_cls=BackfilledThread,
        tool_name="emit_thread",
        tool_description="Emit the full iMessage thread for this historical session.",
        summary_builder=summary,
        input_summary=(
            f"{user_a.name} + {user_b.name} @ {session.campus}; "
            f"outcome={session.resolved_outcome}"
        ),
        temperature=0.7,
        tags=["backfill_agent", "sonnet", session.resolved_outcome or "unresolved"],
    )

    user_map = {"a": user_a, "b": user_b}
    start = session.created_at
    msgs: list[Message] = []
    for i, m in enumerate(thread.messages):
        target = user_map[m.who]
        created_at = start + timedelta(minutes=i * 7)
        msgs.append(
            Message(
                user_id=target.id,
                direction=m.direction,
                body=m.body,
                kind="text",
                session_id=session.id,
                created_at=created_at,
            )
        )

    if msgs:
        await db[collections.messages].insert_many(
            [m.model_dump(by_alias=True) for m in msgs]
        )

    # Stash each user's generated inbound reply on their participant record
    # so the structured-debrief "raw reply" panel stops showing the old
    # "[historical, synthesized]" placeholder.
    a_reply = next(
        (m.body for m in thread.messages if m.who == "a" and m.direction == "inbound"),
        None,
    )
    b_reply = next(
        (m.body for m in thread.messages if m.who == "b" and m.direction == "inbound"),
        None,
    )
    set_fields: dict = {}
    if a_reply:
        set_fields["participants.0.raw_reply_text"] = a_reply
    if b_reply:
        set_fields["participants.1.raw_reply_text"] = b_reply
    if set_fields:
        await db[collections.sessions].update_one(
            {"_id": session.id}, {"$set": set_fields}
        )

    return len(msgs)


async def backfill_all_missing(concurrency: int = 5, force: bool = False) -> dict:
    """Find every resolved or closed session with no messages and backfill
    concurrently. Returns a summary dict for the admin caller."""
    db = get_db()
    targets: list[AftersSession] = []
    async for raw in db[collections.sessions].find(
        {"state": {"$in": ["resolved", "closed"]}}
    ):
        session = AftersSession.model_validate(raw)
        if force:
            targets.append(session)
        else:
            count = await db[collections.messages].count_documents(
                {"session_id": session.id}
            )
            if count == 0:
                targets.append(session)

    sem = asyncio.Semaphore(concurrency)

    async def _one(s: AftersSession) -> int:
        async with sem:
            try:
                return await backfill_messages_for_session(s, force=force)
            except Exception as exc:  # noqa: BLE001 - log and continue
                print(f"[backfill] session {s.id} failed: {exc}")
                return 0

    counts = await asyncio.gather(*[_one(s) for s in targets])
    return {
        "sessions_inspected": len(targets),
        "sessions_backfilled": sum(1 for c in counts if c > 0),
        "messages_written": sum(counts),
        "force": force,
    }
