from __future__ import annotations

from fastapi import APIRouter, BackgroundTasks, HTTPException

from afters.models import ScenarioName
from afters.services import SCENARIOS, run_scenario

router = APIRouter(prefix="/scenarios", tags=["scenarios"])


@router.get("/")
async def list_scenarios():
    return [
        {
            "name": n,
            "label": data["label"],
            "pair": list(data["pair_names"]),
            "campus": data["campus"],
        }
        for n, data in SCENARIOS.items()
    ]


@router.post("/{name}")
async def trigger_scenario(name: ScenarioName, background: BackgroundTasks):
    if name not in SCENARIOS:
        raise HTTPException(404, f"unknown scenario {name}")
    # Run inline so the dashboard's confirmation response includes the session id.
    result = await run_scenario(name)
    return result
