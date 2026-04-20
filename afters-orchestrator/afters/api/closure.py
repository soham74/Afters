from __future__ import annotations

from fastapi import APIRouter
from pydantic import BaseModel

from afters.db.mongo import collections, get_db, jsonable
from afters.services.closure_service import approve_review, edit_review, reject_review

router = APIRouter(prefix="/closure", tags=["closure"])


@router.get("")
async def list_closure_reviews(status: str | None = None):
    db = get_db()
    q: dict = {}
    if status:
        q["status"] = status
    rows = [
        jsonable(r)
        async for r in db[collections.closure_reviews].find(q).sort("created_at", -1)
    ]
    return rows


@router.get("/{review_id}")
async def get_review(review_id: str):
    raw = await get_db()[collections.closure_reviews].find_one({"_id": review_id})
    return jsonable(raw)


@router.post("/{review_id}/approve")
async def approve(review_id: str):
    review = await approve_review(review_id)
    return jsonable(review.model_dump(by_alias=True))


class EditPayload(BaseModel):
    edited_message: str


@router.post("/{review_id}/edit")
async def edit(review_id: str, payload: EditPayload):
    review = await edit_review(review_id, payload.edited_message)
    return jsonable(review.model_dump(by_alias=True))


@router.post("/{review_id}/reject")
async def reject(review_id: str):
    review = await reject_review(review_id)
    return jsonable(review.model_dump(by_alias=True))
