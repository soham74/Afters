"""Scheduler.

Deterministic. Produces 3 proposed time slots for the coming week based on a
mock availability intersection. Writes its own agent_trace (kind=deterministic)
so the Traces view reflects every agent invocation, LLM or not."""

from __future__ import annotations

from datetime import datetime, timedelta, time

from afters.llm.tracing import write_trace

# Mock "available hours" per user. In real Ditto this would read from the
# calendar-intersection service. For the demo, every user has the same soft window.
DEFAULT_HOURS = [18, 19, 20]  # 6pm, 7pm, 8pm
DEFAULT_WEEKDAYS = [1, 2, 3, 4, 6]  # Tue, Wed, Thu, Fri, Sun


async def propose_time_slots(
    *,
    session_id: str,
    pair_label: str,
    start_from: datetime | None = None,
    count: int = 3,
) -> list[str]:
    """Returns a list of ISO-formatted candidate datetimes."""
    start = (start_from or datetime.utcnow()) + timedelta(days=1)
    slots: list[str] = []
    d = start.date()
    hour_cursor = 0
    while len(slots) < count:
        if d.isoweekday() in DEFAULT_WEEKDAYS:
            slot_dt = datetime.combine(d, time(hour=DEFAULT_HOURS[hour_cursor % len(DEFAULT_HOURS)]))
            slots.append(slot_dt.isoformat())
            hour_cursor += 1
        d = d + timedelta(days=1)
        if d > start.date() + timedelta(days=14):
            break

    await write_trace(
        session_id=session_id,
        agent_name="Scheduler",
        kind="deterministic",
        input_summary=f"{pair_label}; {len(slots)} slots requested",
        output={"slots": slots},
        summary=(
            f"Scheduler proposed {len(slots)} time slots for {pair_label} "
            f"between {slots[0][:10]} and {slots[-1][:10]} based on mock availability overlap."
        ),
        tags=["scheduler"],
    )
    return slots
