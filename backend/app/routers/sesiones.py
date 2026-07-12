"""Endpoints de Sesiones de karaoke (modo día del evento)."""
from fastapi import APIRouter, Depends, HTTPException

from ..deps import get_grupo_id
from ..schemas import (
    CancionSesionOut,
    ColaRequest,
    MarcarCantadaRequest,
    SesionCreate,
    SesionOut,
    SesionUnirseRequest,
    VotarTurnoRequest,
    VotosTurnoOut,
)
from ..services import sesiones as svc

router = APIRouter(prefix="/api/sesiones", tags=["sesiones"])


@router.get("", response_model=list[SesionOut])
def historial(id_grupo: str = Depends(get_grupo_id)):
    return svc.historial(id_grupo)


@router.get("/activa", response_model=SesionOut | None)
def activa(id_grupo: str = Depends(get_grupo_id)):
    return svc.get_activa(id_grupo)


@router.post("", response_model=SesionOut)
def crear(data: SesionCreate, id_grupo: str = Depends(get_grupo_id)):
    try:
        return svc.crear(id_grupo, data.participantes)
    except ValueError as e:
        raise HTTPException(400, str(e))


@router.get("/{id_sesion}", response_model=SesionOut)
def obtener(id_sesion: str, id_grupo: str = Depends(get_grupo_id)):
    s = svc.get_por_id(id_grupo, id_sesion)
    if not s:
        raise HTTPException(404, "Sesión no encontrada")
    return s


@router.get("/{id_sesion}/detalle", response_model=list[CancionSesionOut])
def detalle(id_sesion: str, id_grupo: str = Depends(get_grupo_id)):
    return svc.detalle(id_grupo, id_sesion)


@router.post("/{id_sesion}/unirse", response_model=SesionOut)
def unirse(id_sesion: str, data: SesionUnirseRequest, id_grupo: str = Depends(get_grupo_id)):
    try:
        return svc.unirse(id_grupo, id_sesion, data.nombre)
    except ValueError as e:
        raise HTTPException(400, str(e))


@router.post("/{id_sesion}/cola", response_model=CancionSesionOut)
def agregar_a_cola(id_sesion: str, data: ColaRequest, id_grupo: str = Depends(get_grupo_id)):
    try:
        return svc.agregar_a_cola(id_grupo, id_sesion, data.id_cancion, data.cantantes)
    except ValueError as e:
        raise HTTPException(400, str(e))


@router.post("/{id_sesion}/siguiente", response_model=CancionSesionOut)
def siguiente(id_sesion: str, id_grupo: str = Depends(get_grupo_id)):
    try:
        return svc.siguiente_cancion(id_grupo, id_sesion)
    except ValueError as e:
        raise HTTPException(400, str(e))


@router.post("/{id_sesion}/canciones/{id_cancion}/votar_turno", response_model=VotosTurnoOut)
def votar_turno(id_sesion: str, id_cancion: str, data: VotarTurnoRequest, id_grupo: str = Depends(get_grupo_id)):
    try:
        return svc.votar_turno(id_grupo, id_sesion, id_cancion, data.id_usuario, data.puntuacion)
    except ValueError as e:
        raise HTTPException(400, str(e))


@router.get("/{id_sesion}/canciones/{id_cancion}/votos_turno", response_model=VotosTurnoOut)
def votos_turno(id_sesion: str, id_cancion: str, id_grupo: str = Depends(get_grupo_id)):
    try:
        return svc.votos_turno(id_grupo, id_sesion, id_cancion)
    except ValueError as e:
        raise HTTPException(404, str(e))


@router.post("/{id_sesion}/canciones/{id_cancion}/cantada", response_model=CancionSesionOut)
def marcar_cantada(id_sesion: str, id_cancion: str, data: MarcarCantadaRequest, id_grupo: str = Depends(get_grupo_id)):
    try:
        return svc.marcar_cantada(id_grupo, id_sesion, id_cancion, data.puntuacion)
    except ValueError as e:
        raise HTTPException(400, str(e))


@router.post("/{id_sesion}/canciones/{id_cancion}/saltar", response_model=CancionSesionOut)
def saltar(id_sesion: str, id_cancion: str, id_grupo: str = Depends(get_grupo_id)):
    try:
        return svc.saltar(id_grupo, id_sesion, id_cancion)
    except ValueError as e:
        raise HTTPException(400, str(e))


@router.post("/{id_sesion}/finalizar", response_model=SesionOut)
def finalizar(id_sesion: str, id_grupo: str = Depends(get_grupo_id)):
    try:
        return svc.finalizar(id_grupo, id_sesion)
    except ValueError as e:
        raise HTTPException(400, str(e))
