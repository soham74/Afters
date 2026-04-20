from fastapi import APIRouter

from . import admin, closure, messages, metrics, scenarios, sessions, traces, users

router = APIRouter()
router.include_router(scenarios.router)
router.include_router(sessions.router)
router.include_router(traces.router)
router.include_router(messages.router)
router.include_router(closure.router)
router.include_router(metrics.router)
router.include_router(users.router)
router.include_router(admin.router)

__all__ = ["router"]
