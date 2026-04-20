from __future__ import annotations

from fastapi import APIRouter

from afters.db.mongo import collections, get_db, jsonable

router = APIRouter(prefix="/traces", tags=["traces"])


@router.get("")
async def list_traces(
    kind: str | None = None,
    agent_name: str | None = None,
    session_id: str | None = None,
    limit: int = 250,
    sort: str = "created_at",
    direction: int = -1,
):
    db = get_db()
    q: dict = {}
    if kind:
        q["kind"] = kind
    if agent_name:
        q["agent_name"] = agent_name
    if session_id:
        q["session_id"] = session_id
    rows = [
        jsonable(r)
        async for r in db[collections.traces].find(q).sort(sort, direction).limit(limit)
    ]
    return rows
