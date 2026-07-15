"""Lógica de negocio de Retos: aleatorio por categoría y altas personalizadas."""
import random

from .. import db
from ..curated_data import DEFAULT_RETOS
from .ids import new_id

CATEGORIAS = ["Normal", "Picante", "Creativo", "Grupo"]


def seed_default_retos(id_grupo: str) -> None:
    """Carga los retos por defecto para un grupo recién creado (un solo request)."""
    filas = [(new_id("R"), id_grupo, texto, dificultad, categoria) for texto, dificultad, categoria in DEFAULT_RETOS]
    db.execute_many(
        "INSERT INTO retos (id, id_grupo, texto, dificultad, categoria) VALUES (%s, %s, %s, %s, %s)",
        filas,
    )


def _row_to_out(row: dict) -> dict:
    return {
        "id": row["id"],
        "texto": row["texto"],
        "dificultad": row["dificultad"],
        "categoria": row["categoria"],
    }


def listar(id_grupo: str, categoria: str | None = None) -> list[dict]:
    rows = [_row_to_out(r) for r in db.fetch_all("SELECT * FROM retos WHERE id_grupo = %s", (id_grupo,))]
    if categoria:
        rows = [r for r in rows if r["categoria"].lower() == categoria.lower()]
    return rows


def aleatorio(id_grupo: str, categoria: str | None = None) -> dict:
    disponibles = listar(id_grupo, categoria)
    if not disponibles:
        raise ValueError("No hay retos disponibles para esa categoría")
    return random.choice(disponibles)


def crear(id_grupo: str, texto: str, dificultad: str, categoria: str) -> dict:
    id_reto = new_id("R")
    texto = texto.strip()
    db.execute(
        "INSERT INTO retos (id, id_grupo, texto, dificultad, categoria) VALUES (%s, %s, %s, %s, %s)",
        (id_reto, id_grupo, texto, dificultad, categoria),
    )
    return {"id": id_reto, "texto": texto, "dificultad": dificultad, "categoria": categoria}
