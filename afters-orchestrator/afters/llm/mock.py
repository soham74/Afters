"""MOCK_LLM=true registry. Returns canned structured outputs keyed on (agent_name, scenario_tag).

Used so demo scenarios are deterministic, offline-runnable, and cost zero tokens.
Real Anthropic calls still route through the same trace writer, so the Traces view
looks the same in both modes (model field is just `mock` instead of claude-sonnet-4-5).
"""

from __future__ import annotations

from typing import Any

# (agent_name, tag) -> output dict
MOCK_REGISTRY: dict[tuple[str, str], dict[str, Any]] = {}


def register_mock(agent_name: str, tag: str, output: dict[str, Any]) -> None:
    MOCK_REGISTRY[(agent_name, tag)] = output


def get_mock(agent_name: str, tag: str) -> dict[str, Any] | None:
    return MOCK_REGISTRY.get((agent_name, tag))
