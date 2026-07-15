"""Lógica de negocio de Usuarios. Cada usuario pertenece a un único grupo:
el mismo nombre en dos grupos distintos genera dos filas independientes.
"""
from .. import db
from .ids import new_id


def _row_to_out(row: dict) -> dict:
    return {
        "id": row["id"],
        "nombre": row["nombre"],
        "foto": row["foto"],
        "puntos_totales": row["puntos_totales"],
        "sesiones_jugadas": row["sesiones_jugadas"],
    }


def listar(id_grupo: str) -> list[dict]:
    rows = db.fetch_all("SELECT * FROM usuarios WHERE id_grupo = %s", (id_grupo,))
    return [_row_to_out(r) for r in rows]


def get_por_id(id_grupo: str, id_usuario: str) -> dict | None:
    row = db.fetch_one("SELECT * FROM usuarios WHERE id = %s AND id_grupo = %s", (id_usuario, id_grupo))
    return _row_to_out(row) if row else None


def get_or_create(id_grupo: str, nombre: str, foto: str = "") -> dict:
    """Busca un usuario por nombre dentro del grupo (sin distinguir
    mayúsculas); lo crea si no existe."""
    nombre = nombre.strip()
    row = db.fetch_one(
        "SELECT * FROM usuarios WHERE id_grupo = %s AND lower(nombre) = lower(%s)",
        (id_grupo, nombre),
    )
    if row:
        return _row_to_out(row)
    id_usuario = new_id("U")
    db.execute(
        "INSERT INTO usuarios (id, id_grupo, nombre, foto, puntos_totales, sesiones_jugadas) "
        "VALUES (%s, %s, %s, %s, 0, 0)",
        (id_usuario, id_grupo, nombre, foto),
    )
    return {"id": id_usuario, "nombre": nombre, "foto": foto, "puntos_totales": 0, "sesiones_jugadas": 0}


def sumar_puntos(id_usuario: str, puntos: int) -> None:
    db.execute("UPDATE usuarios SET puntos_totales = puntos_totales + %s WHERE id = %s", (puntos, id_usuario))


def eliminar(id_grupo: str, id_usuario: str) -> None:
    row = db.fetch_one("SELECT id FROM usuarios WHERE id = %s AND id_grupo = %s", (id_usuario, id_grupo))
    if row is None:
        raise ValueError("Usuario no encontrado en este grupo")
    db.execute("DELETE FROM usuarios WHERE id = %s", (id_usuario,))


def incrementar_sesiones(id_usuario: str) -> None:
    db.execute("UPDATE usuarios SET sesiones_jugadas = sesiones_jugadas + 1 WHERE id = %s", (id_usuario,))
