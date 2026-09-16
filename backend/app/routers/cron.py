"""Tareas programadas ejecutadas por Vercel Cron."""
import secrets

from fastapi import APIRouter, Header, HTTPException

from .. import db
from ..config import settings

router = APIRouter(prefix="/api/cron", tags=["cron"])


@router.get("/db-keepalive")
def mantener_bd_activa(authorization: str = Header(default="")):
    """Comprueba a diario que Supabase acepte conexiones y consultas."""
    secreto = settings.cron_secret.strip()
    esperado = f"Bearer {secreto}"
    if not secreto or not secrets.compare_digest(authorization, esperado):
        raise HTTPException(status_code=401, detail="No autorizado")

    resultado = db.fetch_one("SELECT 1 AS ok")
    if not resultado or resultado.get("ok") != 1:
        raise HTTPException(status_code=503, detail="Base de datos no disponible")

    return {"status": "ok", "database": "reachable"}
