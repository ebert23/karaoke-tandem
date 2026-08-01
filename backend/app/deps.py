"""Dependencias comunes de FastAPI."""
import secrets

from fastapi import Depends, Header, HTTPException


def get_grupo_id(x_grupo_id: str = Header(alias="X-Grupo-Id")) -> str:
    """Grupo/sala activa del cliente. No se valida contra el Sheet en cada
    request (evita llamadas extra a la API de Sheets) — solo aísla los datos
    para la experiencia de uso, no es un mecanismo de seguridad con auth real.
    """
    if not x_grupo_id.strip():
        raise HTTPException(400, "Falta el header X-Grupo-Id")
    return x_grupo_id.strip()


def requiere_dj(
    id_grupo: str = Depends(get_grupo_id),
    x_dj_codigo: str = Header(default="", alias="X-DJ-Codigo"),
) -> str:
    """Puerta de la vista del DJ: exige el código secreto del local.

    ATENCIÓN — esto NO es autenticación. Es un secreto compartido tipo bearer:
    evita que la vista del DJ sea una URL adivinable, pero cualquiera que
    tenga el código es el DJ, no hay identidad detrás. El día que esto se
    venda a un local hay que reemplazarlo por auth de verdad; mientras tanto
    al menos el control de la noche no queda abierto a quien pruebe /dj.

    La comparación es de tiempo constante para no filtrar el código carácter a
    carácter con un ataque de temporización.
    """
    from .services import grupos as grupos_svc

    codigo_real = grupos_svc.get_codigo_dj(id_grupo)
    enviado = x_dj_codigo.strip()
    if not codigo_real:
        raise HTTPException(400, "Este local no tiene modo salón activado")
    if not enviado or not secrets.compare_digest(enviado, codigo_real):
        raise HTTPException(403, "Código de DJ inválido")
    return id_grupo
