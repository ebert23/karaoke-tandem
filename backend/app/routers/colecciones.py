"""Endpoints de Colecciones temáticas: listado, canciones y carga del pack."""
from fastapi import APIRouter, Depends, HTTPException

from ..deps import get_grupo_id
from ..schemas import CancionOut, CargaColeccionOut, ColeccionOut, ColeccionCargarRequest
from ..services import colecciones as svc

router = APIRouter(prefix="/api/colecciones", tags=["colecciones"])


@router.get("", response_model=list[ColeccionOut])
def listar(id_grupo: str = Depends(get_grupo_id)):
    """Solo las que tienen canciones suficientes en este catálogo.

    Filtrar acá y no en el front es a propósito: la regla de "cuántas hacen
    falta para que valga la pena mostrarla" es una sola y vive con el resto de
    la lógica de colecciones.
    """
    return svc.listar(id_grupo)


@router.get("/catalogo", response_model=list[ColeccionOut])
def catalogo(id_grupo: str = Depends(get_grupo_id)):
    """Todas, incluso las vacías, con cuántas se pueden cargar del pack. Es la
    vista del dueño: le interesa justo la que todavía no tiene."""
    return svc.catalogo(id_grupo)


@router.get("/{id_coleccion}/canciones", response_model=list[CancionOut])
def canciones(id_coleccion: str, id_usuario: str | None = None, id_grupo: str = Depends(get_grupo_id)):
    try:
        return svc.canciones_de(id_grupo, id_coleccion, id_usuario=id_usuario)
    except ValueError as e:
        raise HTTPException(404, str(e))


@router.post("/{id_coleccion}/cargar", response_model=CargaColeccionOut)
def cargar(id_coleccion: str, data: ColeccionCargarRequest, id_grupo: str = Depends(get_grupo_id)):
    """Suma al catálogo las curadas que falten. Solo admins.

    Igual que la importación de CSV: con confirmar=false devuelve el resumen
    sin escribir nada.
    """
    try:
        svc.requiere_admin(id_grupo, data.id_usuario_actor)
        return svc.cargar_pack(id_grupo, id_coleccion, confirmar=data.confirmar)
    except PermissionError as e:
        raise HTTPException(403, str(e))
    except ValueError as e:
        raise HTTPException(404, str(e))
