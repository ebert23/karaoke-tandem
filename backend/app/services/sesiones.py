"""Lógica de negocio de Sesiones de karaoke: turnos, cola, selección de
canción, participantes en vivo, votación en tiempo real, marcar cantada /
saltar y cierre e historial.
"""
import random

from .. import db
from . import canciones as canciones_svc
from . import grupos as grupos_svc
from . import usuarios as usuarios_svc
from .ids import new_id, now_iso


def _sesion_row_to_out(row: dict) -> dict:
    return {
        "id_sesion": row["id_sesion"],
        "fecha": row["fecha"],
        "participantes": row["participantes"],
        "estado": row["estado"],
        "turno_actual": row["turno_actual"],
    }


def crear(id_grupo: str, participantes: list[str]) -> dict:
    nombres = [p.strip() for p in participantes if p.strip()]
    if not nombres:
        raise ValueError("Se necesita al menos un participante")
    for nombre in nombres:
        usuario = usuarios_svc.get_or_create(id_grupo, nombre)
        usuarios_svc.incrementar_sesiones(usuario["id"])

    id_sesion = new_id("S")
    fecha = now_iso()
    db.execute(
        "INSERT INTO sesiones (id_sesion, id_grupo, fecha, participantes, estado, turno_actual) "
        "VALUES (%s, %s, %s, %s, 'Activa', 0)",
        (id_sesion, id_grupo, fecha, nombres),
    )
    return {"id_sesion": id_sesion, "fecha": fecha, "participantes": nombres, "estado": "Activa", "turno_actual": 0}


def get_activa(id_grupo: str) -> dict | None:
    row = db.fetch_one(
        "SELECT * FROM sesiones WHERE id_grupo = %s AND estado = 'Activa' ORDER BY fecha DESC LIMIT 1",
        (id_grupo,),
    )
    return _sesion_row_to_out(row) if row else None


def get_por_id(id_grupo: str, id_sesion: str) -> dict | None:
    row = db.fetch_one("SELECT * FROM sesiones WHERE id_sesion = %s", (id_sesion,))
    if row is None or row["id_grupo"] != id_grupo:
        return None
    return _sesion_row_to_out(row)


def unirse(id_grupo: str, id_sesion: str, nombre: str) -> dict:
    sesion_row = db.fetch_one("SELECT * FROM sesiones WHERE id_sesion = %s", (id_sesion,))
    if sesion_row is None or sesion_row["id_grupo"] != id_grupo:
        raise ValueError("Sesión no encontrada")
    if sesion_row["estado"] != "Activa":
        raise ValueError("La sesión no está activa")

    nombre = nombre.strip()
    usuario = usuarios_svc.get_or_create(id_grupo, nombre)
    usuarios_svc.incrementar_sesiones(usuario["id"])

    participantes = sesion_row["participantes"]
    if nombre.lower() not in [p.lower() for p in participantes]:
        participantes = participantes + [nombre]
        db.execute("UPDATE sesiones SET participantes = %s WHERE id_sesion = %s", (participantes, id_sesion))
        sesion_row["participantes"] = participantes
    return _sesion_row_to_out(sesion_row)


def quitar_participante(id_grupo: str, id_sesion: str, nombre: str) -> None:
    """Saca a alguien de la lista de participantes en vivo de una sesión
    (p.ej. al expulsarlo del grupo). No toca turnos ya jugados — esos
    quedan como registro histórico."""
    row = db.fetch_one("SELECT * FROM sesiones WHERE id_sesion = %s", (id_sesion,))
    if row is None or row["id_grupo"] != id_grupo:
        return
    nombre_lower = nombre.strip().lower()
    nuevos = [p for p in row["participantes"] if p.lower() != nombre_lower]
    if nuevos != row["participantes"]:
        db.execute("UPDATE sesiones SET participantes = %s WHERE id_sesion = %s", (nuevos, id_sesion))


def _turno_to_out(row: dict, incluir_cancion: bool = True) -> dict:
    return {
        "id_sesion": row["id_sesion"],
        "id_cancion": row["id_cancion"],
        "turno": row["turno"],
        "cantada_por": row["cantada_por"],
        "puntuacion": row["puntuacion"],
        "estado": row["estado"],
        "cancion": canciones_svc.get_por_id(row["id_cancion"]) if incluir_cancion else None,
    }


def agregar_a_cola(id_grupo: str, id_sesion: str, id_cancion: str, cantantes: list[str] | None = None) -> dict:
    sesion_row = db.fetch_one("SELECT * FROM sesiones WHERE id_sesion = %s", (id_sesion,))
    if sesion_row is None or sesion_row["id_grupo"] != id_grupo:
        raise ValueError("Sesión no encontrada")
    if sesion_row["estado"] != "Activa":
        raise ValueError("La sesión no está activa")

    turnos_previos = db.fetch_all("SELECT id_cancion, estado FROM canciones_sesion WHERE id_sesion = %s", (id_sesion,))
    ids_usadas = {t["id_cancion"] for t in turnos_previos if t["estado"] in ("Pendiente", "Cantada", "En cola")}
    if id_cancion in ids_usadas:
        raise ValueError("Esa canción ya está en la sesión (cantada, pendiente o en cola)")

    # Si se eligen cantantes a mano (dueto/grupal o "quiero que cante X"), se
    # guardan ya en la fila de cola; si no, queda vacío y "siguiente" asigna
    # por rotación al promoverla.
    nombres = [n.strip() for n in (cantantes or []) if n.strip()]
    cantada_por = ", ".join(nombres)

    siguiente_orden = db.fetch_one(
        "SELECT COALESCE(MAX(orden), 0) + 1 AS n FROM canciones_sesion WHERE id_sesion = %s AND estado = 'En cola'",
        (id_sesion,),
    )["n"]

    row = db.fetch_one(
        "INSERT INTO canciones_sesion (id_sesion, id_grupo, id_cancion, orden, turno, cantada_por, puntuacion, estado) "
        "VALUES (%s, %s, %s, %s, 0, %s, NULL, 'En cola') RETURNING *",
        (id_sesion, id_grupo, id_cancion, siguiente_orden, cantada_por),
    )
    return _turno_to_out(row)


def _requiere_admin(id_grupo: str, id_usuario_actor: str) -> None:
    grupo = grupos_svc.get_por_id(id_grupo)
    if grupo is None:
        raise ValueError("Grupo no encontrado")
    if not grupos_svc.es_admin(grupo, id_usuario_actor):
        raise PermissionError("Solo un admin puede modificar la cola")


def quitar_de_cola(id_grupo: str, id_sesion: str, id_cancion: str, id_usuario_actor: str) -> None:
    _requiere_admin(id_grupo, id_usuario_actor)
    row = _fila_turno(id_sesion, id_cancion)
    if row is None or row["id_grupo"] != id_grupo:
        raise ValueError("Canción no encontrada en la sesión")
    if row["estado"] != "En cola":
        raise ValueError("Esa canción ya no está en la cola (ya se promovió o se cantó)")
    db.execute("DELETE FROM canciones_sesion WHERE id = %s", (row["id"],))


def mover_en_cola(id_grupo: str, id_sesion: str, id_cancion: str, id_usuario_actor: str, direccion: str) -> list[dict]:
    """Reordena la cola intercambiando la posición ("orden") de dos filas
    vecinas — mucho más simple que el truco de Sheets de simular el orden
    con la posición física de las filas."""
    _requiere_admin(id_grupo, id_usuario_actor)
    filas_cola = db.fetch_all(
        "SELECT * FROM canciones_sesion WHERE id_sesion = %s AND estado = 'En cola' ORDER BY orden ASC, id ASC",
        (id_sesion,),
    )
    posicion = next((i for i, row in enumerate(filas_cola) if row["id_cancion"] == id_cancion), None)
    if posicion is None:
        raise ValueError("Canción no encontrada en la cola")

    vecino = posicion - 1 if direccion == "arriba" else posicion + 1
    if vecino < 0 or vecino >= len(filas_cola):
        raise ValueError("Esa canción ya está en un extremo de la cola")

    fila_a, fila_b = filas_cola[posicion], filas_cola[vecino]
    db.execute("UPDATE canciones_sesion SET orden = %s WHERE id = %s", (fila_b["orden"], fila_a["id"]))
    db.execute("UPDATE canciones_sesion SET orden = %s WHERE id = %s", (fila_a["orden"], fila_b["id"]))
    fila_a["orden"], fila_b["orden"] = fila_b["orden"], fila_a["orden"]

    filas_cola.sort(key=lambda r: (r["orden"], r["id"]))
    return [_turno_to_out(r) for r in filas_cola]


def siguiente_cancion(id_grupo: str, id_sesion: str, id_usuario_actor: str) -> dict:
    _requiere_admin(id_grupo, id_usuario_actor)
    sesion_row = db.fetch_one("SELECT * FROM sesiones WHERE id_sesion = %s", (id_sesion,))
    if sesion_row is None or sesion_row["id_grupo"] != id_grupo:
        raise ValueError("Sesión no encontrada")
    if sesion_row["estado"] != "Activa":
        raise ValueError("La sesión no está activa")

    # Si dos clics de "siguiente" llegan casi juntos (dos personas con
    # permiso, o un doble clic) ya no se crean dos turnos "Pendiente" en
    # paralelo — el segundo llamado simplemente recibe el que ya quedó
    # armado, así todos terminan viendo la misma canción.
    pendiente_existente = db.fetch_one(
        "SELECT * FROM canciones_sesion WHERE id_sesion = %s AND estado = 'Pendiente' ORDER BY id DESC LIMIT 1",
        (id_sesion,),
    )
    if pendiente_existente is not None:
        return _turno_to_out(pendiente_existente)

    turnos_previos = db.fetch_all("SELECT id_cancion, estado FROM canciones_sesion WHERE id_sesion = %s", (id_sesion,))
    turno_actual = sesion_row["turno_actual"]
    participantes = sesion_row["participantes"]
    if not participantes:
        raise ValueError("La sesión no tiene participantes")
    cantante = participantes[turno_actual % len(participantes)]

    cola_row = db.fetch_one(
        "SELECT * FROM canciones_sesion WHERE id_sesion = %s AND estado = 'En cola' ORDER BY orden ASC, id ASC LIMIT 1",
        (id_sesion,),
    )
    if cola_row is not None:
        nuevo_turno = len(turnos_previos) + 1
        # Si la fila ya trae cantante(s) elegidos a mano (dueto/grupal), se
        # respetan; si no, se asigna por rotación como siempre.
        cantante_final = cola_row["cantada_por"] or cantante
        db.execute(
            "UPDATE canciones_sesion SET turno = %s, cantada_por = %s, estado = 'Pendiente' WHERE id = %s",
            (nuevo_turno, cantante_final, cola_row["id"]),
        )
        db.execute("UPDATE sesiones SET turno_actual = %s WHERE id_sesion = %s", (turno_actual + 1, id_sesion))
        cola_row.update({"turno": nuevo_turno, "cantada_por": cantante_final, "estado": "Pendiente"})
        return _turno_to_out(cola_row)

    ids_usadas = {t["id_cancion"] for t in turnos_previos if t["estado"] in ("Pendiente", "Cantada", "En cola")}
    todas = canciones_svc.listar(id_grupo)
    disponibles = [c for c in todas if c["id"] not in ids_usadas]
    if not disponibles:
        raise ValueError("No quedan canciones disponibles en la lista")

    elegida = random.choice(disponibles)
    nuevo_turno = len(turnos_previos) + 1
    row = db.fetch_one(
        "INSERT INTO canciones_sesion (id_sesion, id_grupo, id_cancion, orden, turno, cantada_por, puntuacion, estado) "
        "VALUES (%s, %s, %s, 0, %s, %s, NULL, 'Pendiente') RETURNING *",
        (id_sesion, id_grupo, elegida["id"], nuevo_turno, cantante),
    )
    db.execute("UPDATE sesiones SET turno_actual = %s WHERE id_sesion = %s", (turno_actual + 1, id_sesion))
    return _turno_to_out(row)


def _turno_pendiente(id_sesion: str, id_cancion: str) -> dict:
    row = db.fetch_one(
        "SELECT * FROM canciones_sesion WHERE id_sesion = %s AND id_cancion = %s AND estado = 'Pendiente' "
        "ORDER BY id ASC LIMIT 1",
        (id_sesion, id_cancion),
    )
    if row is None:
        raise ValueError("No hay un turno pendiente para esa canción en esta sesión")
    return row


def _fila_turno(id_sesion: str, id_cancion: str) -> dict | None:
    return db.fetch_one(
        "SELECT * FROM canciones_sesion WHERE id_sesion = %s AND id_cancion = %s ORDER BY id ASC LIMIT 1",
        (id_sesion, id_cancion),
    )


def votar_turno(id_grupo: str, id_sesion: str, id_cancion: str, id_usuario: str, puntuacion: int) -> dict:
    turno_row = _fila_turno(id_sesion, id_cancion)
    if turno_row is None or turno_row["id_grupo"] != id_grupo:
        raise ValueError("Turno no encontrado")
    if turno_row["estado"] != "Pendiente":
        raise ValueError("Ya no se puede votar esta interpretación")

    db.execute(
        "INSERT INTO votos_turno (id_grupo, id_sesion, id_cancion, turno, id_usuario, puntuacion, fecha) "
        "VALUES (%s, %s, %s, %s, %s, %s, %s) "
        "ON CONFLICT (id_sesion, id_cancion, turno, id_usuario) DO UPDATE SET puntuacion = EXCLUDED.puntuacion",
        (id_grupo, id_sesion, id_cancion, turno_row["turno"], id_usuario, puntuacion, now_iso()),
    )
    return votos_turno(id_grupo, id_sesion, id_cancion)


def votos_turno(id_grupo: str, id_sesion: str, id_cancion: str) -> dict:
    turno_row = _fila_turno(id_sesion, id_cancion)
    if turno_row is None or turno_row["id_grupo"] != id_grupo:
        raise ValueError("Turno no encontrado")

    filas = db.fetch_all(
        "SELECT id_usuario, puntuacion FROM votos_turno WHERE id_sesion = %s AND id_cancion = %s AND turno = %s",
        (id_sesion, id_cancion, turno_row["turno"]),
    )
    votos = [{"id_usuario": v["id_usuario"], "puntuacion": v["puntuacion"]} for v in filas]
    promedio = round(sum(v["puntuacion"] for v in votos) / len(votos), 2) if votos else None
    return {"votos": votos, "promedio": promedio}


def marcar_cantada(id_grupo: str, id_sesion: str, id_cancion: str, puntuacion: int | None) -> dict:
    row = _turno_pendiente(id_sesion, id_cancion)
    if row["id_grupo"] != id_grupo:
        raise ValueError("No hay un turno pendiente para esa canción en esta sesión")

    votos_info = votos_turno(id_grupo, id_sesion, id_cancion)
    if votos_info["promedio"] is not None:
        puntuacion_final = round(votos_info["promedio"])
    elif puntuacion is not None:
        puntuacion_final = puntuacion
    else:
        raise ValueError("Falta la puntuación: nadie votó esta interpretación todavía")

    db.execute(
        "UPDATE canciones_sesion SET puntuacion = %s, estado = 'Cantada' WHERE id = %s",
        (puntuacion_final, row["id"]),
    )
    canciones_svc.registrar_cantada(id_cancion)

    # Un turno puede tener varios cantantes (dueto/grupal) separados por
    # coma en "Cantada por" — cada uno recibe el puntaje completo, no
    # repartido entre todos.
    for nombre in [n.strip() for n in row["cantada_por"].split(",") if n.strip()]:
        usuario = usuarios_svc.get_or_create(id_grupo, nombre)
        usuarios_svc.sumar_puntos(usuario["id"], puntuacion_final)

    row["puntuacion"] = puntuacion_final
    row["estado"] = "Cantada"
    return _turno_to_out(row)


def saltar(id_grupo: str, id_sesion: str, id_cancion: str) -> dict:
    row = _turno_pendiente(id_sesion, id_cancion)
    if row["id_grupo"] != id_grupo:
        raise ValueError("No hay un turno pendiente para esa canción en esta sesión")
    db.execute("UPDATE canciones_sesion SET estado = 'Saltada' WHERE id = %s", (row["id"],))
    row["estado"] = "Saltada"
    return _turno_to_out(row)


def finalizar(id_grupo: str, id_sesion: str) -> dict:
    row = db.fetch_one("SELECT * FROM sesiones WHERE id_sesion = %s", (id_sesion,))
    if row is None or row["id_grupo"] != id_grupo:
        raise ValueError("Sesión no encontrada")
    db.execute("UPDATE sesiones SET estado = 'Finalizada' WHERE id_sesion = %s", (id_sesion,))
    row["estado"] = "Finalizada"
    return _sesion_row_to_out(row)


def historial(id_grupo: str) -> list[dict]:
    rows = db.fetch_all("SELECT * FROM sesiones WHERE id_grupo = %s ORDER BY fecha DESC", (id_grupo,))
    return [_sesion_row_to_out(r) for r in rows]


def detalle(id_grupo: str, id_sesion: str) -> list[dict]:
    rows = db.fetch_all(
        "SELECT * FROM canciones_sesion WHERE id_sesion = %s AND id_grupo = %s "
        "ORDER BY turno ASC, orden ASC, id ASC",
        (id_sesion, id_grupo),
    )
    return [_turno_to_out(r) for r in rows]
