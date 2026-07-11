"""Endpoints de Retos."""
from fastapi import APIRouter, Depends, HTTPException

from ..deps import get_grupo_id
from ..schemas import RetoCreate, RetoOut
from ..services import retos as svc

router = APIRouter(prefix="/api/retos", tags=["retos"])


@router.get("", response_model=list[RetoOut])
def listar(categoria: str | None = None, id_grupo: str = Depends(get_grupo_id)):
    return svc.listar(id_grupo, categoria)


@router.get("/aleatorio", response_model=RetoOut)
def aleatorio(categoria: str | None = None, id_grupo: str = Depends(get_grupo_id)):
    try:
        return svc.aleatorio(id_grupo, categoria)
    except ValueError as e:
        raise HTTPException(404, str(e))


@router.post("", response_model=RetoOut)
def crear(data: RetoCreate, id_grupo: str = Depends(get_grupo_id)):
    return svc.crear(id_grupo, data.texto, data.dificultad, data.categoria)
