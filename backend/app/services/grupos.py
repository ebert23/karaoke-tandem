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


def es_admin(grupo: dict, id_usuario: str) -> bool:
    return id_usuario in grupo["admins"]


def reclamar_admin(id_grupo: str, id_usuario: str) -> dict:
    """Válvula de escape para grupos sin ningún admin (p.ej. uno migrado de
    antes de que existiera este rol): el primer miembro que la pide se
    convierte en admin. Deja de estar disponible en cuanto el grupo ya
    tiene un admin."""
    row_number, row = _table().get_by_id("ID", id_grupo)
    if row_number is None:
        raise ValueError("Grupo no encontrado")
    grupo = _row_to_out(row)
    if grupo["admins"]:
        raise PermissionError("Este grupo ya tiene un admin; pedile que te otorgue el rol")
    if usuarios_svc.get_por_id(id_grupo, id_usuario) is None:
        raise ValueError("Usuario no encontrado en este grupo")
    _table().update_row(row_number, {"Admins": id_usuario})
    grupo["admins"] = [id_usuario]
    grupo["miembros"] = usuarios_svc.listar(id_grupo)
    return grupo


def hacer_admin(id_grupo: str, id_usuario_actor: str, id_usuario_objetivo: str) -> dict:
    row_number, row = _table().get_by_id("ID", id_grupo)
    if row_number is None:
        raise ValueError("Grupo no encontrado")
    grupo = _row_to_out(row)
    if not es_admin(grupo, id_usuario_actor):
        raise PermissionError("Solo un admin puede otorgar el rol de admin")
    if usuarios_svc.get_por_id(id_grupo, id_usuario_objetivo) is None:
        raise ValueError("Usuario no encontrado en este grupo")
    if id_usuario_objetivo not in grupo["admins"]:
        nuevos_admins = grupo["admins"] + [id_usuario_objetivo]
        _table().update_row(row_number, {"Admins": ",".join(nuevos_admins)})
        grupo["admins"] = nuevos_admins
    grupo["miembros"] = usuarios_svc.listar(id_grupo)
    return grupo


def quitar_admin(id_grupo: str, id_usuario_actor: str, id_usuario_objetivo: str) -> dict:
    row_number, row = _table().get_by_id("ID", id_grupo)
    if row_number is None:
        raise ValueError("Grupo no encontrado")
    grupo = _row_to_out(row)
    if not es_admin(grupo, id_usuario_actor):
        raise PermissionError("Solo un admin puede quitar el rol de admin")
    if id_usuario_objetivo in grupo["admins"]:
        if len(grupo["admins"]) == 1:
            raise ValueError("No podés quitar al último admin del grupo")
        nuevos_admins = [a for a in grupo["admins"] if a != id_usuario_objetivo]
        _table().update_row(row_number, {"Admins": ",".join(nuevos_admins)})
        grupo["admins"] = nuevos_admins
    grupo["miembros"] = usuarios_svc.listar(id_grupo)
    return grupo


def expulsar_miembro(id_grupo: str, id_usuario_actor: str, id_usuario_objetivo: str) -> dict:
    grupo = get_por_id(id_grupo)
    if grupo is None:
        raise ValueError("Grupo no encontrado")
    if not es_admin(grupo, id_usuario_actor):
        raise PermissionError("Solo un admin puede expulsar miembros")
    if id_usuario_objetivo in grupo["admins"]:
        raise ValueError("No podés expulsar a otro admin; primero quitale el rol de admin")
    usuarios_svc.eliminar(id_grupo, id_usuario_objetivo)
    grupo["miembros"] = usuarios_svc.listar(id_grupo)
    return grupo
