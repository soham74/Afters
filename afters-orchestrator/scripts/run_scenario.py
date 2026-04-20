"""CLI trigger for a scenario. Convenience for development and testing.
Usage:  python -m scripts.run_scenario both_again
"""

from __future__ import annotations

import asyncio
import json
import sys

from afters.services import SCENARIOS, run_scenario


async def _main(name: str):
    if name not in SCENARIOS:
        print(f"unknown scenario '{name}'. known: {list(SCENARIOS)}")
        raise SystemExit(2)
    result = await run_scenario(name)  # type: ignore[arg-type]
    print(json.dumps(result, indent=2, default=str))


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("usage: python -m scripts.run_scenario <scenario_name>")
        raise SystemExit(1)
    asyncio.run(_main(sys.argv[1]))
