"""Modelos Pydantic para requests/responses de la API."""
from pydantic import BaseModel, Field


# --- Grupos ---
class GrupoCreate(BaseModel):
    nombre: str = Field(min_length=1, max_length=80)
    foto: str = ""
    creado_por_nombre: str = Field(min_length=1, max_length=80)


class GrupoUnirseRequest(BaseModel):
    codigo: str = Field(min_length=6, max_length=6)


class GrupoOut(BaseModel):
    id: str
    nombre: str
    codigo: str
    foto: str
    admins: list[str]
    fecha_creacion: str


class GrupoDetalleOut(GrupoOut):
    miembros: list["UsuarioOut"] = []


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


class VotarTurnoRequest(BaseModel):
    id_usuario: str
    puntuacion: int = Field(ge=1, le=10)


class VotoTurnoOut(BaseModel):
    id_usuario: str
    puntuacion: int


class VotosTurnoOut(BaseModel):
    votos: list[VotoTurnoOut]
    promedio: float | None


GrupoDetalleOut.model_rebuild()
