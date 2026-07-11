"""Cliente mínimo de YouTube Data API v3 (solo búsqueda de video)."""
import httpx

from .config import settings

SEARCH_URL = "https://www.googleapis.com/youtube/v3/search"


def disponible() -> bool:
    return bool(settings.youtube_api_key)


def buscar(q: str, max_resultados: int = 8) -> list[dict]:
    if not settings.youtube_api_key:
        raise RuntimeError("YOUTUBE_API_KEY no configurada")

    resp = httpx.get(
        SEARCH_URL,
        params={
            "part": "snippet",
            "q": q,
            "type": "video",
            "videoCategoryId": "10",  # Música
            "maxResults": max_resultados,
            "key": settings.youtube_api_key,
        },
        timeout=8.0,
    )
    resp.raise_for_status()
    data = resp.json()

    resultados = []
    for item in data.get("items", []):
        video_id = item.get("id", {}).get("videoId")
        snippet = item.get("snippet", {})
        if not video_id:
            continue
        resultados.append({
            "titulo": snippet.get("title", ""),
            "canal": snippet.get("channelTitle", ""),
            "link_youtube": f"https://youtu.be/{video_id}",
            "miniatura": snippet.get("thumbnails", {}).get("default", {}).get("url", ""),
        })
    return resultados
