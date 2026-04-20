"""Closure review actions.

approve : send draft (or edited body) to recipient, mark review approved, session closed.
edit    : same as approve but using the reviewer's edit.
reject  : regenerate once at higher temperature. Second reject falls back to
          a deterministic generic template.
"""

from __future__ import annotations

from datetime import datetime

from afters.agents import fallback_closure_message, run_closure_agent
from afters.db.mongo import collections, get_db
from afters.db.redis_client import publish_event
from afters.llm.tracing import write_human_feedback_trace
from afters.messaging import send_message
from afters.models import (
    AftersSession,
    ClosureReview,
    DebriefExtraction,
    ParticipantDebrief,
    User,
)


async def _load_review(review_id: str) -> ClosureReview:
    raw = await get_db()[collections.closure_reviews].find_one({"_id": review_id})
    if raw is None:
        raise RuntimeError(f"closure review {review_id} not found")
    return ClosureReview.model_validate(raw)


async def _load_session(session_id: str) -> AftersSession:
    raw = await get_db()[collections.sessions].find_one({"_id": session_id})
    return AftersSession.model_validate(raw)


def _debrief_from_participant(p: ParticipantDebrief) -> DebriefExtraction:
    return DebriefExtraction(
        interest_level=p.interest_level or 0,
        choice=p.choice or "pass",
        wants_second_date=bool(p.wants_second_date),
        willing_to_group_hang=bool(p.willing_to_group_hang),
        memorable_moments=p.memorable_moments,
        concerns=p.concerns,
        free_text_note=p.free_text_note or "",
    )


async def _send_and_close(
    review: ClosureReview, body: str, action: str
) -> ClosureReview:
    db = get_db()
    now = datetime.utcnow()
    await send_message(
        user_id=review.recipient_user_id,
        body=body,
        session_id=review.session_id,
    )
    status = "approved" if action == "approve" else "edited" if action == "edit" else "rejected_fallback"
    await db[collections.closure_reviews].update_one(
        {"_id": review.id},
        {
            "$set": {
                "status": status,
                "final_message": body,
                "reviewer_action_at": now,
            }
        },
    )
    await db[collections.sessions].update_one(
        {"_id": review.session_id},
        {"$set": {"state": "closed", "updated_at": now}},
    )
    await publish_event(
        "closure_review.resolved",
        {"review_id": review.id, "session_id": review.session_id, "status": status},
    )
    return await _load_review(review.id)


async def approve_review(review_id: str) -> ClosureReview:
    review = await _load_review(review_id)
    await write_human_feedback_trace(
        session_id=review.session_id,
        action="approve",
        summary=(
            f"Reviewer approved the Closure Agent draft for "
            f"{review.recipient_name} ({len(review.draft_message.split())} words)."
        ),
        details={"review_id": review.id, "length_words": len(review.draft_message.split())},
    )
    return await _send_and_close(review, review.draft_message, "approve")


async def edit_review(review_id: str, edited_message: str) -> ClosureReview:
    review = await _load_review(review_id)
    await write_human_feedback_trace(
        session_id=review.session_id,
        action="edit",
        summary=(
            f"Reviewer edited the Closure Agent draft for "
            f"{review.recipient_name} (from {len(review.draft_message.split())} "
            f"to {len(edited_message.split())} words)."
        ),
        details={
            "review_id": review.id,
            "original": review.draft_message,
            "edited": edited_message,
        },
    )
    return await _send_and_close(review, edited_message, "edit")


async def reject_review(review_id: str) -> ClosureReview:
    review = await _load_review(review_id)
    db = get_db()
    session = await _load_session(review.session_id)
    a, b = session.participants
    recipient = a if a.user_id == review.recipient_user_id else b
    other = b if recipient is a else a

    if review.regeneration_count >= 1:
        # Fall back to a deterministic template on the second reject.
        fallback = fallback_closure_message(review.recipient_name)
        await write_human_feedback_trace(
            session_id=review.session_id,
            action="reject_fallback",
            summary=(
                f"Reviewer rejected draft #{review.regeneration_count + 1}; "
                f"falling back to deterministic template for {review.recipient_name}."
            ),
            details={"review_id": review.id, "template_used": True},
        )
        return await _send_and_close(review, fallback, "reject")

    # First reject: regenerate with a higher temperature and a different seed.
    await write_human_feedback_trace(
        session_id=review.session_id,
        action="reject_regenerate",
        summary=(
            f"Reviewer rejected the Closure Agent draft; regenerating for "
            f"{review.recipient_name} at higher temperature."
        ),
        details={"review_id": review.id, "regeneration_seed": 1},
    )

    outcome = session.resolved_outcome or "asymmetric_again_pass"
    draft = await run_closure_agent(
        session_id=session.id,
        recipient_name=review.recipient_name,
        recipient_choice=recipient.choice or "again",
        other_choice=other.choice or "pass",
        outcome=outcome,
        recipient_debrief=_debrief_from_participant(recipient),
        other_debrief=_debrief_from_participant(other),
        regeneration_seed=1,
    )
    await db[collections.closure_reviews].update_one(
        {"_id": review.id},
        {
            "$set": {
                "draft_message": draft.message,
                "regeneration_count": review.regeneration_count + 1,
                "status": "pending",
                "reviewer_action_at": datetime.utcnow(),
            }
        },
    )
    await publish_event(
        "closure_review.regenerated",
        {"review_id": review.id, "session_id": review.session_id},
    )
    return await _load_review(review.id)
