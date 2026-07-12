"""Lógica de negocio de Usuarios. Cada usuario pertenece a un único grupo:
el mismo nombre en dos grupos distintos genera dos filas independientes.
"""
from ..sheets_client import SheetTable
from .ids import new_id


def _table() -> SheetTable:
    return SheetTable("Usuarios")


def _row_to_out(row: dict) -> dict:
    return {
        "id": row["ID"],
        "nombre": row["Nombre"],
        "foto": row["Foto"],
        "puntos_totales": int(row["Puntos totales"] or 0),
        "sesiones_jugadas": int(row["Sesiones jugadas"] or 0),
    }


def listar(id_grupo: str) -> list[dict]:
    return [_row_to_out(r) for r in _table().all_rows() if r["ID Grupo"] == id_grupo]


def get_por_id(id_grupo: str, id_usuario: str) -> dict | None:
    _, row = _table().get_by_id("ID", id_usuario)
    if row is None or row["ID Grupo"] != id_grupo:
        return None
    return _row_to_out(row)


def get_or_create(id_grupo: str, nombre: str, foto: str = "") -> dict:
    """Busca un usuario por nombre dentro del grupo (sin distinguir
    mayúsculas); lo crea si no existe."""
    nombre = nombre.strip()
    tabla = _table()
    for r in tabla.all_rows():
        if r["ID Grupo"] == id_grupo and r["Nombre"].strip().lower() == nombre.lower():
            return _row_to_out(r)
    row = {
        "ID": new_id("U"),
        "ID Grupo": id_grupo,
        "Nombre": nombre,
        "Foto": foto,
        "Puntos totales": 0,
        "Sesiones jugadas": 0,
    }
    tabla.append(row)
    return _row_to_out(row)


def sumar_puntos(id_usuario: str, puntos: int) -> None:
    tabla = _table()
    row_number, row = tabla.get_by_id("ID", id_usuario)
    if row_number is None:
        return
    nuevo_total = int(row["Puntos totales"] or 0) + puntos
    tabla.update_row(row_number, {"Puntos totales": nuevo_total})


def eliminar(id_grupo: str, id_usuario: str) -> None:
    tabla = _table()
    row_number, row = tabla.get_by_id("ID", id_usuario)
    if row_number is None or row["ID Grupo"] != id_grupo:
        raise ValueError("Usuario no encontrado en este grupo")
    tabla.delete_row(row_number)


def incrementar_sesiones(id_usuario: str) -> None:
    tabla = _table()
    row_number, row = tabla.get_by_id("ID", id_usuario)
    if row_number is None:
        return
    nuevas = int(row["Sesiones jugadas"] or 0) + 1
    tabla.update_row(row_number, {"Sesiones jugadas": nuevas})
