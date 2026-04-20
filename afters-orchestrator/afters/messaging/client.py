"""HTTP client into the NestJS messaging service.

The orchestrator never writes to the messages collection directly. It always
goes through NestJS so the split between orchestration (Python) and delivery
(TypeScript) is demo-legible: one is reasoning, the other is iMessage simulation."""

from __future__ import annotations

from typing import Any

import httpx

from afters.config import get_settings


class MessagingClient:
    def __init__(self) -> None:
        self._base = get_settings().messaging_base_url
        self._client = httpx.AsyncClient(base_url=self._base, timeout=10.0)

    async def send(
        self,
        *,
        user_id: str,
        body: str,
        kind: str = "text",
        session_id: str | None = None,
        card_meta: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        payload = {
            "user_id": user_id,
            "body": body,
            "kind": kind,
            "session_id": session_id,
            "card_meta": card_meta,
        }
        resp = await self._client.post("/messages/send", json=payload)
        resp.raise_for_status()
        return resp.json()

    async def close(self) -> None:
        await self._client.aclose()


_client: MessagingClient | None = None


def _get() -> MessagingClient:
    global _client
    if _client is None:
        _client = MessagingClient()
    return _client


async def send_message(
    *,
    user_id: str,
    body: str,
    kind: str = "text",
    session_id: str | None = None,
    card_meta: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return await _get().send(
        user_id=user_id,
        body=body,
        kind=kind,
        session_id=session_id,
        card_meta=card_meta,
    )
