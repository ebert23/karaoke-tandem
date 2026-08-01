"""Endpoints del modo salón: mesas del local, pedidos desde el celular del
cliente y la vista del DJ.

Tres públicos distintos, con tres formas de entrar:

- **Dueño** (`/api/mesas`): X-Grupo-Id + id_usuario_actor admin, igual que el
  resto del panel de grupo.
- **Cliente** (`/api/mesa/{codigo}`): solo el código del QR de su mesa. No
  manda X-Grupo-Id a propósito — el código ya dice de qué local y qué mesa se
  trata, y así el celular de un cliente nunca necesita saber el id del grupo.
- **DJ** (`/api/dj`): X-Grupo-Id + X-DJ-Codigo (ver deps.requiere_dj).
"""
from fastapi import APIRouter, Depends, HTTPException

from ..deps import get_grupo_id, requiere_dj
from ..schemas import (
    CancionOut,
    ColaSalonOut,
    DjEntrarRequest,
    EstadoMesaOut,
    GrupoOut,
    MesaAbrirRequest,
    MesaCreate,
    MesaOut,
    MiembroAccionRequest,
    PedidoCreate,
    PedidoOut,
    SugerenciaCreate,
    SugerenciaMesaOut,
)
from ..services import canciones as canciones_svc
from ..services import grupos as grupos_svc
from ..services import mesas as mesas_svc
from ..services import sesiones as sesiones_svc

router = APIRouter(tags=["salon"])


def _requiere_admin(id_grupo: str, id_usuario_actor: str) -> None:
    grupo = grupos_svc.get_por_id(id_grupo)
    if grupo is None:
        raise HTTPException(404, "Local no encontrado")
    if not grupos_svc.es_admin(grupo, id_usuario_actor):
        raise HTTPException(403, "Solo un admin del local puede hacer esto")


def _sesion_activa_o_error(id_grupo: str) -> str:
    sesion = sesiones_svc.get_activa(id_grupo)
    if sesion is None:
        raise HTTPException(400, "No hay una noche abierta: creá la sesión primero")
    return sesion["id_sesion"]


# ---------------------------------------------------------------------------
# Panel del dueño
# ---------------------------------------------------------------------------

@router.get("/api/mesas", response_model=list[MesaOut])
def listar_mesas(id_grupo: str = Depends(get_grupo_id)):
    return mesas_svc.listar(id_grupo)


@router.post("/api/mesas", response_model=MesaOut)
def crear_mesa(data: MesaCreate, id_grupo: str = Depends(get_grupo_id)):
    try:
        return mesas_svc.crear(id_grupo, data.numero, data.tamano)
    except ValueError as e:
        raise HTTPException(400, str(e))


@router.post("/api/mesas/{id_mesa}/abrir", response_model=MesaOut)
def abrir_mesa(id_mesa: str, data: MesaAbrirRequest, id_grupo: str = Depends(get_grupo_id)):
    id_sesion = _sesion_activa_o_error(id_grupo)
    # La ronda en curso se calcula acá y se congela en la mesa: es lo que
    # define en qué punto de la rotación entra la gente que recién se sienta.
    ronda = sesiones_svc.ronda_actual(id_grupo, id_sesion)
    try:
        return mesas_svc.abrir(id_grupo, id_mesa, id_sesion, ronda, data.tamano)
    except ValueError as e:
        raise HTTPException(404, str(e))


@router.post("/api/mesas/{id_mesa}/cerrar", response_model=MesaOut)
def cerrar_mesa(id_mesa: str, id_grupo: str = Depends(get_grupo_id)):
    try:
        return mesas_svc.cerrar(id_grupo, id_mesa)
    except ValueError as e:
        raise HTTPException(404, str(e))


@router.delete("/api/mesas/{id_mesa}", status_code=204)
def eliminar_mesa(id_mesa: str, data: MiembroAccionRequest, id_grupo: str = Depends(get_grupo_id)):
    _requiere_admin(id_grupo, data.id_usuario_actor)
    try:
        mesas_svc.eliminar(id_grupo, id_mesa)
    except ValueError as e:
        raise HTTPException(400, str(e))


# ---------------------------------------------------------------------------
# Cliente en la mesa (entra por el QR, sin X-Grupo-Id)
# ---------------------------------------------------------------------------

def _mesa_por_codigo(codigo: str) -> dict:
    mesa = mesas_svc.get_row_por_codigo(codigo)
    if mesa is None:
        raise HTTPException(404, "Código de mesa no encontrado")
    return mesa


@router.get("/api/mesa/{codigo}", response_model=EstadoMesaOut)
def estado_mesa(codigo: str):
    return sesiones_svc.estado_mesa(_mesa_por_codigo(codigo))


@router.get("/api/mesa/{codigo}/catalogo", response_model=list[CancionOut])
def catalogo_mesa(codigo: str, q: str | None = None, genero: str | None = None):
    """Catálogo del local. Cerrado a propósito: el cliente solo puede pedir lo
    que el DJ realmente tiene para poner."""
    mesa = _mesa_por_codigo(codigo)
    return canciones_svc.listar(mesa["id_grupo"], q=q, genero=genero)


@router.post("/api/mesa/{codigo}/pedidos", response_model=PedidoOut)
def crear_pedido(codigo: str, data: PedidoCreate):
    mesa = _mesa_por_codigo(codigo)
    if not mesa["id_sesion"]:
        raise HTTPException(400, "La mesa está cerrada: pedile al mozo que la abra")
    try:
        return sesiones_svc.agregar_pedido(
            mesa["id_grupo"], mesa["id_sesion"], mesa, data.id_cancion, data.pedido_por
        )
    except ValueError as e:
        raise HTTPException(400, str(e))


@router.delete("/api/mesa/{codigo}/pedidos/{id_pedido}", status_code=204)
def cancelar_pedido_propio(codigo: str, id_pedido: int):
    mesa = _mesa_por_codigo(codigo)
    try:
        # Se pasa id_mesa para que una mesa solo pueda borrar lo suyo: el
        # código de otra mesa no alcanza para tocarle la lista a nadie.
        sesiones_svc.cancelar_pedido(mesa["id_grupo"], id_pedido, id_mesa=mesa["id"])
    except PermissionError as e:
        raise HTTPException(403, str(e))
    except ValueError as e:
        raise HTTPException(404, str(e))


@router.post("/api/mesa/{codigo}/sugerencias", response_model=SugerenciaMesaOut)
def sugerir_cancion(codigo: str, data: SugerenciaCreate):
    mesa = _mesa_por_codigo(codigo)
    if not mesa["id_sesion"]:
        raise HTTPException(400, "La mesa está cerrada: pedile al mozo que la abra")
    try:
        return sesiones_svc.agregar_sugerencia(
            mesa["id_grupo"], mesa["id_sesion"], mesa, data.titulo, data.artista, data.pedido_por
        )
    except ValueError as e:
        raise HTTPException(400, str(e))


# ---------------------------------------------------------------------------
# Vista del DJ
# ---------------------------------------------------------------------------

@router.post("/api/dj/entrar", response_model=GrupoOut)
def dj_entrar(data: DjEntrarRequest):
    """El DJ entra tipeando su código y de ahí sale de qué local se trata.

    Así el secreto viaja en el body y no en la URL: una URL con el código
    quedaría en el historial del navegador, en el botón de compartir y en los
    logs de cualquier proxy entre el celular y el servidor.
    """
    grupo = grupos_svc.por_codigo_dj(data.codigo)
    if grupo is None:
        raise HTTPException(404, "Código de DJ no encontrado")
    return grupo


@router.get("/api/salon/pantalla", response_model=ColaSalonOut)
def pantalla_salon(id_grupo: str = Depends(get_grupo_id)):
    """Vista de solo lectura para la pantalla del salón (Modo TV).

    No pide el código del DJ: lo que muestra ya está a la vista de todo el
    local, y obligar a la TV a tener el secreto sería meterlo en un equipo
    que queda encendido y desatendido toda la noche.
    """
    id_sesion = _sesion_activa_o_error(id_grupo)
    try:
        estado = sesiones_svc.cola_salon(id_grupo, id_sesion)
    except ValueError as e:
        raise HTTPException(400, str(e))
    estado["cola"] = estado["cola"][:6]
    estado["cantadas"] = []
    return estado


@router.get("/api/dj/cola", response_model=ColaSalonOut)
def dj_cola(id_grupo: str = Depends(requiere_dj)):
    id_sesion = _sesion_activa_o_error(id_grupo)
    try:
        return sesiones_svc.cola_salon(id_grupo, id_sesion)
    except ValueError as e:
        raise HTTPException(400, str(e))


@router.post("/api/dj/siguiente", response_model=PedidoOut | None)
def dj_siguiente(id_grupo: str = Depends(requiere_dj)):
    id_sesion = _sesion_activa_o_error(id_grupo)
    try:
        return sesiones_svc.siguiente_salon(id_grupo, id_sesion)
    except ValueError as e:
        raise HTTPException(400, str(e))


@router.post("/api/dj/pedidos/{id_pedido}/cantada", response_model=PedidoOut)
def dj_marcar_cantada(id_pedido: int, id_grupo: str = Depends(requiere_dj)):
    try:
        return sesiones_svc.marcar_cantada_salon(id_grupo, id_pedido)
    except ValueError as e:
        raise HTTPException(400, str(e))


@router.post("/api/dj/pedidos/{id_pedido}/no-vino", response_model=PedidoOut)
def dj_no_vino(id_pedido: int, id_grupo: str = Depends(requiere_dj)):
    try:
        return sesiones_svc.no_vino(id_grupo, id_pedido)
    except ValueError as e:
        raise HTTPException(400, str(e))


@router.post("/api/dj/pedidos/{id_pedido}/subir", response_model=PedidoOut)
def dj_subir(id_pedido: int, id_grupo: str = Depends(requiere_dj)):
    try:
        return sesiones_svc.subir_pedido(id_grupo, id_pedido)
    except ValueError as e:
        raise HTTPException(400, str(e))


@router.delete("/api/dj/pedidos/{id_pedido}", status_code=204)
def dj_cancelar(id_pedido: int, id_grupo: str = Depends(requiere_dj)):
    try:
        sesiones_svc.cancelar_pedido(id_grupo, id_pedido)
    except ValueError as e:
        raise HTTPException(400, str(e))


@router.get("/api/dj/sugerencias", response_model=list[SugerenciaMesaOut])
def dj_sugerencias(id_grupo: str = Depends(requiere_dj)):
    id_sesion = _sesion_activa_o_error(id_grupo)
    return sesiones_svc.listar_sugerencias(id_grupo, id_sesion)


@router.get("/api/dj/mesas", response_model=list[MesaOut])
def dj_mesas(id_grupo: str = Depends(requiere_dj)):
    return mesas_svc.listar(id_grupo)
