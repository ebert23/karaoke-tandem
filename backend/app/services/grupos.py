"""Lógica de negocio de Grupos/Salas: crear, unirse por código, detalle.

Un grupo es también un "local" cuando su modo es 'salon' (ver schema.sql): las
dos experiencias comparten catálogo, sesión y cola, y solo cambia quién maneja
la rotación y cómo se reparten los turnos.
"""
import random
import secrets

from .. import db
from . import retos as retos_svc
from . import usuarios as usuarios_svc
from .ids import new_id, now_iso

MODOS = ("grupo", "salon")


def _row_to_out(row: dict) -> dict:
    return {
        "id": row["id"],
        "nombre": row["nombre"],
        "codigo": row["codigo"],
        "foto": row["foto"],
        "admins": row["admins"],
        "fecha_creacion": row["fecha_creacion"],
        # .get() y no [] porque _row_to_out también recibe dicts armados a
        # mano en los tests y en crear().
        "modo": row.get("modo", "grupo"),
    }


def _codigo_unico() -> str:
    existentes = {r["codigo"] for r in db.fetch_all("SELECT codigo FROM grupos")}
    while True:
        codigo = f"{random.randint(0, 999999):06d}"
        if codigo not in existentes:
            return codigo


def _codigo_dj_nuevo() -> str:
    """Secreto de la vista del DJ.

    Largo a propósito: es lo único que separa a cualquiera de los controles de
    la noche. Aun así NO es autenticación (ver deps.requiere_dj) — resuelve que
    la URL no sea adivinable, nada más.
    """
    return secrets.token_urlsafe(18)


def crear(nombre: str, foto: str = "", creado_por_nombre: str = "", modo: str = "grupo") -> dict:
    if modo not in MODOS:
        raise ValueError(f"Modo inválido: {modo}")
    id_grupo = new_id("G")
    codigo = _codigo_unico()
    fecha_creacion = now_iso()
    codigo_dj = _codigo_dj_nuevo() if modo == "salon" else ""

    # El grupo tiene que existir antes de crear su primer usuario (FK
    # usuarios.id_grupo -> grupos.id), así que se inserta vacío de admins
    # primero y se completa después de crear al admin.
    db.execute(
        "INSERT INTO grupos (id, nombre, codigo, foto, admins, fecha_creacion, modo, codigo_dj) "
        "VALUES (%s, %s, %s, %s, %s, %s, %s, %s)",
        (id_grupo, nombre.strip(), codigo, foto.strip(), [], fecha_creacion, modo, codigo_dj),
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
        "modo": modo,
    }


def get_codigo_dj(id_grupo: str) -> str:
    row = db.fetch_one("SELECT codigo_dj FROM grupos WHERE id = %s", (id_grupo,))
    return row["codigo_dj"] if row else ""


def por_codigo_dj(codigo: str) -> dict | None:
    """Resuelve el local a partir del código del DJ.

    Existe para que el DJ pueda entrar tipeando solo su código, en vez de
    abrir un link que lleve el secreto en la URL (donde queda en el historial
    del navegador y en los logs de cualquier proxy en el camino).
    """
    codigo = codigo.strip()
    if not codigo:
        return None
    row = db.fetch_one("SELECT * FROM grupos WHERE codigo_dj = %s AND modo = 'salon'", (codigo,))
    return _row_to_out(row) if row else None


def convertir_a_salon(id_grupo: str, id_usuario_actor: str) -> dict:
    """Pasa un grupo a modo salón y le genera su código de DJ.

    Es la puerta de entrada para un local: crea su grupo como siempre y lo
    convierte. Si ya estaba en modo salón se le devuelve el código que tenía,
    para que entrar dos veces no le invalide el que el DJ ya está usando.
    """
    grupo = get_por_id(id_grupo)
    if grupo is None:
        raise ValueError("Grupo no encontrado")
    if not es_admin(grupo, id_usuario_actor):
        raise PermissionError("Solo un admin puede convertir el grupo en local")

    codigo_dj = get_codigo_dj(id_grupo) or _codigo_dj_nuevo()
    db.execute("UPDATE grupos SET modo = 'salon', codigo_dj = %s WHERE id = %s", (codigo_dj, id_grupo))
    grupo["modo"] = "salon"
    grupo["codigo_dj"] = codigo_dj
    return grupo


def regenerar_codigo_dj(id_grupo: str, id_usuario_actor: str) -> dict:
    """Invalida el código del DJ y emite uno nuevo — para cuando se filtró o
    se fue el DJ que lo tenía."""
    grupo = get_por_id(id_grupo)
    if grupo is None:
        raise ValueError("Grupo no encontrado")
    if not es_admin(grupo, id_usuario_actor):
        raise PermissionError("Solo un admin puede regenerar el código del DJ")

    codigo_dj = _codigo_dj_nuevo()
    db.execute("UPDATE grupos SET codigo_dj = %s WHERE id = %s", (codigo_dj, id_grupo))
    grupo["codigo_dj"] = codigo_dj
    return grupo


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
