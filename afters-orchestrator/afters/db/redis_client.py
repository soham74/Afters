"""Redis wrapper.

Two uses in this project:
1. `afters:events` Redis Stream: the dashboard tails state transitions.
2. `afters:chat:{user_id}` pub/sub: live chat delivery to the dashboard's iMessage view.
"""

from __future__ import annotations

import json
from typing import Any

from redis.asyncio import Redis

from afters.config import get_settings

_redis: Redis | None = None

EVENTS_STREAM = "afters:events"


async def get_redis() -> Redis:
    global _redis
    if _redis is None:
        _redis = Redis.from_url(get_settings().redis_url, decode_responses=True)
    return _redis


async def publish_event(kind: str, payload: dict[str, Any]) -> None:
    r = await get_redis()
    # Redis Streams only store flat string fields, so we JSON-encode the payload.
    await r.xadd(
        EVENTS_STREAM,
        {"kind": kind, "payload": json.dumps(payload, default=str)},
        maxlen=5000,
        approximate=True,
    )


async def publish_chat(user_id: str, message: dict[str, Any]) -> None:
    r = await get_redis()
    await r.publish(f"afters:chat:{user_id}", json.dumps(message, default=str))
