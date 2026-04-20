"""LangGraph post-reveal state machine.

Nodes:
    route_by_outcome (conditional, entry)
    both_again_venue    -> both_again_schedule -> both_again_confirm -> scoring_agent
    both_group_batch    -> both_group_confirm -> scoring_agent
    both_pass_noop      -> scoring_agent
    asymmetric_closure  -> asymmetric_queue   -> scoring_agent
    timeout_handler                            -> scoring_agent
    scoring_agent -> END

Each node is a thin wrapper that (1) reads the current session from Mongo,
(2) calls one agent, (3) updates Mongo, (4) updates the Redis event stream.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from langgraph.graph import END, StateGraph

from afters.agents import (
    batch_group_queue,
    extract_group_tags,
    fallback_closure_message,
    propose_time_slots,
    run_closure_agent,
    run_scoring_agent,
    run_venue_agent,
)
from afters.db.mongo import collections, get_db
from afters.db.redis_client import publish_event
from afters.graph.state import GraphState
from afters.messaging import fmt_dt, send_message
from afters.models import (
    AftersOutcome,
    AftersSession,
    ClosureReview,
    GroupQueueEntry,
    Match,
    ParticipantDebrief,
    SecondDate,
    User,
    Venue,
    VenueProposal,
    DebriefExtraction,
)


# ---------- shared helpers ----------


async def _load_session(session_id: str) -> AftersSession:
    db = get_db()
    raw = await db[collections.sessions].find_one({"_id": session_id})
    if raw is None:
        raise RuntimeError(f"session {session_id} not found")
    return AftersSession.model_validate(raw)


async def _load_user(user_id: str) -> User:
    raw = await get_db()[collections.users].find_one({"_id": user_id})
    return User.model_validate(raw)


async def _load_match(match_id: str) -> Match:
    raw = await get_db()[collections.matches].find_one({"_id": match_id})
    return Match.model_validate(raw)


async def _load_first_date_venue(date_id: str) -> Venue:
    db = get_db()
    date = await db[collections.dates].find_one({"_id": date_id})
    venue = await db[collections.venues].find_one({"_id": date["venue_id"]})
    return Venue.model_validate(venue)


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


async def _update_session(session_id: str, update: dict[str, Any]) -> None:
    update["updated_at"] = datetime.utcnow()
    await get_db()[collections.sessions].update_one(
        {"_id": session_id}, {"$set": update}
    )
    await publish_event("session.updated", {"session_id": session_id, **update})


# ---------- nodes ----------


async def node_route(state: GraphState) -> GraphState:
    # Passthrough. The conditional edge function reads state["outcome"].
    return state


def _route_outcome(state: GraphState) -> str:
    outcome = state["outcome"]
    return {
        "both_again": "both_again_venue",
        "both_group": "both_group_batch",
        "both_pass": "both_pass_noop",
        "asymmetric_again_group": "asymmetric_closure",
        "asymmetric_again_pass": "asymmetric_closure",
        "asymmetric_group_pass": "asymmetric_closure",
        "timed_out": "timeout_handler",
    }[outcome]


# ---------- Both Again branch ----------


async def node_both_again_venue(state: GraphState) -> GraphState:
    session = await _load_session(state["session_id"])
    user_a = await _load_user(session.participants[0].user_id)
    user_b = await _load_user(session.participants[1].user_id)
    first_venue = await _load_first_date_venue(session.date_id)

    ranking = await run_venue_agent(
        session_id=session.id,
        campus=session.campus,
        user_a_name=user_a.name,
        user_b_name=user_b.name,
        user_a_debrief=_debrief_from_participant(session.participants[0]),
        user_b_debrief=_debrief_from_participant(session.participants[1]),
        first_date_venue=first_venue,
        scenario_mock_tag=state.get("scenario_mock_tag"),
    )
    state["venue_pick_ids"] = [p.venue_id for p in ranking.picks]
    state["venue_reasons"] = [p.reason for p in ranking.picks]
    return state


async def node_both_again_schedule(state: GraphState) -> GraphState:
    session = await _load_session(state["session_id"])
    u_a = await _load_user(session.participants[0].user_id)
    u_b = await _load_user(session.participants[1].user_id)
    slots = await propose_time_slots(
        session_id=session.id,
        pair_label=f"{u_a.name} + {u_b.name}",
        count=3,
    )
    state["proposed_time_slots"] = slots
    return state


async def node_both_again_confirm(state: GraphState) -> GraphState:
    session = await _load_session(state["session_id"])
    db = get_db()

    proposals = [
        VenueProposal(venue_id=vid, reason=reason)
        for vid, reason in zip(
            state["venue_pick_ids"], state["venue_reasons"], strict=False
        )
    ]
    sd = SecondDate(
        session_id=session.id,
        proposed_venues=proposals,
        proposed_time_slots=state["proposed_time_slots"],
    )
    await db[collections.second_dates].insert_one(sd.model_dump(by_alias=True))

    # Send poster-style confirmation to both users.
    top_venue = await db[collections.venues].find_one(
        {"_id": state["venue_pick_ids"][0]}
    )
    top = Venue.model_validate(top_venue)
    top_time = state["proposed_time_slots"][0]

    for p in session.participants:
        user = await _load_user(p.user_id)
        first_name = user.name.split()[0].lower()
        await send_message(
            user_id=user.id,
            body=(
                f"good news {first_name}. they also said yes to a second one. "
                f"we picked {top.name} for you on {fmt_dt(top_time)}. "
                "reply yes to lock it in, or type another time if that doesn't work."
            ),
            kind="card",
            session_id=session.id,
            card_meta={
                "kind": "second_date_offer",
                "venue_id": top.id,
                "venue_name": top.name,
                "venue_address": top.address,
                "proposed_time": top_time,
                "proposed_time_human": fmt_dt(top_time),
                "picks": state["venue_pick_ids"],
                "reasons": state["venue_reasons"],
                "time_slots": state["proposed_time_slots"],
            },
        )

    state["second_date_id"] = sd.id
    await _update_session(
        session.id,
        {"second_date_id": sd.id, "state": "resolved", "resolved_at": datetime.utcnow()},
    )
    return state


# ---------- Both Group branch ----------


async def node_both_group_batch(state: GraphState) -> GraphState:
    session = await _load_session(state["session_id"])
    db = get_db()
    entry_ids: list[str] = []
    for p in session.participants:
        tags = extract_group_tags(_debrief_from_participant(p))
        entry = GroupQueueEntry(
            user_id=p.user_id,
            session_id=session.id,
            campus=session.campus,
            tags=tags,
        )
        await db[collections.group_queue].insert_one(entry.model_dump(by_alias=True))
        entry_ids.append(entry.id)

    # Try to batch immediately. May no-op if not enough queued.
    await batch_group_queue(session.campus)
    state["group_queue_entry_ids"] = entry_ids
    return state


async def node_both_group_confirm(state: GraphState) -> GraphState:
    session = await _load_session(state["session_id"])
    for p in session.participants:
        user = await _load_user(p.user_id)
        first_name = user.name.split()[0].lower()
        await send_message(
            user_id=user.id,
            body=(
                f"nice one {first_name}. we put you both in the group queue. "
                "you'll hear from us within a week once we line up 4 to 6 people "
                "with a similar vibe."
            ),
            session_id=session.id,
        )
    await _update_session(
        session.id,
        {
            "group_queue_entry_ids": state["group_queue_entry_ids"],
            "state": "resolved",
            "resolved_at": datetime.utcnow(),
        },
    )
    return state


# ---------- Both Pass branch ----------


async def node_both_pass_noop(state: GraphState) -> GraphState:
    session = await _load_session(state["session_id"])
    for p in session.participants:
        user = await _load_user(p.user_id)
        first_name = user.name.split()[0].lower()
        await send_message(
            user_id=user.id,
            body=(
                f"thanks for letting us know {first_name}. "
                "we'll find you someone better suited next wednesday."
            ),
            session_id=session.id,
        )
    await _update_session(
        session.id, {"state": "resolved", "resolved_at": datetime.utcnow()}
    )
    return state


# ---------- Asymmetric branch ----------


async def node_asymmetric_closure(state: GraphState) -> GraphState:
    session = await _load_session(state["session_id"])
    outcome: AftersOutcome = state["outcome"]  # type: ignore
    a, b = session.participants[0], session.participants[1]

    # Identify the more-interested party (recipient) and the less-interested
    # party (other). The "interested" side is defined per outcome on the ladder
    # again > group > pass. The previous implementation hard-coded recipient to
    # whoever picked "again", which routed the closure message to the wrong
    # person in the Group-vs-Pass branch (neither side picked again, so the
    # Pass user was landing in the recipient slot).
    if outcome in ("asymmetric_again_pass", "asymmetric_again_group"):
        if a.choice == "again":
            recipient, other = a, b
        else:
            recipient, other = b, a
    elif outcome == "asymmetric_group_pass":
        if a.choice == "group":
            recipient, other = a, b
        else:
            recipient, other = b, a
    else:
        raise RuntimeError(
            f"asymmetric_closure called with non-asymmetric outcome: {outcome}"
        )

    recipient_user = await _load_user(recipient.user_id)

    draft = await run_closure_agent(
        session_id=session.id,
        recipient_name=recipient_user.name,
        recipient_choice=recipient.choice or "again",
        other_choice=other.choice or "pass",
        outcome=outcome,
        recipient_debrief=_debrief_from_participant(recipient),
        other_debrief=_debrief_from_participant(other),
        scenario_mock_tag=state.get("scenario_mock_tag"),
    )

    review = ClosureReview(
        session_id=session.id,
        recipient_user_id=recipient_user.id,
        recipient_name=recipient_user.name,
        draft_message=draft.message,
    )
    await get_db()[collections.closure_reviews].insert_one(
        review.model_dump(by_alias=True)
    )
    state["closure_review_id"] = review.id
    state["closure_draft"] = draft.message

    await _update_session(
        session.id,
        {
            "closure_review_id": review.id,
            "state": "resolving",
            "resolved_at": datetime.utcnow(),
        },
    )
    await publish_event(
        "closure_review.created",
        {"session_id": session.id, "review_id": review.id},
    )
    return state


# ---------- Timeout branch ----------


async def node_timeout_handler(state: GraphState) -> GraphState:
    session = await _load_session(state["session_id"])
    # Find whoever did respond; send them a gentle close.
    responder = next(
        (p for p in session.participants if p.response_state == "submitted"), None
    )
    if responder is not None:
        user = await _load_user(responder.user_id)
        first_name = user.name.split()[0].lower()
        await send_message(
            user_id=user.id,
            body=(
                f"hey {first_name}. the other person didn't get back to us this week. "
                "we called it here so you aren't left hanging. next wednesday we'll "
                "line up someone who follows up faster."
            ),
            session_id=session.id,
        )
    await _update_session(
        session.id,
        {"state": "closed", "resolved_at": datetime.utcnow()},
    )
    return state


# ---------- Scoring ----------


async def node_scoring(state: GraphState) -> GraphState:
    # Scoring intentionally does not touch session.state; the upstream branch node
    # is the source of truth for that (both_again_confirm and friends set resolved,
    # timeout_handler sets closed, asymmetric_closure leaves it at resolving until
    # the human reviewer acts).
    session = await _load_session(state["session_id"])
    match = await _load_match(session.match_id)
    first_venue = await _load_first_date_venue(session.date_id)
    result = await run_scoring_agent(
        session=session, match=match, venue_tags=first_venue.tags
    )
    state["score_pre"] = result["pre"]
    state["score_post"] = result["post"]
    return state


# ---------- graph builder ----------


def build_graph():
    g = StateGraph(GraphState)

    g.add_node("route", node_route)
    g.add_node("both_again_venue", node_both_again_venue)
    g.add_node("both_again_schedule", node_both_again_schedule)
    g.add_node("both_again_confirm", node_both_again_confirm)
    g.add_node("both_group_batch", node_both_group_batch)
    g.add_node("both_group_confirm", node_both_group_confirm)
    g.add_node("both_pass_noop", node_both_pass_noop)
    g.add_node("asymmetric_closure", node_asymmetric_closure)
    g.add_node("timeout_handler", node_timeout_handler)
    g.add_node("scoring", node_scoring)

    g.set_entry_point("route")
    g.add_conditional_edges(
        "route",
        _route_outcome,
        {
            "both_again_venue": "both_again_venue",
            "both_group_batch": "both_group_batch",
            "both_pass_noop": "both_pass_noop",
            "asymmetric_closure": "asymmetric_closure",
            "timeout_handler": "timeout_handler",
        },
    )
    g.add_edge("both_again_venue", "both_again_schedule")
    g.add_edge("both_again_schedule", "both_again_confirm")
    g.add_edge("both_again_confirm", "scoring")
    g.add_edge("both_group_batch", "both_group_confirm")
    g.add_edge("both_group_confirm", "scoring")
    g.add_edge("both_pass_noop", "scoring")
    g.add_edge("asymmetric_closure", "scoring")
    g.add_edge("timeout_handler", "scoring")
    g.add_edge("scoring", END)

    return g.compile()


_compiled = None


def get_compiled():
    global _compiled
    if _compiled is None:
        _compiled = build_graph()
    return _compiled


async def run_resolution(
    session_id: str,
    outcome: AftersOutcome,
    scenario_mock_tag: str | None = None,
) -> GraphState:
    state: GraphState = {
        "session_id": session_id,
        "outcome": outcome,
    }
    if scenario_mock_tag:
        state["scenario_mock_tag"] = scenario_mock_tag  # type: ignore
    compiled = get_compiled()
    return await compiled.ainvoke(state)
