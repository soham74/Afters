"""Admin endpoints. Non-scenario operations that sit outside the scripted flow.

POST /admin/reset: wipes runtime collections and re-runs the seed script so
                   the dashboard opens on a clean cohort with the seeded
                   outcome mix visible.
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException

from afters.services import reset_demo_data

router = APIRouter(prefix="/admin", tags=["admin"])


@router.post("/reset")
async def reset():
    """Drop runtime collections (sessions, traces, messages, closure reviews,
    second dates, group queue) and re-run the seed to restore 20 users,
    46 venues, 30 historical sessions, and 30 feedback_training.jsonl rows.

    Returns a JSON summary with the same shape as `pnpm seed`.
    """
    try:
        return await reset_demo_data()
    except Exception as exc:  # noqa: BLE001 - surface any seed failure to the caller
        raise HTTPException(500, f"reset failed: {exc}")
