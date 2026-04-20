"""Anthropic wrapper. Every call:
- writes one agent_trace (prompt, model, usage, cost, latency, human-readable summary)
- respects MOCK_LLM=true (returns canned output without hitting the API)
- uses tool-calling for structured output against a Pydantic schema
"""

from __future__ import annotations

import time
from typing import Any, TypeVar

from anthropic import AsyncAnthropic
from pydantic import BaseModel

from afters.config import get_settings
from afters.llm.mock import get_mock
from afters.llm.tracing import write_trace

T = TypeVar("T", bound=BaseModel)

# Rough per-million-token pricing. Matches afters-shared/src/constants.ts.
PRICING: dict[str, dict[str, float]] = {
    "claude-sonnet-4-5": {"input": 3.0, "output": 15.0},
    "claude-haiku-4-5": {"input": 1.0, "output": 5.0},
}


def estimate_cost(model: str, tokens_in: int, tokens_out: int) -> float:
    p = PRICING.get(model, {"input": 0.0, "output": 0.0})
    return (tokens_in / 1_000_000) * p["input"] + (tokens_out / 1_000_000) * p["output"]


class LLMClient:
    def __init__(self) -> None:
        self._settings = get_settings()
        self._anthropic: AsyncAnthropic | None = None

    @property
    def mock(self) -> bool:
        return self._settings.mock_llm

    @property
    def anthropic(self) -> AsyncAnthropic:
        if self._anthropic is None:
            self._anthropic = AsyncAnthropic(api_key=self._settings.anthropic_api_key)
        return self._anthropic

    async def structured(
        self,
        *,
        agent_name: str,
        session_id: str | None,
        model: str,
        system: str,
        user: str,
        schema_cls: type[T],
        tool_name: str,
        tool_description: str,
        max_tokens: int = 1024,
        temperature: float = 0.4,
        summary_builder,  # (parsed, latency_ms) -> str
        input_summary: str,
        mock_tag: str | None = None,
        tags: list[str] | None = None,
    ) -> T:
        """Run Anthropic tool-use with a forced tool choice and parse into schema_cls.
        summary_builder takes the parsed object and latency_ms and returns the
        human-readable single sentence for the trace row. That sentence is what
        gets quoted on camera, so agents pass a careful closure here."""

        start = time.perf_counter()

        if self.mock and mock_tag is not None:
            canned = get_mock(agent_name, mock_tag)
            if canned is None:
                raise RuntimeError(
                    f"MOCK_LLM=true but no registered mock for {agent_name}/{mock_tag}"
                )
            parsed = schema_cls.model_validate(canned)
            latency_ms = int((time.perf_counter() - start) * 1000)
            await write_trace(
                session_id=session_id,
                agent_name=agent_name,
                kind="llm",
                model=f"mock:{model}",
                input_summary=input_summary,
                prompt=f"[system]\n{system}\n\n[user]\n{user}",
                output=parsed.model_dump(),
                tokens_in=0,
                tokens_out=0,
                cost_usd=0.0,
                latency_ms=latency_ms,
                summary=summary_builder(parsed, latency_ms),
                tags=(tags or []) + ["mock"],
            )
            return parsed

        tool = {
            "name": tool_name,
            "description": tool_description,
            "input_schema": _sanitize_schema(schema_cls.model_json_schema()),
        }
        resp = await self.anthropic.messages.create(
            model=model,
            max_tokens=max_tokens,
            temperature=temperature,
            system=system,
            messages=[{"role": "user", "content": user}],
            tools=[tool],
            tool_choice={"type": "tool", "name": tool_name},
        )
        latency_ms = int((time.perf_counter() - start) * 1000)

        tool_input: dict[str, Any] | None = None
        for block in resp.content:
            if block.type == "tool_use" and block.name == tool_name:
                tool_input = block.input
                break
        if tool_input is None:
            raise RuntimeError(f"{agent_name}: model did not call tool {tool_name}")

        parsed = schema_cls.model_validate(tool_input)
        tokens_in = resp.usage.input_tokens
        tokens_out = resp.usage.output_tokens
        cost = estimate_cost(model, tokens_in, tokens_out)

        await write_trace(
            session_id=session_id,
            agent_name=agent_name,
            kind="llm",
            model=model,
            input_summary=input_summary,
            prompt=f"[system]\n{system}\n\n[user]\n{user}",
            output=parsed.model_dump(),
            tokens_in=tokens_in,
            tokens_out=tokens_out,
            cost_usd=cost,
            latency_ms=latency_ms,
            summary=summary_builder(parsed, latency_ms),
            tags=tags or [],
        )
        return parsed


def _sanitize_schema(schema: dict[str, Any]) -> dict[str, Any]:
    """Anthropic's tool input_schema accepts JSON Schema but is strict about a few
    Pydantic v2 artifacts. Strip `title` and `$defs` refs expansion isn't needed
    here because our structured outputs are flat or near-flat."""
    out = dict(schema)
    out.pop("title", None)
    if "properties" in out and isinstance(out["properties"], dict):
        for k, v in out["properties"].items():
            if isinstance(v, dict):
                v.pop("title", None)
    return out


_llm: LLMClient | None = None


def get_llm() -> LLMClient:
    global _llm
    if _llm is None:
        _llm = LLMClient()
    return _llm
