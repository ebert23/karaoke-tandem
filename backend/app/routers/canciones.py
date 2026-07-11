"""Endpoints de Canciones: listado, alta, votación, favoritos, top 10,
sugerencias, búsqueda en YouTube y export CSV."""
from fastapi import APIRouter, Depends, HTTPException, Response

from ..deps import get_grupo_id
from ..schemas import CancionCreate, CancionOut, FavoritoRequest, SugerenciaOut, VotoRequest
from ..services import canciones as svc

router = APIRouter(prefix="/api/canciones", tags=["canciones"])


@router.get("", response_model=list[CancionOut])
def listar(
    id_usuario: str | None = None,
    genero: str | None = None,
    q: str | None = None,
    favoritas: bool = False,
    id_grupo: str = Depends(get_grupo_id),
):
    return svc.listar(id_grupo, id_usuario=id_usuario, genero=genero, q=q, favoritas=favoritas)


@router.get("/top10", response_model=list[CancionOut])
def top10(id_usuario: str | None = None, id_grupo: str = Depends(get_grupo_id)):
    return svc.top10(id_grupo, id_usuario=id_usuario)


@router.get("/sugerencias", response_model=list[SugerenciaOut])
def sugerencias(genero: str | None = None):
    return svc.sugerencias(genero)


@router.get("/export.csv")
def exportar_csv(id_grupo: str = Depends(get_grupo_id)):
    contenido = svc.exportar_csv(id_grupo)
    return Response(
        content=contenido,
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=canciones.csv"},
    )


@router.post("", response_model=CancionOut)
def crear(data: CancionCreate, id_grupo: str = Depends(get_grupo_id)):
    return svc.crear(id_grupo, data)


@router.post("/{id_cancion}/votar", response_model=CancionOut)
def votar(id_cancion: str, data: VotoRequest, id_grupo: str = Depends(get_grupo_id)):
    try:
        return svc.votar(id_grupo, id_cancion, data.id_usuario)
    except ValueError as e:
        raise HTTPException(404, str(e))


@router.post("/{id_cancion}/favorito", response_model=CancionOut)
def favorito(id_cancion: str, data: FavoritoRequest, id_grupo: str = Depends(get_grupo_id)):
    try:
        return svc.favorito_toggle(id_grupo, id_cancion, data.id_usuario)
    except ValueError as e:
        raise HTTPException(404, str(e))
