"""Lógica de negocio de Sesiones de karaoke: turnos, cola, selección de
canción, participantes en vivo, votación en tiempo real, marcar cantada /
saltar y cierre e historial.
"""
import random

from ..sheets_client import SheetTable
from . import canciones as canciones_svc
from . import usuarios as usuarios_svc
from .ids import new_id, now_iso


def _sesiones() -> SheetTable:
    return SheetTable("Sesiones")


def _cs() -> SheetTable:
    return SheetTable("Canciones_Sesion")


def _votos_turno() -> SheetTable:
    return SheetTable("Votos_Turno")


def _sesion_row_to_out(row: dict) -> dict:
    return {
        "id_sesion": row["ID Sesión"],
        "fecha": row["Fecha"],
        "participantes": [p.strip() for p in row["Participantes"].split(",") if p.strip()],
        "estado": row["Estado"],
        "turno_actual": int(row["Turno actual"] or 0),
    }


def crear(id_grupo: str, participantes: list[str]) -> dict:
    nombres = [p.strip() for p in participantes if p.strip()]
    if not nombres:
        raise ValueError("Se necesita al menos un participante")
    for nombre in nombres:
        usuario = usuarios_svc.get_or_create(id_grupo, nombre)
        usuarios_svc.incrementar_sesiones(usuario["id"])

    row = {
        "ID Sesión": new_id("S"),
        "ID Grupo": id_grupo,
        "Fecha": now_iso(),
        "Participantes": ", ".join(nombres),
        "Estado": "Activa",
        "Turno actual": 0,
    }
    _sesiones().append(row)
    return _sesion_row_to_out(row)


def get_activa(id_grupo: str) -> dict | None:
    activas = [r for r in _sesiones().all_rows() if r["ID Grupo"] == id_grupo and r["Estado"] == "Activa"]
    if not activas:
        return None
    return _sesion_row_to_out(activas[-1])


def get_por_id(id_grupo: str, id_sesion: str) -> dict | None:
    _, row = _sesiones().get_by_id("ID Sesión", id_sesion)
    if row is None or row["ID Grupo"] != id_grupo:
        return None
    return _sesion_row_to_out(row)


def unirse(id_grupo: str, id_sesion: str, nombre: str) -> dict:
    row_number, sesion_row = _sesiones().get_by_id("ID Sesión", id_sesion)
    if sesion_row is None or sesion_row["ID Grupo"] != id_grupo:
        raise ValueError("Sesión no encontrada")
    if sesion_row["Estado"] != "Activa":
        raise ValueError("La sesión no está activa")

    nombre = nombre.strip()
    usuario = usuarios_svc.get_or_create(id_grupo, nombre)
    usuarios_svc.incrementar_sesiones(usuario["id"])

    participantes = [p.strip() for p in sesion_row["Participantes"].split(",") if p.strip()]
    if nombre.lower() not in [p.lower() for p in participantes]:
        participantes.append(nombre)
        _sesiones().update_row(row_number, {"Participantes": ", ".join(participantes)})
        sesion_row["Participantes"] = ", ".join(participantes)
    return _sesion_row_to_out(sesion_row)


def _turnos_de_sesion(id_sesion: str) -> list[dict]:
    return [r for r in _cs().all_rows() if r["ID Sesión"] == id_sesion]


def _turno_to_out(row: dict, incluir_cancion: bool = True) -> dict:
    out = {
        "id_sesion": row["ID Sesión"],
        "id_cancion": row["ID Canción"],
        "turno": int(row["Turno"] or 0),
        "cantada_por": row["Cantada por"],
        "puntuacion": int(row["Puntuación"]) if str(row["Puntuación"]).strip().isdigit() else None,
        "estado": row["Estado"],
        "cancion": canciones_svc.get_por_id(row["ID Canción"]) if incluir_cancion else None,
    }
    return out


def _primera_fila_en_cola(id_sesion: str) -> tuple[int, dict] | tuple[None, None]:
    for i, row in enumerate(_cs().all_rows()):
        if row["ID Sesión"] == id_sesion and row["Estado"] == "En cola":
            return i + 2, row  # +2: fila 1 es encabezado, all_rows es 0-indexado
    return None, None


def agregar_a_cola(id_grupo: str, id_sesion: str, id_cancion: str, cantantes: list[str] | None = None) -> dict:
    _, sesion_row = _sesiones().get_by_id("ID Sesión", id_sesion)
    if sesion_row is None or sesion_row["ID Grupo"] != id_grupo:
        raise ValueError("Sesión no encontrada")
    if sesion_row["Estado"] != "Activa":
        raise ValueError("La sesión no está activa")

    turnos_previos = _turnos_de_sesion(id_sesion)
    ids_usadas = {t["ID Canción"] for t in turnos_previos if t["Estado"] in ("Pendiente", "Cantada", "En cola")}
    if id_cancion in ids_usadas:
        raise ValueError("Esa canción ya está en la sesión (cantada, pendiente o en cola)")

    # Si se eligen cantantes a mano (dueto/grupal o "quiero que cante X"), se
    # guardan ya en la fila de cola; si no, queda vacío y "siguiente" asigna
    # por rotación al promoverla.
    nombres = [n.strip() for n in (cantantes or []) if n.strip()]
    row = {
        "ID Sesión": id_sesion,
        "ID Grupo": id_grupo,
        "ID Canción": id_cancion,
        "Turno": 0,
        "Cantada por": ", ".join(nombres),
        "Puntuación": "",
        "Estado": "En cola",
    }
    _cs().append(row)
    return _turno_to_out(row)


def siguiente_cancion(id_grupo: str, id_sesion: str) -> dict:
    sesion_row_number, sesion_row = _sesiones().get_by_id("ID Sesión", id_sesion)
    if sesion_row is None or sesion_row["ID Grupo"] != id_grupo:
        raise ValueError("Sesión no encontrada")
    if sesion_row["Estado"] != "Activa":
        raise ValueError("La sesión no está activa")

    sesion = _sesion_row_to_out(sesion_row)
    turnos_previos = _turnos_de_sesion(id_sesion)
    turno_actual = sesion["turno_actual"]
    participantes = sesion["participantes"]
    if not participantes:
        raise ValueError("La sesión no tiene participantes")
    cantante = participantes[turno_actual % len(participantes)]

    cola_row_number, cola_row = _primera_fila_en_cola(id_sesion)
    if cola_row is not None:
        nuevo_turno = len(turnos_previos) + 1
        # Si la fila ya trae cantante(s) elegidos a mano (dueto/grupal), se
        # respetan; si no, se asigna por rotación como siempre.
        cantante_final = cola_row["Cantada por"] or cantante
        _cs().update_row(cola_row_number, {"Turno": nuevo_turno, "Cantada por": cantante_final, "Estado": "Pendiente"})
        cola_row["Turno"] = nuevo_turno
        cola_row["Cantada por"] = cantante_final
        cola_row["Estado"] = "Pendiente"
        _sesiones().update_row(sesion_row_number, {"Turno actual": turno_actual + 1})
        return _turno_to_out(cola_row)

    ids_usadas = {t["ID Canción"] for t in turnos_previos if t["Estado"] in ("Pendiente", "Cantada", "En cola")}
    todas = canciones_svc.listar(id_grupo)
    disponibles = [c for c in todas if c["id"] not in ids_usadas]
    if not disponibles:
        raise ValueError("No quedan canciones disponibles en la lista")

    elegida = random.choice(disponibles)

    row = {
        "ID Sesión": id_sesion,
        "ID Grupo": id_grupo,
        "ID Canción": elegida["id"],
        "Turno": len(turnos_previos) + 1,
        "Cantada por": cantante,
        "Puntuación": "",
        "Estado": "Pendiente",
    }
    _cs().append(row)
    _sesiones().update_row(sesion_row_number, {"Turno actual": turno_actual + 1})

    return _turno_to_out(row)


def _turno_pendiente(id_sesion: str, id_cancion: str) -> tuple[int, dict]:
    for i, row in enumerate(_cs().all_rows()):
        if row["ID Sesión"] == id_sesion and row["ID Canción"] == id_cancion and row["Estado"] == "Pendiente":
            return i + 2, row  # +2: fila 1 es encabezado, all_rows es 0-indexado
    raise ValueError("No hay un turno pendiente para esa canción en esta sesión")


def _fila_turno(id_sesion: str, id_cancion: str) -> tuple[int, dict] | tuple[None, None]:
    for i, row in enumerate(_cs().all_rows()):
        if row["ID Sesión"] == id_sesion and row["ID Canción"] == id_cancion:
            return i + 2, row
    return None, None


def votar_turno(id_grupo: str, id_sesion: str, id_cancion: str, id_usuario: str, puntuacion: int) -> dict:
    _, turno_row = _fila_turno(id_sesion, id_cancion)
    if turno_row is None or turno_row["ID Grupo"] != id_grupo:
        raise ValueError("Turno no encontrado")
    if turno_row["Estado"] != "Pendiente":
        raise ValueError("Ya no se puede votar esta interpretación")
    turno = int(turno_row["Turno"] or 0)

    tabla = _votos_turno()
    existente_row_number = None
    for i, v in enumerate(tabla.all_rows()):
        if v["ID Sesión"] == id_sesion and v["ID Canción"] == id_cancion and str(v["Turno"]) == str(turno) and v["ID Usuario"] == id_usuario:
            existente_row_number = i + 2
            break

    if existente_row_number is not None:
        tabla.update_row(existente_row_number, {"Puntuación": puntuacion})
    else:
        tabla.append({
            "ID Grupo": id_grupo,
            "ID Sesión": id_sesion,
            "ID Canción": id_cancion,
            "Turno": turno,
            "ID Usuario": id_usuario,
            "Puntuación": puntuacion,
            "Fecha": now_iso(),
        })
    return votos_turno(id_grupo, id_sesion, id_cancion)


def votos_turno(id_grupo: str, id_sesion: str, id_cancion: str) -> dict:
    _, turno_row = _fila_turno(id_sesion, id_cancion)
    if turno_row is None or turno_row["ID Grupo"] != id_grupo:
        raise ValueError("Turno no encontrado")
    turno = str(int(turno_row["Turno"] or 0))

    votos = [
        {"id_usuario": v["ID Usuario"], "puntuacion": int(v["Puntuación"])}
        for v in _votos_turno().all_rows()
        if v["ID Sesión"] == id_sesion and v["ID Canción"] == id_cancion and str(v["Turno"]) == turno
        and str(v["Puntuación"]).strip().isdigit()
    ]
    promedio = round(sum(v["puntuacion"] for v in votos) / len(votos), 2) if votos else None
    return {"votos": votos, "promedio": promedio}


def marcar_cantada(id_grupo: str, id_sesion: str, id_cancion: str, puntuacion: int | None) -> dict:
    row_number, row = _turno_pendiente(id_sesion, id_cancion)
    if row["ID Grupo"] != id_grupo:
        raise ValueError("No hay un turno pendiente para esa canción en esta sesión")

    votos_info = votos_turno(id_grupo, id_sesion, id_cancion)
    if votos_info["promedio"] is not None:
        puntuacion_final = round(votos_info["promedio"])
    elif puntuacion is not None:
        puntuacion_final = puntuacion
    else:
        raise ValueError("Falta la puntuación: nadie votó esta interpretación todavía")

    _cs().update_row(row_number, {"Puntuación": puntuacion_final, "Estado": "Cantada"})
    canciones_svc.registrar_cantada(id_cancion)

    # Un turno puede tener varios cantantes (dueto/grupal) separados por
    # coma en "Cantada por" — cada uno recibe el puntaje completo, no
    # repartido entre todos.
    for nombre in [n.strip() for n in row["Cantada por"].split(",") if n.strip()]:
        usuario = usuarios_svc.get_or_create(id_grupo, nombre)
        usuarios_svc.sumar_puntos(usuario["id"], puntuacion_final)

    row["Puntuación"] = puntuacion_final
    row["Estado"] = "Cantada"
    return _turno_to_out(row)


def saltar(id_grupo: str, id_sesion: str, id_cancion: str) -> dict:
    row_number, row = _turno_pendiente(id_sesion, id_cancion)
    if row["ID Grupo"] != id_grupo:
        raise ValueError("No hay un turno pendiente para esa canción en esta sesión")
    _cs().update_row(row_number, {"Estado": "Saltada"})
    row["Estado"] = "Saltada"
    return _turno_to_out(row)


def finalizar(id_grupo: str, id_sesion: str) -> dict:
    row_number, row = _sesiones().get_by_id("ID Sesión", id_sesion)
    if row_number is None or row["ID Grupo"] != id_grupo:
        raise ValueError("Sesión no encontrada")
    _sesiones().update_row(row_number, {"Estado": "Finalizada"})
    row["Estado"] = "Finalizada"
    return _sesion_row_to_out(row)


def historial(id_grupo: str) -> list[dict]:
    sesiones = [_sesion_row_to_out(r) for r in _sesiones().all_rows() if r["ID Grupo"] == id_grupo]
    sesiones.sort(key=lambda s: s["fecha"], reverse=True)
    return sesiones


def detalle(id_grupo: str, id_sesion: str) -> list[dict]:
    turnos = [t for t in _turnos_de_sesion(id_sesion) if t["ID Grupo"] == id_grupo]
    turnos.sort(key=lambda t: int(t["Turno"] or 0))
    return [_turno_to_out(t) for t in turnos]
