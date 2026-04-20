from __future__ import annotations

from fastapi import APIRouter

from afters.db.mongo import collections, get_db, jsonable

router = APIRouter(prefix="/users", tags=["users"])


@router.get("")
async def list_users():
    db = get_db()
    rows = [jsonable(r) async for r in db[collections.users].find({}).sort("name", 1)]
    return rows


@router.get("/{user_id}")
async def get_user(user_id: str):
    raw = await get_db()[collections.users].find_one({"_id": user_id})
    return jsonable(raw)


@router.get("/{user_id}/active_session")
async def get_active_session(user_id: str):
    """The most recent non-terminal session this user is a participant in.
    Null if they are not currently mid-flow."""
    db = get_db()
    raw = await db[collections.sessions].find_one(
        {
            "state": {
                "$in": [
                    "awaiting_first_response",
                    "awaiting_second_response",
                    "mutual_reveal_ready",
                    "resolving",
                ]
            },
            "participants.user_id": user_id,
        },
        sort=[("created_at", -1)],
    )
    return jsonable(raw)
