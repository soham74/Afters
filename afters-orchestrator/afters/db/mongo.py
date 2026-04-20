"""Mongo access. We keep ids as hex strings everywhere (no ObjectId wrapping)
so the dashboard and messaging service can round-trip JSON without custom codecs."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
from pydantic import BaseModel

from afters.config import get_settings

_client: AsyncIOMotorClient | None = None


def get_client() -> AsyncIOMotorClient:
    global _client
    if _client is None:
        _client = AsyncIOMotorClient(get_settings().mongodb_uri, tz_aware=False)
    return _client


def get_db() -> AsyncIOMotorDatabase:
    return get_client()[get_settings().mongo_db_name]


class Collections:
    users = "users"
    matches = "matches"
    dates = "dates"
    venues = "venues"
    sessions = "afters_sessions"
    traces = "agent_traces"
    messages = "messages"
    second_dates = "second_dates"
    group_queue = "group_queue"
    closure_reviews = "closure_reviews"


collections = Collections()


def serialize(model: BaseModel) -> dict[str, Any]:
    """Pydantic model -> dict ready for Mongo insert.
    Converts nested datetimes to ISO strings? No. Mongo handles datetimes natively.
    Uses alias so `id` becomes `_id`."""
    return model.model_dump(by_alias=True)


def deserialize(cls: type[BaseModel], raw: dict[str, Any] | None):
    if raw is None:
        return None
    return cls.model_validate(raw)


def jsonable(obj: Any) -> Any:
    """Coerce Mongo/Pydantic objects into JSON-serializable primitives for API responses."""
    if isinstance(obj, datetime):
        return obj.isoformat()
    if isinstance(obj, BaseModel):
        return jsonable(obj.model_dump(by_alias=True))
    if isinstance(obj, dict):
        return {k: jsonable(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [jsonable(v) for v in obj]
    return obj


async def ensure_indexes() -> None:
    db = get_db()
    await db[Collections.sessions].create_index("date_id", unique=True)
    await db[Collections.sessions].create_index("state")
    await db[Collections.sessions].create_index("campus")
    await db[Collections.sessions].create_index("created_at")
    await db[Collections.traces].create_index("session_id")
    await db[Collections.traces].create_index("created_at")
    await db[Collections.messages].create_index([("user_id", 1), ("created_at", -1)])
    await db[Collections.group_queue].create_index([("campus", 1), ("status", 1)])
    await db[Collections.closure_reviews].create_index("session_id")
