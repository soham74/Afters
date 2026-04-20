"""Metrics view API.

Computes resolved-rate within 24h, second-date conversion, group acceptance,
ghost rate, model signal density, and a daily resolved-rate time series.
All derived from afters_sessions + feedback_training.jsonl + second_dates.
"""

from __future__ import annotations

from datetime import datetime, timedelta
from pathlib import Path

from fastapi import APIRouter

from afters.db.mongo import collections, get_db

router = APIRouter(prefix="/metrics", tags=["metrics"])

FEEDBACK_FILE = Path(__file__).resolve().parents[2] / "feedback_training.jsonl"


@router.get("")
async def overview():
    db = get_db()
    sessions = [s async for s in db[collections.sessions].find({})]
    total = len(sessions)
    resolved = [s for s in sessions if s.get("resolved_at")]
    timed_out = [s for s in sessions if s.get("resolved_outcome") == "timed_out"]
    both_again = [s for s in sessions if s.get("resolved_outcome") == "both_again"]
    both_group = [s for s in sessions if s.get("resolved_outcome") == "both_group"]

    # resolved within 24h
    within_24h = 0
    for s in resolved:
        if s.get("resolved_at") and s.get("created_at"):
            delta = s["resolved_at"] - s["created_at"]
            if delta <= timedelta(hours=24):
                within_24h += 1

    # ghost rate: timed out / total
    ghost_rate = (len(timed_out) / total) if total else 0.0
    resolved_rate_24h = (within_24h / total) if total else 0.0
    second_date_conversion = (len(both_again) / total) if total else 0.0
    group_acceptance = (len(both_group) / total) if total else 0.0

    # Per-outcome counts so the percentages can be audited on-screen.
    outcome_counts: dict[str, int] = {}
    for s in sessions:
        outcome = s.get("resolved_outcome") or "unresolved"
        outcome_counts[outcome] = outcome_counts.get(outcome, 0) + 1

    feedback_rows = 0
    if FEEDBACK_FILE.exists():
        with FEEDBACK_FILE.open() as fh:
            feedback_rows = sum(1 for line in fh if line.strip())

    # Daily time series over the last 14 days of resolved rate within 24h.
    today = datetime.utcnow().date()
    timeseries = []
    for days_ago in range(13, -1, -1):
        day = today - timedelta(days=days_ago)
        day_start = datetime.combine(day, datetime.min.time())
        day_end = day_start + timedelta(days=1)
        day_sessions = [
            s
            for s in sessions
            if s.get("created_at")
            and day_start <= s["created_at"] < day_end
        ]
        day_resolved = sum(
            1
            for s in day_sessions
            if s.get("resolved_at")
            and (s["resolved_at"] - s["created_at"]) <= timedelta(hours=24)
        )
        rate = (day_resolved / len(day_sessions)) if day_sessions else None
        timeseries.append(
            {
                "date": day.isoformat(),
                "total": len(day_sessions),
                "resolved_24h": day_resolved,
                "rate": rate,
            }
        )

    return {
        "total_sessions": total,
        "resolved_rate_24h": round(resolved_rate_24h, 3),
        "resolved_24h_count": within_24h,
        "second_date_conversion": round(second_date_conversion, 3),
        "second_date_count": len(both_again),
        "group_acceptance": round(group_acceptance, 3),
        "group_count": len(both_group),
        "ghost_rate": round(ghost_rate, 3),
        "ghost_count": len(timed_out),
        "outcome_counts": outcome_counts,
        "model_signal_rows": feedback_rows,
        "timeseries": timeseries,
    }
