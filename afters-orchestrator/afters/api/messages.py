"""Messages API.

GET /messages/:user_id - thread for that user (used by dashboard chat view).
POST /webhook/user_reply - called by NestJS when a user types a reply in the
                           dashboard iMessage input. We look up the user's
                           active session and call submit_debrief.
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from afters.db.mongo import collections, get_db, jsonable
from afters.services.session_service import submit_debrief

router = APIRouter(tags=["messages"])


@router.get("/messages/{user_id}")
async def list_thread(user_id: str, limit: int = 200):
    db = get_db()
    rows = [
        jsonable(r)
        async for r in db[collections.messages]
        .find({"user_id": user_id})
        .sort("created_at", 1)
        .limit(limit)
    ]
    return rows


class UserReply(BaseModel):
    user_id: str
    body: str
    session_id: str | None = None


TERMINAL_STATES = {"resolved", "closed"}


@router.post("/webhook/user_reply")
async def user_reply(payload: UserReply):
    """Called by NestJS messaging service whenever a user reply lands.
    We find that user's active session if not provided and call submit_debrief.
    Returns 409 if the session is already resolved or closed so nothing is
    silently written into a dead state machine."""
    db = get_db()
    session_id = payload.session_id
    if session_id is None:
        active = await db[collections.sessions].find_one(
            {
                "state": {
                    "$in": ["awaiting_first_response", "awaiting_second_response"]
                },
                "participants.user_id": payload.user_id,
            },
            sort=[("created_at", -1)],
        )
        if active is None:
            raise HTTPException(404, "no active session for this user")
        session_id = active["_id"]

    session_raw = await db[collections.sessions].find_one({"_id": session_id})
    if session_raw is None:
        raise HTTPException(404, "session not found")
    if session_raw["state"] in TERMINAL_STATES:
        raise HTTPException(
            409,
            "session already resolved. no further replies processed.",
        )

    session = await submit_debrief(
        session_id=session_id, user_id=payload.user_id, reply_text=payload.body
    )
    return jsonable(session.model_dump(by_alias=True))
