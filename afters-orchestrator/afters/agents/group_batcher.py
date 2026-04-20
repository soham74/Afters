"""Group Batcher.

Deterministic, rule-based. Extracts tags from a debrief and clusters pending
group_queue entries on the same campus with overlapping tags into a mock
"group hang" event of 4 to 6 people."""

from __future__ import annotations

from itertools import combinations
from uuid import uuid4

from afters.db.mongo import collections, get_db
from afters.llm.tracing import write_trace
from afters.models import Campus, DebriefExtraction, GroupQueueEntry, now


TAG_KEYWORDS: dict[str, list[str]] = {
    "daytime": ["daytime", "coffee", "walk", "brunch", "afternoon"],
    "active": ["walk", "run", "hike", "outdoor", "active", "bike"],
    "quiet": ["quiet", "calm", "conversation", "deeper", "mellow"],
    "music": ["music", "show", "concert", "band", "dj"],
    "low_alcohol": ["sober", "no alcohol", "low alcohol", "mocktail", "coffee"],
    "food_forward": ["food", "dinner", "lunch", "cuisine", "restaurant"],
    "bookish": ["book", "bookstore", "library", "museum"],
    "nightlife": ["bar", "party", "night", "late"],
    "creative": ["art", "studio", "creative", "paint", "draw", "film"],
}


def extract_group_tags(d: DebriefExtraction) -> list[str]:
    tokens = {
        t.lower()
        for m in d.memorable_moments + [d.free_text_note]
        for t in m.lower().replace(",", " ").split()
    }
    hit: list[str] = []
    for tag, keywords in TAG_KEYWORDS.items():
        if any(k in tokens or any(k in tok for tok in tokens) for k in keywords):
            hit.append(tag)
    if not hit:
        hit = ["daytime"]
    return hit


async def batch_group_queue(campus: Campus, min_size: int = 4, max_size: int = 6) -> list[str]:
    """Returns a list of group_event ids formed. Each event groups 4 to 6 queued
    users whose tag sets have >= 2 overlapping tags."""
    db = get_db()
    queued = [
        GroupQueueEntry.model_validate(row)
        async for row in db[collections.group_queue].find(
            {"campus": campus, "status": "queued"}
        )
    ]
    if len(queued) < min_size:
        return []

    events: list[str] = []
    used: set[str] = set()
    for combo in combinations(queued, min_size):
        if any(e.id in used for e in combo):
            continue
        tag_sets = [set(e.tags) for e in combo]
        shared = set.intersection(*tag_sets) if tag_sets else set()
        if len(shared) >= 2:
            event_id = f"grp_{uuid4().hex[:8]}"
            events.append(event_id)
            for e in combo:
                used.add(e.id)
                await db[collections.group_queue].update_one(
                    {"_id": e.id},
                    {"$set": {"status": "matched", "group_event_id": event_id}},
                )

    if events:
        await write_trace(
            session_id=None,
            agent_name="Group Batcher",
            kind="deterministic",
            input_summary=f"campus={campus}; queued={len(queued)}",
            output={"event_ids": events, "batched_users": len(used)},
            summary=(
                f"Group Batcher formed {len(events)} group event(s) "
                f"of {min_size} people each at {campus} from {len(queued)} queued users."
            ),
            tags=["group_batcher", campus],
        )
    return events
