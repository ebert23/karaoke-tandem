"""Endpoints de Canciones: listado, alta, votación, favoritos, top 10,
sugerencias, búsqueda en YouTube y export CSV."""
from fastapi import APIRouter, Depends, HTTPException, Response

from ..deps import get_grupo_id
from ..schemas import (
    CancionCreate,
    CancionOut,
    CancionUpdate,
    FavoritoRequest,
    ImportacionOut,
    ImportarCancionesRequest,
    SugerenciaOut,
    VotoRequest,
)
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


@router.get("/duplicada", response_model=CancionOut | None)
def duplicada(
    titulo: str = "",
    artista: str = "",
    link_youtube: str = "",
    id_grupo: str = Depends(get_grupo_id),
    excluir_id: str = "",
):
    """La canción del grupo que ya representa a esta, o null.

    La usa el formulario para avisar mientras se escribe, antes de que la
    persona termine de cargar todo y recién ahí se entere de que ya estaba.
    La regla vive en el servicio y no repetida en el front, así el aviso y el
    rechazo del alta no pueden decir cosas distintas.
    """
    return svc.duplicada(id_grupo, titulo, artista, link_youtube, excluir_id=excluir_id)


@router.post("/importar", response_model=ImportacionOut)
def importar(data: ImportarCancionesRequest, id_grupo: str = Depends(get_grupo_id)):
    """Carga un catálogo entero desde un CSV. Solo admins.

    Con confirmar=false devuelve el mismo resumen sin escribir nada, para que
    el dueño vea cuántas entran, cuántas ya tenía y qué filas están mal antes
    de tocar su catálogo.
    """
    try:
        svc.requiere_admin(id_grupo, data.id_usuario_actor)
        return svc.importar_csv(id_grupo, data.contenido, confirmar=data.confirmar)
    except PermissionError as e:
        raise HTTPException(403, str(e))
    except ValueError as e:
        raise HTTPException(400, str(e))


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
    try:
        return svc.crear(id_grupo, data)
    except svc.CancionDuplicada as e:
        raise HTTPException(400, str(e))


@router.put("/{id_cancion}", response_model=CancionOut)
def actualizar(id_cancion: str, data: CancionUpdate, id_grupo: str = Depends(get_grupo_id)):
    try:
        return svc.actualizar(id_grupo, id_cancion, data.id_usuario, data)
    except svc.CancionDuplicada as e:
        raise HTTPException(400, str(e))
    except PermissionError as e:
        raise HTTPException(403, str(e))
    except ValueError as e:
        raise HTTPException(404, str(e))


@router.delete("/{id_cancion}")
def eliminar(id_cancion: str, data: VotoRequest, id_grupo: str = Depends(get_grupo_id)):
    try:
        svc.eliminar(id_grupo, id_cancion, data.id_usuario)
    except PermissionError as e:
        raise HTTPException(403, str(e))
    except ValueError as e:
        raise HTTPException(404, str(e))
    return {"ok": True}


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
