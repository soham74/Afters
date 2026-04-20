"""FastAPI entry.

Starts:
- Mongo client with indexes applied
- Redis event stream
- Background timeout watcher

Routes under /api/* mirror the dashboard's needs directly (sessions, traces,
metrics, closure, messages, scenarios)."""

from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from afters.api import router as api_router
from afters.db.mongo import ensure_indexes
from afters.services.session_service import run_timeout_pass


_timeout_task: asyncio.Task | None = None


async def _timeout_loop():
    """Poll every 5 seconds for overdue sessions. Cheap, and matches the
    TIMEOUT_SECONDS_OVERRIDE=60s demo granularity comfortably."""
    while True:
        try:
            await run_timeout_pass()
        except Exception as exc:  # noqa: BLE001 - keep the loop alive
            print(f"[timeout_loop] error: {exc}")
        await asyncio.sleep(5)


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
    await ensure_indexes()
    global _timeout_task
    _timeout_task = asyncio.create_task(_timeout_loop())
    try:
        yield
    finally:
        if _timeout_task is not None:
            _timeout_task.cancel()


app = FastAPI(title="Afters Orchestrator", version="0.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router, prefix="/api")


@app.get("/healthz")
async def healthz() -> dict:
    return {"ok": True}
