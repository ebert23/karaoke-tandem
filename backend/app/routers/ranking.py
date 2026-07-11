"""Endpoints de ranking / gamificación."""
from fastapi import APIRouter, Depends

from ..deps import get_grupo_id
from ..schemas import RankingEntry
from ..services import ranking as svc

router = APIRouter(prefix="/api/ranking", tags=["ranking"])


@router.get("/noche/{id_sesion}", response_model=list[RankingEntry])
def ranking_noche(id_sesion: str, id_grupo: str = Depends(get_grupo_id)):
    return svc.ranking_noche(id_grupo, id_sesion)


@router.get("/historico", response_model=list[RankingEntry])
def ranking_historico(id_grupo: str = Depends(get_grupo_id)):
    return svc.ranking_historico(id_grupo)
