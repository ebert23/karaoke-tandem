"""Endpoints de Usuarios."""
from fastapi import APIRouter, Depends, HTTPException

from ..deps import get_grupo_id
from ..schemas import UsuarioCreate, UsuarioOut
from ..services import usuarios as svc

router = APIRouter(prefix="/api/usuarios", tags=["usuarios"])


@router.get("", response_model=list[UsuarioOut])
def listar(id_grupo: str = Depends(get_grupo_id)):
    return svc.listar(id_grupo)


@router.get("/{id_usuario}", response_model=UsuarioOut)
def obtener(id_usuario: str, id_grupo: str = Depends(get_grupo_id)):
    u = svc.get_por_id(id_grupo, id_usuario)
    if not u:
        raise HTTPException(404, "Usuario no encontrado")
    return u


@router.post("", response_model=UsuarioOut)
def crear_o_obtener(data: UsuarioCreate, id_grupo: str = Depends(get_grupo_id)):
    """Login simple por nombre: si no existe lo crea (sin contraseñas)."""
    return svc.get_or_create(id_grupo, data.nombre, data.foto)
