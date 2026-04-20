"""Agent trace writer. Every LLM call, every deterministic agent, and every human
action (approve/edit/reject in the closure queue) produces one row here. This is
the backbone of the internal tools Traces view and the per-session expandables."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from afters.db.mongo import collections, get_db, jsonable
from afters.db.redis_client import publish_event
from afters.models import AgentTrace, AgentKind


async def write_trace(
    *,
    session_id: str | None,
    agent_name: str,
    kind: AgentKind,
    summary: str,
    input_summary: str,
    output: Any = None,
    prompt: str | None = None,
    model: str | None = None,
    tokens_in: int = 0,
    tokens_out: int = 0,
    cost_usd: float = 0.0,
    latency_ms: int = 0,
    tags: list[str] | None = None,
) -> AgentTrace:
    trace = AgentTrace(
        session_id=session_id,
        agent_name=agent_name,
        kind=kind,
        model=model,
        input_summary=input_summary,
        prompt=prompt,
        output=jsonable(output),
        tokens_in=tokens_in,
        tokens_out=tokens_out,
        cost_usd=cost_usd,
        latency_ms=latency_ms,
        summary=summary,
        tags=tags or [],
        created_at=datetime.utcnow(),
    )
    db = get_db()
    await db[collections.traces].insert_one(trace.model_dump(by_alias=True))
    await publish_event(
        "trace.created",
        {
            "trace_id": trace.id,
            "session_id": session_id,
            "agent_name": agent_name,
            "kind": kind,
            "summary": summary,
        },
    )
    return trace


async def write_human_feedback_trace(
    *,
    session_id: str,
    action: str,
    summary: str,
    details: dict[str, Any] | None = None,
) -> AgentTrace:
    """Log a human-in-the-loop action (approve / edit / reject / regenerate)
    as a first-class trace row so the Traces view interleaves human events with LLM events."""
    return await write_trace(
        session_id=session_id,
        agent_name="Human Reviewer",
        kind="human_feedback",
        summary=summary,
        input_summary=action,
        output=details,
        tags=["human_feedback", action],
    )
