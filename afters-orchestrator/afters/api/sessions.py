from __future__ import annotations

from fastapi import APIRouter, HTTPException

from afters.db.mongo import collections, get_db, jsonable
from afters.models import AftersSession
from afters.services import start_live_session

router = APIRouter(prefix="/sessions", tags=["sessions"])


@router.post("/live")
async def create_live_session():
    """Start a blank live session: a fresh pair on a same-campus pair with
    no pre-filled replies. The reviewer drives by typing into the chat panes."""
    try:
        return await start_live_session()
    except RuntimeError as exc:
        raise HTTPException(409, str(exc))


@router.get("")
async def list_sessions(
    state: str | None = None,
    campus: str | None = None,
    limit: int = 100,
):
    db = get_db()
    query: dict = {}
    if state:
        query["state"] = state
    if campus:
        query["campus"] = campus
    rows = [
        row
        async for row in db[collections.sessions]
        .find(query)
        .sort("created_at", -1)
        .limit(limit)
    ]

    # Hydrate participant names + date/match info for the table view.
    hydrated = []
    for row in rows:
        session = AftersSession.model_validate(row)
        names = []
        for p in session.participants:
            user = await db[collections.users].find_one({"_id": p.user_id})
            names.append((user or {}).get("name", "?"))
        date = await db[collections.dates].find_one({"_id": session.date_id})
        venue = (
            await db[collections.venues].find_one({"_id": date["venue_id"]})
            if date
            else None
        )
        hydrated.append(
            jsonable(
                {
                    **session.model_dump(by_alias=True),
                    "participant_names": names,
                    "venue_name": (venue or {}).get("name"),
                    "time_to_resolution_seconds": (
                        (session.resolved_at - session.created_at).total_seconds()
                        if session.resolved_at
                        else None
                    ),
                }
            )
        )
    return hydrated


@router.get("/{session_id}")
async def get_session(session_id: str):
    db = get_db()
    row = await db[collections.sessions].find_one({"_id": session_id})
    if row is None:
        raise HTTPException(404, "session not found")
    session = AftersSession.model_validate(row)

    # Participants with user fields.
    participants_hydrated = []
    for p in session.participants:
        user = await db[collections.users].find_one({"_id": p.user_id})
        participants_hydrated.append(
            {
                **p.model_dump(),
                "user": jsonable(user) if user else None,
            }
        )

    date = await db[collections.dates].find_one({"_id": session.date_id})
    venue = (
        await db[collections.venues].find_one({"_id": date["venue_id"]}) if date else None
    )
    match = await db[collections.matches].find_one({"_id": session.match_id})

    traces = [
        jsonable(r)
        async for r in db[collections.traces]
        .find({"session_id": session_id})
        .sort("created_at", 1)
    ]

    second_date = await db[collections.second_dates].find_one({"session_id": session_id})
    if second_date and second_date.get("proposed_venues"):
        venue_ids = [p["venue_id"] for p in second_date["proposed_venues"]]
        venue_docs = {
            v["_id"]: v
            async for v in db[collections.venues].find({"_id": {"$in": venue_ids}})
        }
        for p in second_date["proposed_venues"]:
            p["venue"] = jsonable(venue_docs.get(p["venue_id"]))

    group_entries = [
        jsonable(r)
        async for r in db[collections.group_queue].find({"session_id": session_id})
    ]

    closure = None
    if session.closure_review_id:
        closure = await db[collections.closure_reviews].find_one(
            {"_id": session.closure_review_id}
        )

    return jsonable(
        {
            "session": {
                **session.model_dump(by_alias=True),
                "participants_hydrated": participants_hydrated,
            },
            "date": date,
            "venue": venue,
            "match": match,
            "traces": traces,
            "second_date": second_date,
            "group_queue_entries": group_entries,
            "closure_review": closure,
        }
    )
