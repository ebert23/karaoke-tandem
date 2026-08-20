"""Lógica de negocio de Retos: aleatorio por categoría, altas y bajas."""
import random
import re
import unicodedata

from .. import db
from ..curated_data import DEFAULT_RETOS
from . import grupos as grupos_svc
from .ids import new_id

CATEGORIAS = ["Normal", "Picante", "Creativo", "Grupo", "Shots"]


class RetoDuplicado(ValueError):
    """Subclase para que el router responda 400 y no la confunda con el otro
    ValueError de estas rutas ("Reto no encontrado", que es 404)."""


def _clave(texto: str) -> str:
    """Forma normalizada del texto, para comparar retos repetidos.

    Sin mayúsculas, tildes ni puntuación: escribir el mismo reto dos veces con
    una coma de diferencia es lo que pasa en la práctica, y tener el duplicado
    en la baraja hace que salga el doble de seguido que los demás.
    """
    s = unicodedata.normalize("NFKD", (texto or "").strip().lower())
    s = "".join(c for c in s if not unicodedata.combining(c))
    s = re.sub(r"[^a-z0-9 ]", " ", s)
    return re.sub(r"\s+", " ", s).strip()


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


def aleatorio(id_grupo: str, categoria: str | None = None, excluir: str = "") -> dict:
    """Un reto al azar. `excluir` es el que se está mostrando ahora.

    Sin eso, apretar "Otro reto" en una categoría chica devolvía el mismo una
    y otra vez: random.choice no tiene memoria. Si el único candidato es
    justamente el excluido se devuelve igual — mejor repetir que quedarse sin
    reto.
    """
    disponibles = listar(id_grupo, categoria)
    if not disponibles:
        raise ValueError("No hay retos disponibles para esa categoría")
    otros = [r for r in disponibles if r["id"] != excluir]
    return random.choice(otros or disponibles)


def crear(id_grupo: str, texto: str, dificultad: str, categoria: str) -> dict:
    texto = texto.strip()
    clave = _clave(texto)
    for existente in listar(id_grupo):
        if _clave(existente["texto"]) == clave:
            raise RetoDuplicado(f'Ese reto ya está en la baraja: "{existente["texto"]}"')

    id_reto = new_id("R")
    db.execute(
        "INSERT INTO retos (id, id_grupo, texto, dificultad, categoria) VALUES (%s, %s, %s, %s, %s)",
        (id_reto, id_grupo, texto, dificultad, categoria),
    )
    return {"id": id_reto, "texto": texto, "dificultad": dificultad, "categoria": categoria}


def restaurar_defaults(id_grupo: str, id_usuario_actor: str) -> int:
    """Agrega los retos por defecto que le falten al grupo. Devuelve cuántos.

    Hace falta porque seed_default_retos solo corre al crear el grupo: cuando
    la baraja por defecto crece (o cuando alguien borró algo y se arrepintió),
    los grupos que ya existían no se enteran nunca.

    Es a pedido y no automático — la categoría Shots no le sirve a todas las
    salas, y meterle retos de alcohol a un grupo de la oficina sin que nadie lo
    haya pedido sería peor que no tenerlos. Solo agrega: nunca borra ni pisa
    los retos propios del grupo.
    """
    grupo = grupos_svc.get_por_id(id_grupo)
    if grupo is None:
        raise ValueError("Grupo no encontrado")
    if not grupos_svc.es_admin(grupo, id_usuario_actor):
        raise PermissionError("Solo un admin del grupo puede traer los retos que faltan")

    existentes = {_clave(r["texto"]) for r in listar(id_grupo)}
    faltantes = [
        (new_id("R"), id_grupo, texto, dificultad, categoria)
        for texto, dificultad, categoria in DEFAULT_RETOS
        if _clave(texto) not in existentes
    ]
    if faltantes:
        db.execute_many(
            "INSERT INTO retos (id, id_grupo, texto, dificultad, categoria) VALUES (%s, %s, %s, %s, %s)",
            faltantes,
        )
    return len(faltantes)


def eliminar(id_grupo: str, id_reto: str, id_usuario_actor: str) -> None:
    """Saca un reto de la baraja del grupo.

    Solo admins: los retos no guardan quién los creó (los que vienen por
    defecto no son de nadie), así que no hay a quién más darle el permiso sin
    dejar que cualquiera le vacíe la baraja al grupo.
    """
    row = db.fetch_one("SELECT * FROM retos WHERE id = %s AND id_grupo = %s", (id_reto, id_grupo))
    if row is None:
        raise ValueError("Reto no encontrado en este grupo")

    grupo = grupos_svc.get_por_id(id_grupo)
    if grupo is None:
        raise ValueError("Grupo no encontrado")
    if not grupos_svc.es_admin(grupo, id_usuario_actor):
        raise PermissionError("Solo un admin del grupo puede borrar retos")

    db.execute("DELETE FROM retos WHERE id = %s", (id_reto,))
