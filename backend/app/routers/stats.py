"""Endpoints de estadísticas personales."""
from fastapi import APIRouter, Depends, HTTPException

from ..deps import get_grupo_id
from ..schemas import EstadisticasOut
from ..services import stats as svc

router = APIRouter(prefix="/api/estadisticas", tags=["estadisticas"])


@router.get("/{id_usuario}", response_model=EstadisticasOut)
def estadisticas(id_usuario: str, id_grupo: str = Depends(get_grupo_id)):
    try:
        return svc.estadisticas(id_grupo, id_usuario)
    except ValueError as e:
        raise HTTPException(404, str(e))
