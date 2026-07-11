"""Dependencias comunes de FastAPI."""
from fastapi import Header, HTTPException


def get_grupo_id(x_grupo_id: str = Header(alias="X-Grupo-Id")) -> str:
    """Grupo/sala activa del cliente. No se valida contra el Sheet en cada
    request (evita llamadas extra a la API de Sheets) — solo aísla los datos
    para la experiencia de uso, no es un mecanismo de seguridad con auth real.
    """
    if not x_grupo_id.strip():
        raise HTTPException(400, "Falta el header X-Grupo-Id")
    return x_grupo_id.strip()
