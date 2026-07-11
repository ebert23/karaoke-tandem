"""Endpoints de Grupos/Salas: crear, unirse por código, detalle + miembros."""
from fastapi import APIRouter, HTTPException

from ..schemas import GrupoCreate, GrupoDetalleOut, GrupoOut, GrupoUnirseRequest
from ..services import grupos as svc
from ..services import usuarios as usuarios_svc

router = APIRouter(prefix="/api/grupos", tags=["grupos"])


@router.post("", response_model=GrupoOut)
def crear(data: GrupoCreate):
    return svc.crear(data.nombre, data.foto, data.creado_por_nombre)


@router.post("/unirse", response_model=GrupoOut)
def unirse(data: GrupoUnirseRequest):
    grupo = svc.unirse_por_codigo(data.codigo)
    if not grupo:
        raise HTTPException(404, "Código de grupo no encontrado")
    return grupo


@router.get("/{id_grupo}", response_model=GrupoDetalleOut)
def obtener(id_grupo: str):
    grupo = svc.get_por_id(id_grupo)
    if not grupo:
        raise HTTPException(404, "Grupo no encontrado")
    grupo["miembros"] = usuarios_svc.listar(id_grupo)
    return grupo
