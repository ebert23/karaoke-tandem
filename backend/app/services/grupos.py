"""Lógica de negocio de Grupos/Salas: crear, unirse por código, detalle."""
from ..sheets_client import SheetTable
from . import retos as retos_svc
from . import usuarios as usuarios_svc
from .ids import new_id, now_iso


def _table() -> SheetTable:
    return SheetTable("Grupos")


def _row_to_out(row: dict) -> dict:
    admins = [a.strip() for a in row["Admins"].split(",") if a.strip()]
    return {
        "id": row["ID"],
        "nombre": row["Nombre"],
        "codigo": row["Código"],
        "foto": row["Foto"],
        "admins": admins,
        "fecha_creacion": row["Fecha creación"],
    }


def _codigo_unico() -> str:
    import random

    existentes = {r["Código"] for r in _table().all_rows()}
    while True:
        codigo = f"{random.randint(0, 999999):06d}"
        if codigo not in existentes:
            return codigo


def crear(nombre: str, foto: str = "", creado_por_nombre: str = "") -> dict:
    tabla = _table()
    id_grupo = new_id("G")
    codigo = _codigo_unico()

    admin_id = ""
    if creado_por_nombre.strip():
        usuario = usuarios_svc.get_or_create(id_grupo, creado_por_nombre.strip())
        admin_id = usuario["id"]

    row = {
        "ID": id_grupo,
        "Nombre": nombre.strip(),
        "Código": codigo,
        "Foto": foto.strip(),
        "Admins": admin_id,
        "Fecha creación": now_iso(),
    }
    tabla.append(row)
    retos_svc.seed_default_retos(id_grupo)
    return _row_to_out(row)


def unirse_por_codigo(codigo: str) -> dict | None:
    codigo = codigo.strip()
    for r in _table().all_rows():
        if r["Código"] == codigo:
            return _row_to_out(r)
    return None


def get_por_id(id_grupo: str) -> dict | None:
    _, row = _table().get_by_id("ID", id_grupo)
    return _row_to_out(row) if row else None
