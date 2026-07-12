"""Endpoints de Grupos/Salas: crear, unirse por código, detalle + miembros."""
from fastapi import APIRouter, HTTPException

from ..schemas import (
    GrupoCreate,
    GrupoDetalleOut,
    GrupoOut,
    GrupoUnirseRequest,
    MiembroAccionRequest,
    ReclamarAdminRequest,
)
from ..services import grupos as svc
from ..services import sesiones as sesiones_svc
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


@router.post("/{id_grupo}/reclamar-admin", response_model=GrupoDetalleOut)
def reclamar_admin(id_grupo: str, data: ReclamarAdminRequest):
    try:
        return svc.reclamar_admin(id_grupo, data.id_usuario)
    except PermissionError as e:
        raise HTTPException(403, str(e))
    except ValueError as e:
        raise HTTPException(404, str(e))


@router.post("/{id_grupo}/miembros/{id_usuario}/admin", response_model=GrupoDetalleOut)
def hacer_admin(id_grupo: str, id_usuario: str, data: MiembroAccionRequest):
    try:
        return svc.hacer_admin(id_grupo, data.id_usuario_actor, id_usuario)
    except PermissionError as e:
        raise HTTPException(403, str(e))
    except ValueError as e:
        raise HTTPException(404, str(e))


@router.delete("/{id_grupo}/miembros/{id_usuario}/admin", response_model=GrupoDetalleOut)
def quitar_admin(id_grupo: str, id_usuario: str, data: MiembroAccionRequest):
    try:
        return svc.quitar_admin(id_grupo, data.id_usuario_actor, id_usuario)
    except PermissionError as e:
        raise HTTPException(403, str(e))
    except ValueError as e:
        raise HTTPException(400, str(e))


@router.delete("/{id_grupo}/miembros/{id_usuario}", response_model=GrupoDetalleOut)
def expulsar(id_grupo: str, id_usuario: str, data: MiembroAccionRequest):
    objetivo = usuarios_svc.get_por_id(id_grupo, id_usuario)
    try:
        resultado = svc.expulsar_miembro(id_grupo, data.id_usuario_actor, id_usuario)
    except PermissionError as e:
        raise HTTPException(403, str(e))
    except ValueError as e:
        raise HTTPException(400, str(e))
    # Si estaba participando en la sesión de karaoke activa, lo sacamos de
    # ahí también — expulsarlo del grupo pero seguir viéndolo cantando en
    # vivo sería confuso.
    if objetivo:
        sesion_activa = sesiones_svc.get_activa(id_grupo)
        if sesion_activa:
            sesiones_svc.quitar_participante(id_grupo, sesion_activa["id_sesion"], objetivo["nombre"])
    return resultado
