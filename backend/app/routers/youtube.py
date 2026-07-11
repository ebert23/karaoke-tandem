"""Endpoint de búsqueda de canciones en YouTube (requiere YOUTUBE_API_KEY)."""
from fastapi import APIRouter, HTTPException

from .. import youtube_client
from ..schemas import YoutubeResultadoOut

router = APIRouter(prefix="/api/youtube", tags=["youtube"])


@router.get("/buscar", response_model=list[YoutubeResultadoOut])
def buscar(q: str):
    if not youtube_client.disponible():
        raise HTTPException(501, "Búsqueda de YouTube no configurada (falta YOUTUBE_API_KEY)")
    if not q.strip():
        return []
    try:
        return youtube_client.buscar(q.strip())
    except Exception as e:
        raise HTTPException(502, f"No se pudo consultar YouTube: {e}")
