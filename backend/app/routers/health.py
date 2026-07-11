"""Health check para Render y para monitoreo básico."""
from datetime import datetime, timezone

from fastapi import APIRouter

from ..config import settings

router = APIRouter(tags=["salud"])
_START_TIME = datetime.now(timezone.utc)


@router.get("/health")
async def health():
    return {
        "status": "ok",
        "env": settings.app_env,
        "uptime_seconds": round((datetime.now(timezone.utc) - _START_TIME).total_seconds(), 1),
    }
