"""Punto de entrada de la API de KaraokeTandem.

Arranca FastAPI, prepara las hojas de Google Sheets (crea las que falten),
registra los routers y sirve el frontend ya compilado en producción.

Desarrollo:
    uvicorn app.main:app --reload --port 8000
"""
import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from .config import settings
from .routers import canciones, grupos, health, ranking, retos, sesiones, stats, usuarios, youtube

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("karaoketandem")


@asynccontextmanager
async def lifespan(app: FastAPI):
    yield


app = FastAPI(
    title="KaraokeTandem API",
    description="API de la app de karaoke con Postgres (Supabase) como base de datos.",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    logger.error("unhandled_exception path=%s error=%s", request.url.path, exc)
    return JSONResponse(status_code=500, content={"detail": "Error interno del servidor."})


app.include_router(health.router)
app.include_router(grupos.router)
app.include_router(canciones.router)
app.include_router(usuarios.router)
app.include_router(sesiones.router)
app.include_router(retos.router)
app.include_router(ranking.router)
app.include_router(stats.router)
app.include_router(youtube.router)


# En producción, FastAPI sirve el frontend ya compilado (mismo origen, sin CORS).
_DIST = Path(__file__).resolve().parents[2] / "frontend" / "dist"
if _DIST.is_dir():
    app.mount("/", StaticFiles(directory=str(_DIST), html=True), name="frontend")
    logger.info("serving_frontend dist=%s", _DIST)
else:

    @app.get("/")
    async def root():
        return {"service": "KaraokeTandem API", "version": app.version, "docs": "/docs"}
