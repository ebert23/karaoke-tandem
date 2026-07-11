"""Lógica de negocio de Retos: aleatorio por categoría y altas personalizadas."""
import random

from ..sheets_client import SheetTable
from .ids import new_id

CATEGORIAS = ["Normal", "Picante", "Creativo", "Grupo"]


def seed_default_retos(id_grupo: str) -> None:
    """Carga los retos por defecto para un grupo recién creado (un solo request)."""
    from ..sheets_client import DEFAULT_RETOS

    filas = [
        [new_id("R"), id_grupo, texto, dificultad, categoria]
        for texto, dificultad, categoria in DEFAULT_RETOS
    ]
    _table().ws.append_rows(filas, value_input_option="RAW")


def _table() -> SheetTable:
    return SheetTable("Retos")


def _row_to_out(row: dict) -> dict:
    return {
        "id": row["ID"],
        "texto": row["Texto del reto"],
        "dificultad": row["Dificultad"],
        "categoria": row["Categoría"],
    }


def listar(id_grupo: str, categoria: str | None = None) -> list[dict]:
    rows = [_row_to_out(r) for r in _table().all_rows() if r["ID Grupo"] == id_grupo]
    if categoria:
        rows = [r for r in rows if r["categoria"].lower() == categoria.lower()]
    return rows


def aleatorio(id_grupo: str, categoria: str | None = None) -> dict:
    disponibles = listar(id_grupo, categoria)
    if not disponibles:
        raise ValueError("No hay retos disponibles para esa categoría")
    return random.choice(disponibles)


def crear(id_grupo: str, texto: str, dificultad: str, categoria: str) -> dict:
    row = {
        "ID": new_id("R"),
        "ID Grupo": id_grupo,
        "Texto del reto": texto.strip(),
        "Dificultad": dificultad,
        "Categoría": categoria,
    }
    _table().append(row)
    return _row_to_out(row)
