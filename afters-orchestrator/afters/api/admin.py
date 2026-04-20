"""Admin endpoints. Non-scenario operations that sit outside the scripted flow.

POST /admin/reset            wipe runtime collections and re-run the seed.
POST /admin/backfill-messages run the Backfill Agent (sonnet) across every
                              resolved/closed session that has no chat
                              messages, generating believable iMessage
                              threads for each one.
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException

from afters.services import backfill_all_missing, reset_demo_data

router = APIRouter(prefix="/admin", tags=["admin"])


@router.post("/reset")
async def reset():
    """Drop runtime collections (sessions, traces, messages, closure reviews,
    second dates, group queue) and re-run the seed to restore 20 users,
    46 venues, 30 historical sessions, and 30 feedback_training.jsonl rows.

    After seed finishes, also run the Backfill Agent so every historical
    session has a Claude-generated iMessage thread. Returns the seed summary
    with a backfill sub-summary merged in.
    """
    try:
        summary = await reset_demo_data()
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(500, f"reset failed: {exc}")
    try:
        backfill_summary = await backfill_all_missing(concurrency=5, force=True)
        summary["backfill"] = backfill_summary
    except Exception as exc:  # noqa: BLE001 - backfill is best-effort
        summary["backfill_error"] = str(exc)
    return summary


@router.post("/backfill-messages")
async def backfill(force: bool = False, concurrency: int = 5):
    """Generate chat threads via Claude for sessions that have none.

    Query params:
      force       if true, blow away existing messages for every
                  resolved/closed session and regenerate. Default false
                  (only fills sessions where count == 0).
      concurrency cap on simultaneous Claude calls. Default 5.
    """
    try:
        return await backfill_all_missing(concurrency=concurrency, force=force)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(500, f"backfill failed: {exc}")
