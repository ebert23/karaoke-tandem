"""Cliente de Google Sheets: conexión + acceso genérico a "tablas" (hojas).

Toda la base de datos de la app vive en un único Google Sheet. Cada hoja
(pestaña) se trata como una tabla: la fila 1 son los encabezados exactos
definidos abajo, y cada fila siguiente es un registro.

Seguridad: todas las escrituras usan value_input_option="RAW", así Sheets
nunca interpreta un valor escrito por un usuario (p.ej. "=HYPERLINK(...)")
como fórmula — se guarda siempre como texto literal.
"""
import json
import time
from functools import lru_cache
from typing import Any

import gspread
from google.oauth2.service_account import Credentials

from .config import settings

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive.readonly",
]

# --- Definición de encabezados de cada hoja (deben coincidir con la fila 1) ---
# "ID Grupo" aísla los datos de cada grupo/sala dentro del mismo Sheet.
CANCIONES_HEADERS = [
    "ID", "ID Grupo", "Título", "Artista", "Género", "Link YouTube",
    "Agregado por", "Fecha agregado", "Votos", "Veces cantada",
]
USUARIOS_HEADERS = ["ID", "ID Grupo", "Nombre", "Foto", "Puntos totales", "Sesiones jugadas"]
SESIONES_HEADERS = ["ID Sesión", "ID Grupo", "Fecha", "Participantes", "Estado", "Turno actual"]
CANCIONES_SESION_HEADERS = [
    "ID Sesión", "ID Grupo", "ID Canción", "Turno", "Cantada por", "Puntuación", "Estado",
]
RETOS_HEADERS = ["ID", "ID Grupo", "Texto del reto", "Dificultad", "Categoría"]
# Hoja adicional (no listada en el pedido original) necesaria para que cada
# usuario pueda votar una sola vez por canción sin duplicar votos.
VOTOS_HEADERS = ["ID Voto", "ID Grupo", "ID Canción", "ID Usuario", "Fecha"]

# Grupos/salas: cada grupo de amigos tiene su propio espacio aislado.
GRUPOS_HEADERS = ["ID", "Nombre", "Código", "Foto", "Admins", "Fecha creación"]
# Canciones favoritas por usuario (independiente de los votos de la semana).
FAVORITOS_HEADERS = ["ID Grupo", "ID Usuario", "ID Canción", "Fecha"]
# Calificación en vivo de cada interpretación durante una sesión de karaoke.
VOTOS_TURNO_HEADERS = ["ID Grupo", "ID Sesión", "ID Canción", "Turno", "ID Usuario", "Puntuación", "Fecha"]

SHEETS: dict[str, list[str]] = {
    "Canciones": CANCIONES_HEADERS,
    "Usuarios": USUARIOS_HEADERS,
    "Sesiones": SESIONES_HEADERS,
    "Canciones_Sesion": CANCIONES_SESION_HEADERS,
    "Retos": RETOS_HEADERS,
    "Votos": VOTOS_HEADERS,
    "Grupos": GRUPOS_HEADERS,
    "Favoritos": FAVORITOS_HEADERS,
    "Votos_Turno": VOTOS_TURNO_HEADERS,
}

DEFAULT_RETOS: list[list[str]] = [
    ["Canta agachado toda la canción", "Fácil", "Normal"],
    ["Cambia la letra por algo gracioso en el coro", "Medio", "Creativo"],
    ["Baila sin cantar los primeros 15 segundos", "Fácil", "Normal"],
    ["Cántale la canción a alguien del grupo mirándolo a los ojos", "Medio", "Picante"],
    ["Todo el grupo debe hacer los coros contigo", "Fácil", "Grupo"],
    ["Inventa una coreografía en 10 segundos y úsala toda la canción", "Difícil", "Creativo"],
    ["Canta con acento de otro país", "Medio", "Creativo"],
    ["Elige a alguien para que sea tu dueto sorpresa", "Medio", "Grupo"],
    ["Si te equivocas en la letra, debes repetir la estrofa bailando", "Difícil", "Picante"],
    ["Regala un piropo cantado a alguien del público antes de empezar", "Fácil", "Picante"],
]

# Sugerencias de canciones populares por género, para el modal de "agregar
# canción" (chips de un click). Curada a mano — no depende de cuota de
# ninguna API externa. El link queda vacío a propósito: el usuario lo
# completa buscando en YouTube o pegándolo manualmente.
SUGERENCIAS_POR_GENERO: dict[str, list[tuple[str, str]]] = {
    "Pop": [
        ("Shape of You", "Ed Sheeran"),
        ("Blinding Lights", "The Weeknd"),
        ("Levitating", "Dua Lipa"),
    ],
    "Rock": [
        ("Livin' on a Prayer", "Bon Jovi"),
        ("Zombie", "The Cranberries"),
        ("De Musica Ligera", "Soda Stereo"),
    ],
    "Balada": [
        ("Perfect", "Ed Sheeran"),
        ("Un Beso", "Aventura"),
        ("Amor Eterno", "Rocio Durcal"),
    ],
    "Reggaeton": [
        ("Danza Kuduro", "Don Omar"),
        ("Gasolina", "Daddy Yankee"),
        ("Vivir Mi Vida", "Marc Anthony"),
    ],
    "Cumbia": [
        ("La Cumbia del Rio", "Los Angeles Azules"),
        ("El Sonidito", "Hechizeros Band"),
        ("Cumbia Sobre el Rio", "Selena"),
    ],
    "Salsa": [
        ("Vivir Mi Vida", "Marc Anthony"),
        ("La Vida es un Carnaval", "Celia Cruz"),
        ("Pedro Navaja", "Ruben Blades"),
    ],
    "Norteña": [
        ("El Rey", "Vicente Fernandez"),
        ("Cielito Lindo", "Ana Gabriel"),
        ("Volver Volver", "Vicente Fernandez"),
    ],
}


@lru_cache
def _get_client() -> gspread.Client:
    if settings.google_service_account_json:
        info = json.loads(settings.google_service_account_json)
        creds = Credentials.from_service_account_info(info, scopes=SCOPES)
    elif settings.google_credentials_file.exists():
        creds = Credentials.from_service_account_file(
            str(settings.google_credentials_file), scopes=SCOPES
        )
    else:
        raise RuntimeError(
            "No hay credenciales de Google configuradas. Define "
            "GOOGLE_SERVICE_ACCOUNT_JSON o coloca backend/credentials.json "
            "(ver DEPLOY.md)."
        )
    return gspread.authorize(creds)


@lru_cache
def _get_spreadsheet() -> gspread.Spreadsheet:
    if not settings.google_sheet_id:
        raise RuntimeError("Falta GOOGLE_SHEET_ID en las variables de entorno.")
    return _get_client().open_by_key(settings.google_sheet_id)


@lru_cache
def _get_worksheet(name: str) -> gspread.Worksheet:
    """Cachea el objeto Worksheet por nombre.

    gspread.Spreadsheet.worksheet() vuelve a pedir los metadatos de TODO el
    Sheet cada vez que se llama. Sin este cache, cada lectura/escritura de
    SheetTable disparaba una llamada extra a la API — con varias acciones
    seguidas (p.ej. cambiar de filtro de género varias veces) eso agotaba la
    cuota de lecturas por minuto de Google Sheets (error 429). El objeto
    Worksheet en sí no cambia durante la vida de esta instancia serverless.
    """
    return _get_spreadsheet().worksheet(name)


def _codigo_unico(grupos_ws: gspread.Worksheet) -> str:
    """Genera un código de invitación de 6 dígitos que no choque con uno existente."""
    import random

    existentes = set(grupos_ws.col_values(3)[1:])  # columna "Código", sin encabezado
    while True:
        codigo = f"{random.randint(0, 999999):06d}"
        if codigo not in existentes:
            return codigo


def ensure_sheets() -> None:
    """Crea las hojas y encabezados que falten. Idempotente — se corre al iniciar.

    Importante: si una hoja ya existe y tiene una fila de encabezados no
    vacía que no coincide con lo esperado, NO se sobrescribe (eso movería el
    significado de columnas con datos reales debajo, sin mover los datos).
    Solo se registra una advertencia; el ajuste en ese caso debe hacerse a
    mano en el Sheet — EXCEPTO el caso especial de la migración a Grupos
    (ver más abajo), que es una inserción de columna seguro y reversible.
    """
    import logging

    logger = logging.getLogger("karaoketandem")

    ss = _get_spreadsheet()
    existing = {ws.title: ws for ws in ss.worksheets()}

    for name, headers in SHEETS.items():
        ws = existing.get(name)
        if ws is None:
            ws = ss.add_worksheet(title=name, rows=200, cols=max(10, len(headers)))
            ws.append_row(headers, value_input_option="RAW")
            ws.freeze(rows=1)
            existing[name] = ws
        else:
            first_row = ws.row_values(1)
            if not first_row:
                ws.update("A1", [headers], value_input_option="RAW")
                ws.freeze(rows=1)

    # --- Migración a Grupos ---
    # Si la hoja "Grupos" se acaba de crear (estaba vacía), se siembra un
    # grupo "Original" y se le asigna TODO lo que ya existía en las demás
    # hojas (útil la primera vez que este código corre sobre un Sheet que
    # todavía no tenía el concepto de grupos). Es idempotente: en el
    # siguiente arranque los encabezados ya van a coincidir y no se toca
    # nada más.
    grupos_ws = existing["Grupos"]
    grupo_original_id: str | None = None
    if len(grupos_ws.get_all_values()) <= 1:
        from .services.ids import new_id, now_iso

        grupo_original_id = new_id("G")
        codigo = _codigo_unico(grupos_ws)
        grupos_ws.append_row(
            [grupo_original_id, "Original", codigo, "", "", now_iso()],
            value_input_option="RAW",
        )
        logger.warning("grupo_original_creado id=%s codigo=%s", grupo_original_id, codigo)

    for name, headers in SHEETS.items():
        if name == "Grupos":
            continue
        ws = existing[name]
        first_row = ws.row_values(1)
        if not first_row or first_row == headers:
            continue

        esperado_sin_grupo = [h for h in headers if h != "ID Grupo"]
        if "ID Grupo" in headers and "ID Grupo" not in first_row and first_row == esperado_sin_grupo:
            grupo_id = grupo_original_id or (grupos_ws.col_values(1)[1:] or [""])[0]
            num_filas = len(ws.get_all_values()) - 1
            columna = ["ID Grupo"] + [grupo_id] * num_filas
            ws.insert_cols([columna], col=2, value_input_option="RAW")
            logger.warning(
                "sheet_migrada_a_grupo hoja=%s filas=%s grupo=%s", name, num_filas, grupo_id
            )
        else:
            logger.warning(
                "sheet_headers_mismatch hoja=%s esperado=%s encontrado=%s "
                "(no se modifica automáticamente para no desalinear datos existentes)",
                name, headers, first_row,
            )


# Caché de lectura en memoria del proceso, por hoja: (timestamp, filas). Vive
# mientras la instancia serverless siga "tibia" — no es un caché distribuido,
# pero alcanza para que las varias lecturas de una misma hoja que dispara una
# sola carga de pantalla (o ráfagas de varios usuarios casi al mismo tiempo)
# no cada una golpee la API de Sheets, que es lo que agotaba la cuota de
# lecturas por minuto (429). Cualquier escritura invalida la entrada al toque
# para no servir datos viejos después de guardar algo.
_TTL_SEGUNDOS = 4
_cache: dict[str, tuple[float, list[dict[str, Any]]]] = {}


class SheetTable:
    """Acceso genérico de lectura/escritura a una hoja, tratada como tabla."""

    def __init__(self, name: str):
        self.name = name
        self.headers = SHEETS[name]

    @property
    def ws(self) -> gspread.Worksheet:
        return _get_worksheet(self.name)

    def all_rows(self) -> list[dict[str, Any]]:
        """Devuelve todas las filas como dicts (todos los valores como texto)."""
        cacheado = _cache.get(self.name)
        if cacheado is not None and time.monotonic() - cacheado[0] < _TTL_SEGUNDOS:
            return [dict(r) for r in cacheado[1]]
        records = self.ws.get_all_records(
            expected_headers=self.headers, numericise_ignore=["all"]
        )
        _cache[self.name] = (time.monotonic(), records)
        return [dict(r) for r in records]

    def _invalidar_cache(self) -> None:
        _cache.pop(self.name, None)

    def append(self, row: dict[str, Any]) -> None:
        values = [str(row.get(h, "")) for h in self.headers]
        self.ws.append_row(values, value_input_option="RAW")
        self._invalidar_cache()

    def find_row_number(self, id_field: str, id_value: str) -> int | None:
        """1-based row number (incluye encabezado) o None si no existe.

        A propósito NO usa la caché de all_rows(): esta función resuelve la
        posición exacta de una fila que después se va a escribir
        (update_row/delete_row). Si dos instancias serverless tienen cada
        una su propio caché y una borra una fila mientras la otra todavía
        tiene la posición vieja, escribiría en la fila equivocada. Para
        listados de solo lectura sí conviene el caché (ver all_rows());
        para resolver "qué fila edito" siempre se pide en vivo.
        """
        col = self.headers.index(id_field) + 1
        cell = self.ws.find(id_value, in_column=col)
        return cell.row if cell else None

    def update_row(self, row_number: int, updates: dict[str, Any]) -> None:
        cells = []
        for field, value in updates.items():
            col = self.headers.index(field) + 1
            cells.append(gspread.Cell(row=row_number, col=col, value=str(value)))
        if cells:
            self.ws.update_cells(cells, value_input_option="RAW")
        self._invalidar_cache()

    def get_by_id(self, id_field: str, id_value: str) -> tuple[int, dict[str, Any]] | tuple[None, None]:
        row_number = self.find_row_number(id_field, id_value)
        if row_number is None:
            return None, None
        row_values = self.ws.row_values(row_number)
        row = {h: (row_values[i] if i < len(row_values) else "") for i, h in enumerate(self.headers)}
        return row_number, row

    def delete_row(self, row_number: int) -> None:
        self.ws.delete_rows(row_number)
        self._invalidar_cache()
