"""Endpoints de Retos."""
from fastapi import APIRouter, Depends, HTTPException

from ..deps import get_grupo_id
from ..schemas import MiembroAccionRequest, RetoCreate, RetoOut
from ..services import retos as svc

router = APIRouter(prefix="/api/retos", tags=["retos"])


@router.get("", response_model=list[RetoOut])
def listar(categoria: str | None = None, id_grupo: str = Depends(get_grupo_id)):
    return svc.listar(id_grupo, categoria)


@router.get("/aleatorio", response_model=RetoOut)
def aleatorio(categoria: str | None = None, excluir: str = "", id_grupo: str = Depends(get_grupo_id)):
    """Un reto al azar. `excluir` es el id del que ya se está mostrando, para
    que "Otro reto" no devuelva el mismo en una categoría con pocos."""
    try:
        return svc.aleatorio(id_grupo, categoria, excluir=excluir)
    except ValueError as e:
        raise HTTPException(404, str(e))


@router.post("", response_model=RetoOut)
def crear(data: RetoCreate, id_grupo: str = Depends(get_grupo_id)):
    try:
        return svc.crear(id_grupo, data.texto, data.dificultad, data.categoria)
    except svc.RetoDuplicado as e:
        raise HTTPException(400, str(e))


@router.post("/restaurar", response_model=list[RetoOut])
def restaurar(data: MiembroAccionRequest, id_grupo: str = Depends(get_grupo_id)):
    """Trae los retos por defecto que le falten al grupo y devuelve la baraja."""
    try:
        svc.restaurar_defaults(id_grupo, data.id_usuario_actor)
    except PermissionError as e:
        raise HTTPException(403, str(e))
    except ValueError as e:
        raise HTTPException(404, str(e))
    return svc.listar(id_grupo)


@router.delete("/{id_reto}", status_code=204)
def eliminar(id_reto: str, data: MiembroAccionRequest, id_grupo: str = Depends(get_grupo_id)):
    try:
        svc.eliminar(id_grupo, id_reto, data.id_usuario_actor)
    except PermissionError as e:
        raise HTTPException(403, str(e))
    except ValueError as e:
        raise HTTPException(404, str(e))
