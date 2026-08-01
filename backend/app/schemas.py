"""Modelos Pydantic para requests/responses de la API."""
from pydantic import BaseModel, Field


# --- Grupos ---
class GrupoCreate(BaseModel):
    nombre: str = Field(min_length=1, max_length=80)
    foto: str = ""
    creado_por_nombre: str = Field(min_length=1, max_length=80)
    # "salon" crea directamente un local de karaoke (mesas + DJ) en vez de una
    # sala de amigos. Los clientes viejos no mandan el campo y siguen creando
    # grupos normales.
    modo: str = Field(default="grupo", pattern="^(grupo|salon)$")


class GrupoUnirseRequest(BaseModel):
    codigo: str = Field(min_length=6, max_length=6)


class GrupoOut(BaseModel):
    id: str
    nombre: str
    codigo: str
    foto: str
    admins: list[str]
    fecha_creacion: str
    modo: str = "grupo"


class GrupoConDjOut(GrupoOut):
    # Solo se devuelve al admin que lo pide explícitamente (convertir a salón
    # o regenerar); nunca en el detalle normal del grupo.
    codigo_dj: str = ""


class GrupoDetalleOut(GrupoOut):
    miembros: list["UsuarioOut"] = []


class MiembroAccionRequest(BaseModel):
    # Quien ejecuta la acción (debe ser admin del grupo) — se verifica en el
    # servicio, igual que id_usuario en VotoRequest/FavoritoRequest.
    id_usuario_actor: str


class ReclamarAdminRequest(BaseModel):
    id_usuario: str


# --- Canciones ---
class CancionCreate(BaseModel):
    titulo: str = Field(min_length=1, max_length=200)
    artista: str = Field(min_length=1, max_length=200)
    genero: str = Field(min_length=1, max_length=60)
    link_youtube: str = ""
    agregado_por: str = Field(min_length=1, max_length=80)


class CancionOut(BaseModel):
    id: str
    titulo: str
    artista: str
    genero: str
    link_youtube: str
    agregado_por: str
    fecha_agregado: str
    votos: int
    veces_cantada: int
    ya_voto: bool = False
    es_favorita: bool = False


class CancionUpdate(BaseModel):
    titulo: str = Field(min_length=1, max_length=200)
    artista: str = Field(min_length=1, max_length=200)
    genero: str = Field(min_length=1, max_length=60)
    link_youtube: str = ""
    # Quien pide el cambio — se verifica que sea el autor o un admin.
    id_usuario: str


class VotoRequest(BaseModel):
    id_usuario: str


# --- Usuarios ---
class UsuarioCreate(BaseModel):
    nombre: str = Field(min_length=1, max_length=80)
    foto: str = ""


class UsuarioOut(BaseModel):
    id: str
    nombre: str
    foto: str
    puntos_totales: int
    sesiones_jugadas: int


# --- Sesiones ---
class SesionCreate(BaseModel):
    participantes: list[str] = Field(min_length=1)


class SesionOut(BaseModel):
    id_sesion: str
    fecha: str
    participantes: list[str]
    estado: str
    turno_actual: int


class MarcarCantadaRequest(BaseModel):
    # Opcional: si hubo votación en vivo (Votos_Turno), se usa el promedio y
    # este valor se ignora. Solo hace falta si nadie votó (p.ej. una prueba
    # en solitario).
    puntuacion: int | None = Field(default=None, ge=1, le=10)


class CancionSesionOut(BaseModel):
    id_sesion: str
    id_cancion: str
    turno: int
    cantada_por: str
    puntuacion: int | None
    estado: str
    cancion: CancionOut | None = None


# --- Retos ---
class RetoCreate(BaseModel):
    texto: str = Field(min_length=1, max_length=300)
    dificultad: str = Field(pattern="^(Fácil|Medio|Difícil)$")
    categoria: str = Field(pattern="^(Normal|Picante|Creativo|Grupo)$")


class RetoOut(BaseModel):
    id: str
    texto: str
    dificultad: str
    categoria: str


# --- Ranking / gamificación ---
class BadgeOut(BaseModel):
    codigo: str
    nombre: str
    descripcion: str
    icono: str


class RankingEntry(BaseModel):
    id_usuario: str
    nombre: str
    foto: str
    puntos: int
    canciones_cantadas: int
    badges: list[BadgeOut] = []


# --- Estadísticas ---
class EstadisticasOut(BaseModel):
    id_usuario: str
    nombre: str
    canciones_cantadas: int
    puntuacion_promedio: float
    genero_favorito: str | None
    canciones_top: list[dict]
    generos: dict[str, int]


# --- Favoritos / sugerencias / YouTube ---
class FavoritoRequest(BaseModel):
    id_usuario: str


class SugerenciaOut(BaseModel):
    titulo: str
    artista: str
    genero: str


class YoutubeResultadoOut(BaseModel):
    titulo: str
    canal: str
    link_youtube: str
    miniatura: str


# --- Karaoke en vivo: cola, unirse, votación por turno ---
class ColaRequest(BaseModel):
    id_cancion: str
    # Cantantes elegidos a mano (dueto/grupal). Vacío = se asigna por turno.
    cantantes: list[str] = Field(default_factory=list)


class SesionUnirseRequest(BaseModel):
    nombre: str = Field(min_length=1, max_length=80)


class ColaAccionRequest(BaseModel):
    # Quien ejecuta la acción (debe ser admin del grupo) — se verifica en el
    # servicio, igual que MiembroAccionRequest.
    id_usuario_actor: str


class SiguienteRequest(ColaAccionRequest):
    # "cola": promueve la primera de la cola. "aleatorio": sortea del
    # catálogo ignorando la cola (lo encolado queda reservado).
    # None (no viene el campo): comportamiento histórico — primero la cola y
    # si está vacía sortea. Hace falta porque la app es una PWA: un celular
    # con el bundle viejo en caché sigue mandando el request sin "modo", y
    # con un default "cola" se le rompía con un 400 al quedarse sin cola.
    modo: str | None = Field(default=None, pattern="^(cola|aleatorio)$")


class MoverColaRequest(ColaAccionRequest):
    direccion: str = Field(pattern="^(arriba|abajo)$")


class VotarTurnoRequest(BaseModel):
    id_usuario: str
    puntuacion: int = Field(ge=1, le=10)


class VotoTurnoOut(BaseModel):
    id_usuario: str
    puntuacion: int


class VotosTurnoOut(BaseModel):
    votos: list[VotoTurnoOut]
    promedio: float | None


# --- Modo salón: mesas, pedidos, vista del DJ ---
class DjEntrarRequest(BaseModel):
    codigo: str = Field(min_length=8, max_length=120)


class MesaCreate(BaseModel):
    numero: str = Field(min_length=1, max_length=40)
    tamano: int = Field(default=2, ge=1, le=30)


class MesaAbrirRequest(BaseModel):
    # Cuánta gente se sentó. Define el cupo por ronda (1 persona -> 1 canción
    # por vuelta, 2+ -> 2). Es autodeclarado y el local lo puede corregir.
    tamano: int = Field(default=2, ge=1, le=30)


class MesaOut(BaseModel):
    id: str
    numero: str
    codigo: str
    tamano: int
    cupo_por_ronda: int
    estado: str
    id_sesion: str | None = None
    fecha_apertura: str = ""
    pedidos_cancelados: int | None = None


class PedidoCreate(BaseModel):
    id_cancion: str
    # Nombre libre de quien va a cantar. No es un usuario del grupo: en el
    # salón el público rota toda la noche.
    pedido_por: str = Field(default="", max_length=80)


class SugerenciaCreate(BaseModel):
    titulo: str = Field(min_length=1, max_length=200)
    artista: str = Field(default="", max_length=200)
    pedido_por: str = Field(default="", max_length=80)


class PedidoOut(BaseModel):
    id: int
    id_cancion: str
    cancion: CancionOut | None = None
    estado: str
    ronda: int
    turno: int
    pedido_por: str
    fecha_pedido: str = ""
    fecha_cantada: str = ""
    id_mesa: str | None = None
    mesa_numero: str = ""
    # Solo vienen en la vista del DJ.
    repetida: bool | None = None
    cantada_hace_min: int | None = None
    # Solo vienen en la vista del cliente.
    posicion: int | None = None
    espera_min: int | None = None
    es_mi_mesa: bool | None = None


class ColaSalonOut(BaseModel):
    id_sesion: str
    ahora: PedidoOut | None = None
    cola: list[PedidoOut] = []
    cantadas: list[PedidoOut] = []
    total_cantadas: int = 0
    ronda_actual: int = 0
    mesas_abiertas: int = 0


class MesaResumenOut(BaseModel):
    id: str
    numero: str
    estado: str
    tamano: int | None = None
    cupo_por_ronda: int | None = None


class EstadoMesaOut(BaseModel):
    mesa: MesaResumenOut
    abierta: bool
    ahora: PedidoOut | None = None
    mis_pedidos: list[PedidoOut] = []
    total_en_cola: int = 0
    max_pedidos: int | None = None


class SugerenciaMesaOut(BaseModel):
    id: int
    titulo: str
    artista: str
    pedido_por: str
    mesa_numero: str
    fecha: str


GrupoDetalleOut.model_rebuild()
