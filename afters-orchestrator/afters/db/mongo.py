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
    """Create indexes. Non-fatal if they fail (e.g. disk pressure on hosted Mongo)."""
    db = get_db()
    indexes = [
        (Collections.sessions, "date_id", {"unique": True}),
        (Collections.sessions, "state", {}),
        (Collections.sessions, "campus", {}),
        (Collections.sessions, "created_at", {}),
        (Collections.traces, "session_id", {}),
        (Collections.traces, "created_at", {}),
        (Collections.messages, [("user_id", 1), ("created_at", -1)], {}),
        (Collections.group_queue, [("campus", 1), ("status", 1)], {}),
        (Collections.closure_reviews, "session_id", {}),
    ]
    for collection, keys, opts in indexes:
        try:
            await db[collection].create_index(keys, **opts)
        except Exception as e:
            # index creation is best-effort. app stays up even if Mongo is disk-constrained.
            print(f"[ensure_indexes] skipping index on {collection}: {e}")
