"""Lógica de negocio de Grupos/Salas: crear, unirse por código, detalle."""
import random

from .. import db
from . import retos as retos_svc
from . import usuarios as usuarios_svc
from .ids import new_id, now_iso


def _row_to_out(row: dict) -> dict:
    return {
        "id": row["id"],
        "nombre": row["nombre"],
        "codigo": row["codigo"],
        "foto": row["foto"],
        "admins": row["admins"],
        "fecha_creacion": row["fecha_creacion"],
    }


def _codigo_unico() -> str:
    existentes = {r["codigo"] for r in db.fetch_all("SELECT codigo FROM grupos")}
    while True:
        codigo = f"{random.randint(0, 999999):06d}"
        if codigo not in existentes:
            return codigo


def crear(nombre: str, foto: str = "", creado_por_nombre: str = "") -> dict:
    id_grupo = new_id("G")
    codigo = _codigo_unico()
    fecha_creacion = now_iso()

    # El grupo tiene que existir antes de crear su primer usuario (FK
    # usuarios.id_grupo -> grupos.id), así que se inserta vacío de admins
    # primero y se completa después de crear al admin.
    db.execute(
        "INSERT INTO grupos (id, nombre, codigo, foto, admins, fecha_creacion) "
        "VALUES (%s, %s, %s, %s, %s, %s)",
        (id_grupo, nombre.strip(), codigo, foto.strip(), [], fecha_creacion),
    )
    retos_svc.seed_default_retos(id_grupo)

    admin_id = ""
    if creado_por_nombre.strip():
        usuario = usuarios_svc.get_or_create(id_grupo, creado_por_nombre.strip())
        admin_id = usuario["id"]

    admins = [admin_id] if admin_id else []
    if admins:
        db.execute("UPDATE grupos SET admins = %s WHERE id = %s", (admins, id_grupo))

    return {
        "id": id_grupo,
        "nombre": nombre.strip(),
        "codigo": codigo,
        "foto": foto.strip(),
        "admins": admins,
        "fecha_creacion": fecha_creacion,
    }


def unirse_por_codigo(codigo: str) -> dict | None:
    row = db.fetch_one("SELECT * FROM grupos WHERE codigo = %s", (codigo.strip(),))
    return _row_to_out(row) if row else None


def get_por_id(id_grupo: str) -> dict | None:
    row = db.fetch_one("SELECT * FROM grupos WHERE id = %s", (id_grupo,))
    return _row_to_out(row) if row else None


def es_admin(grupo: dict, id_usuario: str) -> bool:
    return id_usuario in grupo["admins"]


def reclamar_admin(id_grupo: str, id_usuario: str) -> dict:
    """Válvula de escape para grupos sin ningún admin (p.ej. uno migrado de
    antes de que existiera este rol): el primer miembro que la pide se
    convierte en admin. Deja de estar disponible en cuanto el grupo ya
    tiene un admin."""
    grupo = get_por_id(id_grupo)
    if grupo is None:
        raise ValueError("Grupo no encontrado")
    if grupo["admins"]:
        raise PermissionError("Este grupo ya tiene un admin; pedile que te otorgue el rol")
    if usuarios_svc.get_por_id(id_grupo, id_usuario) is None:
        raise ValueError("Usuario no encontrado en este grupo")
    db.execute("UPDATE grupos SET admins = %s WHERE id = %s", ([id_usuario], id_grupo))
    grupo["admins"] = [id_usuario]
    grupo["miembros"] = usuarios_svc.listar(id_grupo)
    return grupo


def hacer_admin(id_grupo: str, id_usuario_actor: str, id_usuario_objetivo: str) -> dict:
    grupo = get_por_id(id_grupo)
    if grupo is None:
        raise ValueError("Grupo no encontrado")
    if not es_admin(grupo, id_usuario_actor):
        raise PermissionError("Solo un admin puede otorgar el rol de admin")
    if usuarios_svc.get_por_id(id_grupo, id_usuario_objetivo) is None:
        raise ValueError("Usuario no encontrado en este grupo")
    if id_usuario_objetivo not in grupo["admins"]:
        nuevos_admins = grupo["admins"] + [id_usuario_objetivo]
        db.execute("UPDATE grupos SET admins = %s WHERE id = %s", (nuevos_admins, id_grupo))
        grupo["admins"] = nuevos_admins
    grupo["miembros"] = usuarios_svc.listar(id_grupo)
    return grupo


def quitar_admin(id_grupo: str, id_usuario_actor: str, id_usuario_objetivo: str) -> dict:
    grupo = get_por_id(id_grupo)
    if grupo is None:
        raise ValueError("Grupo no encontrado")
    if not es_admin(grupo, id_usuario_actor):
        raise PermissionError("Solo un admin puede quitar el rol de admin")
    if id_usuario_objetivo in grupo["admins"]:
        if len(grupo["admins"]) == 1:
            raise ValueError("No podés quitar al último admin del grupo")
        nuevos_admins = [a for a in grupo["admins"] if a != id_usuario_objetivo]
        db.execute("UPDATE grupos SET admins = %s WHERE id = %s", (nuevos_admins, id_grupo))
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
