"""Lógica de negocio de Sesiones de karaoke: turnos, cola, selección de
canción, participantes en vivo, votación en tiempo real, marcar cantada /
saltar y cierre e historial.
"""
import random
from datetime import datetime

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


def _turno_dict(row: dict, cancion: dict | None) -> dict:
    return {
        "id_sesion": row["id_sesion"],
        "id_cancion": row["id_cancion"],
        "turno": row["turno"],
        "cantada_por": row["cantada_por"],
        "puntuacion": row["puntuacion"],
        "estado": row["estado"],
        "cancion": cancion,
    }


def _turno_to_out(row: dict, incluir_cancion: bool = True) -> dict:
    return _turno_dict(row, canciones_svc.get_por_id(row["id_cancion"]) if incluir_cancion else None)


def _turnos_to_out(rows: list[dict]) -> list[dict]:
    """Igual que _turno_to_out pero para una lista: resuelve todas las
    canciones de una sola consulta en vez de una por turno."""
    canciones = canciones_svc.get_varias_por_id([r["id_cancion"] for r in rows])
    return [_turno_dict(r, canciones.get(r["id_cancion"])) for r in rows]


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
        "SELECT * FROM canciones_sesion WHERE id_sesion = %s AND estado = 'En cola' AND id_mesa IS NULL "
        "ORDER BY orden ASC, id ASC",
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
    return _turnos_to_out(filas_cola)


def siguiente_cancion(id_grupo: str, id_sesion: str, id_usuario_actor: str, modo: str | None = None) -> dict:
    """Arma el próximo turno.

    modo="cola": saca la primera de la cola (y falla si está vacía).
    modo="aleatorio": sortea del catálogo IGNORANDO la cola — lo que está
    encolado queda reservado para cuando se vuelva al modo cola, así que
    tampoco puede salir sorteado.
    modo=None: comportamiento histórico (primero la cola, y si está vacía
    sortea). Es lo que mandan los clientes viejos que todavía tienen el
    bundle anterior cacheado, así que no se les puede romper.

    Las consultas a la cola filtran id_mesa IS NULL: los pedidos que vienen de
    una mesa del salón se manejan por siguiente_salon, que respeta la rotación
    y el nombre de quien pidió. Si entraran por acá se les reasignaría el
    cantante por rotación entre participantes y se saltearía el orden de
    mesas — pasa si alguien del local abre la vista de Karaoke por error.
    """
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

    # En modo aleatorio ni miramos la cola. En los otros dos (cola explícita
    # o cliente viejo sin modo) la cola manda; la diferencia es qué pasa si
    # está vacía: con "cola" avisamos, sin modo caemos al sorteo de abajo.
    cola_row = None
    if modo != "aleatorio":
        cola_row = db.fetch_one(
            "SELECT * FROM canciones_sesion WHERE id_sesion = %s AND estado = 'En cola' AND id_mesa IS NULL "
            "ORDER BY orden ASC, id ASC LIMIT 1",
            (id_sesion,),
        )
        if cola_row is None and modo == "cola":
            raise ValueError("La cola está vacía: agregá canciones o cambiá a modo aleatorio")

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

    # Modo aleatorio: 'En cola' sigue contando como usada, así lo que alguien
    # dejó encolado no sale sorteado y queda esperando su turno en la cola.
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
    return _turnos_to_out(rows)


# ---------------------------------------------------------------------------
# Modo salón: pedidos por mesa y rotación entre mesas
#
# Los pedidos viven en canciones_sesion igual que los turnos del modo grupo,
# pero con id_mesa y una "ronda". La cola no se lee por "orden" sino por
# (ronda, id): eso produce el intercalado entre mesas.
# ---------------------------------------------------------------------------

# Duración típica de un turno de karaoke, incluyendo el cambio de cantante y
# lo que el DJ habla en el medio. Solo se usa para estimar la espera que ve el
# cliente ("faltan ~35 min"), que es la pregunta que hoy le hacen al DJ veinte
# veces por noche.
MINUTOS_POR_CANCION = 4

# Techo de pedidos sin cantar por mesa. Evita que una mesa cargue cincuenta
# canciones y monopolice la pantalla del DJ; no limita cuánto puede cantar,
# porque a medida que le van saliendo puede seguir pidiendo.
MAX_PEDIDOS_PENDIENTES = 10

_ESTADOS_EN_JUEGO = ("En cola", "Pendiente")


def _ronda_actual_salon(id_sesion: str) -> int:
    """La vuelta que está corriendo ahora mismo en el salón.

    Es la ronda más baja que todavía tiene pedidos esperando. Si no quedan
    pedidos (la cola se vació), es la siguiente a la última que ya sonó.
    """
    fila = db.fetch_one(
        "SELECT MIN(ronda) AS r FROM canciones_sesion "
        "WHERE id_sesion = %s AND id_mesa IS NOT NULL AND estado IN ('En cola', 'Pendiente')",
        (id_sesion,),
    )
    if fila and fila["r"] is not None:
        return fila["r"]

    fila = db.fetch_one(
        "SELECT MAX(ronda) AS r FROM canciones_sesion WHERE id_sesion = %s AND id_mesa IS NOT NULL",
        (id_sesion,),
    )
    if fila and fila["r"] is not None:
        return fila["r"] + 1
    return 0


def _calcular_ronda(id_sesion: str, mesa_row: dict) -> int:
    """En qué vuelta entra el pedido que la mesa está haciendo ahora.

    Tres casos, y cada uno resuelve un problema real del salón:

    1. La mesa no pidió nada todavía → entra en la vuelta en curso. Así una
       mesa que se sienta a las 11 de la noche no se cuela adelante de todo
       ni queda detrás de las tres vueltas que las otras ya dejaron cargadas.
    2. Le queda cupo en su última vuelta → va en esa misma vuelta. Es lo que
       hace que una mesa de 2+ personas meta dos canciones seguidas.
    3. Llenó su cupo → pasa a la vuelta siguiente, y nunca antes de la que
       está corriendo (si estuvo un rato sin pedir, no puede "recuperar"
       vueltas viejas y saltearse a las demás).
    """
    fila = db.fetch_one(
        "SELECT MAX(ronda) AS ultima FROM canciones_sesion WHERE id_sesion = %s AND id_mesa = %s",
        (id_sesion, mesa_row["id"]),
    )
    ultima = fila["ultima"] if fila else None
    ronda_salon = _ronda_actual_salon(id_sesion)

    if ultima is None:
        return max(ronda_salon, mesa_row["ronda_base"])

    en_esa_ronda = db.fetch_one(
        "SELECT COUNT(*) AS n FROM canciones_sesion WHERE id_sesion = %s AND id_mesa = %s AND ronda = %s",
        (id_sesion, mesa_row["id"], ultima),
    )["n"]
    if en_esa_ronda < max(1, mesa_row["cupo_por_ronda"]):
        return ultima
    return max(ultima + 1, ronda_salon)


def _sesion_activa_row(id_grupo: str, id_sesion: str) -> dict:
    row = db.fetch_one("SELECT * FROM sesiones WHERE id_sesion = %s", (id_sesion,))
    if row is None or row["id_grupo"] != id_grupo:
        raise ValueError("Sesión no encontrada")
    if row["estado"] != "Activa":
        raise ValueError("La sesión no está activa")
    return row


def ronda_actual(id_grupo: str, id_sesion: str) -> int:
    _sesion_activa_row(id_grupo, id_sesion)
    return _ronda_actual_salon(id_sesion)


def agregar_pedido(id_grupo: str, id_sesion: str, mesa_row: dict, id_cancion: str, pedido_por: str = "") -> dict:
    """Encola una canción pedida desde una mesa.

    A diferencia de agregar_a_cola (modo grupo), acá una canción repetida NO
    se rechaza: en un salón con doscientas personas, prohibir un tema porque
    alguien lo cantó a las 8 de la noche sería absurdo. El repetido se marca
    para que el DJ lo vea y decida.
    """
    _sesion_activa_row(id_grupo, id_sesion)
    if mesa_row["estado"] != "Abierta":
        raise ValueError("La mesa está cerrada: pedile al mozo que la abra")
    if mesa_row["id_sesion"] != id_sesion:
        raise ValueError("La mesa no está abierta en esta noche")

    cancion = canciones_svc.get_por_id(id_cancion)
    if cancion is None:
        raise ValueError("Esa canción no está en el catálogo del local")

    pendientes = db.fetch_one(
        "SELECT COUNT(*) AS n FROM canciones_sesion "
        "WHERE id_sesion = %s AND id_mesa = %s AND estado IN ('En cola', 'Pendiente')",
        (id_sesion, mesa_row["id"]),
    )["n"]
    if pendientes >= MAX_PEDIDOS_PENDIENTES:
        raise ValueError(
            f"Ya tenés {MAX_PEDIDOS_PENDIENTES} canciones esperando. "
            "Cuando te salga alguna vas a poder pedir más."
        )

    ya_pedida = db.fetch_one(
        "SELECT id FROM canciones_sesion "
        "WHERE id_sesion = %s AND id_mesa = %s AND id_cancion = %s AND estado IN ('En cola', 'Pendiente')",
        (id_sesion, mesa_row["id"], id_cancion),
    )
    if ya_pedida is not None:
        raise ValueError("Esa canción ya está en la lista de tu mesa")

    ronda = _calcular_ronda(id_sesion, mesa_row)
    row = db.fetch_one(
        "INSERT INTO canciones_sesion "
        "(id_sesion, id_grupo, id_cancion, orden, turno, cantada_por, puntuacion, estado, "
        " id_mesa, pedido_por, ronda, fecha_pedido) "
        "VALUES (%s, %s, %s, 0, 0, %s, NULL, 'En cola', %s, %s, %s, %s) RETURNING *",
        (id_sesion, id_grupo, id_cancion, pedido_por.strip(), mesa_row["id"], pedido_por.strip(), ronda, now_iso()),
    )
    return _pedido_to_out(row, cancion, mesa_row)


def _pedido_to_out(row: dict, cancion: dict | None, mesa: dict | None) -> dict:
    return {
        "id": row["id"],
        "id_cancion": row["id_cancion"],
        "cancion": cancion,
        "estado": row["estado"],
        "ronda": row["ronda"],
        "turno": row["turno"],
        "pedido_por": row["pedido_por"],
        "fecha_pedido": row["fecha_pedido"],
        "fecha_cantada": row["fecha_cantada"],
        "id_mesa": row["id_mesa"],
        "mesa_numero": mesa["numero"] if mesa else "",
    }


def _minutos_desde(fecha: str) -> int | None:
    if not fecha:
        return None
    try:
        cuando = datetime.strptime(fecha, "%Y-%m-%d %H:%M:%S")
    except ValueError:
        return None
    return max(0, int((datetime.now() - cuando).total_seconds() // 60))


def _cargar_pedidos(id_sesion: str) -> tuple[list[dict], dict, dict]:
    """Trae todos los pedidos de la noche más las mesas y canciones que hacen
    falta, en tres consultas fijas (no una por fila)."""
    rows = db.fetch_all(
        "SELECT * FROM canciones_sesion WHERE id_sesion = %s AND id_mesa IS NOT NULL "
        "ORDER BY ronda ASC, id ASC",
        (id_sesion,),
    )
    canciones = canciones_svc.get_varias_por_id([r["id_cancion"] for r in rows])
    ids_mesa = list({r["id_mesa"] for r in rows if r["id_mesa"]})
    mesas = {}
    if ids_mesa:
        mesas = {m["id"]: m for m in db.fetch_all("SELECT * FROM mesas WHERE id = ANY(%s)", (ids_mesa,))}
    return rows, canciones, mesas


def cola_salon(id_grupo: str, id_sesion: str) -> dict:
    """Todo lo que la vista del DJ necesita, en una sola llamada.

    Devuelve qué está sonando, la rotación que sigue, y por cada pedido si la
    canción ya se cantó esta noche (y hace cuánto), para que el DJ decida si
    la repite o la saltea.
    """
    _sesion_activa_row(id_grupo, id_sesion)
    rows, canciones, mesas = _cargar_pedidos(id_sesion)

    # Cuándo sonó cada canción, para marcar los repetidos. Las fechas están en
    # "YYYY-MM-DD HH:MM:SS", que ordena igual como texto que como fecha.
    cantadas_previas: dict[str, list[str]] = {}
    for r in rows:
        if r["estado"] == "Cantada" and r["fecha_cantada"]:
            cantadas_previas.setdefault(r["id_cancion"], []).append(r["fecha_cantada"])

    def armar(row):
        salida = _pedido_to_out(row, canciones.get(row["id_cancion"]), mesas.get(row["id_mesa"]))
        previas = cantadas_previas.get(row["id_cancion"], [])
        if row["estado"] == "Cantada" and row["fecha_cantada"]:
            # Un pedido ya cantado no es repetido de sí mismo: solo cuentan
            # las veces que sonó ANTES que él.
            previas = [f for f in previas if f < row["fecha_cantada"]]
        salida["repetida"] = len(previas) > 0
        salida["cantada_hace_min"] = _minutos_desde(max(previas)) if previas else None
        return salida

    ahora = next((armar(r) for r in rows if r["estado"] == "Pendiente"), None)
    cola = [armar(r) for r in rows if r["estado"] == "En cola"]
    cantadas = [armar(r) for r in rows if r["estado"] == "Cantada"]

    return {
        "id_sesion": id_sesion,
        "ahora": ahora,
        "cola": cola,
        "cantadas": list(reversed(cantadas))[:15],
        "total_cantadas": len(cantadas),
        "ronda_actual": _ronda_actual_salon(id_sesion),
        # Se cuenta contra la tabla y no contra `mesas`, que solo trae las que
        # ya pidieron algo: una mesa recién abierta todavía no aparece ahí.
        "mesas_abiertas": db.fetch_one(
            "SELECT COUNT(*) AS n FROM mesas WHERE id_grupo = %s AND estado = 'Abierta'", (id_grupo,)
        )["n"],
    }


def _pedido_row(id_grupo: str, id_pedido: int) -> dict:
    """Un pedido se busca por su id de fila, no por id_cancion: en el salón la
    misma canción puede aparecer varias veces en la misma noche."""
    row = db.fetch_one("SELECT * FROM canciones_sesion WHERE id = %s", (id_pedido,))
    if row is None or row["id_grupo"] != id_grupo or row["id_mesa"] is None:
        raise ValueError("Pedido no encontrado")
    return row


def siguiente_salon(id_grupo: str, id_sesion: str) -> dict | None:
    """Promueve el primer pedido de la rotación al puesto de "ahora suena"."""
    sesion_row = _sesion_activa_row(id_grupo, id_sesion)

    # Mismo criterio de idempotencia que siguiente_cancion: si ya hay algo
    # sonando, dos clics seguidos devuelven eso y no arman un segundo turno.
    pendiente = db.fetch_one(
        "SELECT * FROM canciones_sesion WHERE id_sesion = %s AND id_mesa IS NOT NULL AND estado = 'Pendiente' "
        "ORDER BY id ASC LIMIT 1",
        (id_sesion,),
    )
    if pendiente is None:
        pendiente = db.fetch_one(
            "SELECT * FROM canciones_sesion WHERE id_sesion = %s AND id_mesa IS NOT NULL AND estado = 'En cola' "
            "ORDER BY ronda ASC, id ASC LIMIT 1",
            (id_sesion,),
        )
        if pendiente is None:
            return None
        nuevo_turno = sesion_row["turno_actual"] + 1
        db.execute(
            "UPDATE canciones_sesion SET estado = 'Pendiente', turno = %s WHERE id = %s",
            (nuevo_turno, pendiente["id"]),
        )
        db.execute("UPDATE sesiones SET turno_actual = %s WHERE id_sesion = %s", (nuevo_turno, id_sesion))
        pendiente.update({"estado": "Pendiente", "turno": nuevo_turno})

    mesa = db.fetch_one("SELECT * FROM mesas WHERE id = %s", (pendiente["id_mesa"],))
    return _pedido_to_out(pendiente, canciones_svc.get_por_id(pendiente["id_cancion"]), mesa)


def marcar_cantada_salon(id_grupo: str, id_pedido: int) -> dict:
    """El DJ marca que el pedido ya sonó.

    No pide puntuación ni reparte puntos: en el salón principal el público
    rota toda la noche y un ranking entre desconocidos no significa nada. Lo
    que sí se registra es veces_cantada de la canción, que es el dato que al
    local le sirve para saber qué se pide de verdad.
    """
    row = _pedido_row(id_grupo, id_pedido)
    if row["estado"] not in _ESTADOS_EN_JUEGO:
        raise ValueError("Ese pedido ya no está en juego")
    cuando = now_iso()
    db.execute(
        "UPDATE canciones_sesion SET estado = 'Cantada', fecha_cantada = %s WHERE id = %s",
        (cuando, id_pedido),
    )
    canciones_svc.registrar_cantada(row["id_cancion"])
    row.update({"estado": "Cantada", "fecha_cantada": cuando})
    mesa = db.fetch_one("SELECT * FROM mesas WHERE id = %s", (row["id_mesa"],))
    return _pedido_to_out(row, canciones_svc.get_por_id(row["id_cancion"]), mesa)


def no_vino(id_grupo: str, id_pedido: int) -> dict:
    """Nadie subió a cantar: el pedido se atrasa una vuelta en vez de perderse.

    Borrarlo sería lo fácil y lo equivocado — normalmente el que pidió está en
    el baño o en la barra, y vuelve. Que pierda su lugar en esta vuelta pero
    conserve el pedido es lo que espera cualquiera que haya trabajado la
    puerta de un karaoke.
    """
    row = _pedido_row(id_grupo, id_pedido)
    if row["estado"] not in _ESTADOS_EN_JUEGO:
        raise ValueError("Ese pedido ya no está en juego")

    nueva_ronda = max(row["ronda"] + 1, _ronda_actual_salon(row["id_sesion"]) + 1)
    db.execute(
        "UPDATE canciones_sesion SET estado = 'En cola', ronda = %s, turno = 0 WHERE id = %s",
        (nueva_ronda, id_pedido),
    )
    row.update({"estado": "En cola", "ronda": nueva_ronda, "turno": 0})
    mesa = db.fetch_one("SELECT * FROM mesas WHERE id = %s", (row["id_mesa"],))
    return _pedido_to_out(row, canciones_svc.get_por_id(row["id_cancion"]), mesa)


def cancelar_pedido(id_grupo: str, id_pedido: int, id_mesa: str | None = None) -> None:
    """Saca un pedido de la rotación. Con id_mesa, solo deja borrar los
    propios (es lo que usa el cliente desde su celular); sin id_mesa es el DJ,
    que puede sacar cualquiera."""
    row = _pedido_row(id_grupo, id_pedido)
    if id_mesa is not None and row["id_mesa"] != id_mesa:
        raise PermissionError("Ese pedido es de otra mesa")
    if row["estado"] not in _ESTADOS_EN_JUEGO:
        raise ValueError("Ese pedido ya no está en juego")
    db.execute("UPDATE canciones_sesion SET estado = 'Cancelada' WHERE id = %s", (id_pedido,))


def subir_pedido(id_grupo: str, id_pedido: int) -> dict:
    """Override manual del DJ: mete un pedido al frente de la rotación.

    El DJ manda. Un sistema que le saca el control de la noche lo desenchufan
    la primera vez que necesitan sacar a alguien antes (un cumpleaños, un
    cliente que se va, lo que sea).
    """
    row = _pedido_row(id_grupo, id_pedido)
    if row["estado"] != "En cola":
        raise ValueError("Ese pedido no está esperando en la cola")

    ronda_min = db.fetch_one(
        "SELECT MIN(ronda) AS r FROM canciones_sesion "
        "WHERE id_sesion = %s AND id_mesa IS NOT NULL AND estado = 'En cola'",
        (row["id_sesion"],),
    )["r"]
    # Una ronda por debajo de la más baja: queda primero sin tener que
    # reescribir el orden de todos los demás pedidos.
    nueva_ronda = (ronda_min if ronda_min is not None else row["ronda"]) - 1
    db.execute("UPDATE canciones_sesion SET ronda = %s WHERE id = %s", (nueva_ronda, id_pedido))
    row["ronda"] = nueva_ronda
    mesa = db.fetch_one("SELECT * FROM mesas WHERE id = %s", (row["id_mesa"],))
    return _pedido_to_out(row, canciones_svc.get_por_id(row["id_cancion"]), mesa)


def estado_mesa(mesa_row: dict) -> dict:
    """Lo que ve el cliente en su celular: qué suena, sus pedidos, su lugar en
    la cola y cuánto falta.

    La espera estimada es la razón de ser de esta pantalla: es exactamente la
    pregunta que hoy le hacen al DJ toda la noche.
    """
    id_sesion = mesa_row["id_sesion"]
    if not id_sesion:
        return {
            "mesa": {"id": mesa_row["id"], "numero": mesa_row["numero"], "estado": mesa_row["estado"]},
            "abierta": False,
            "ahora": None,
            "mis_pedidos": [],
            "total_en_cola": 0,
        }

    rows, canciones, mesas = _cargar_pedidos(id_sesion)
    cola = [r for r in rows if r["estado"] == "En cola"]
    pendiente = next((r for r in rows if r["estado"] == "Pendiente"), None)

    mis_pedidos = []
    for posicion, r in enumerate(cola, start=1):
        if r["id_mesa"] != mesa_row["id"]:
            continue
        salida = _pedido_to_out(r, canciones.get(r["id_cancion"]), mesa_row)
        salida["posicion"] = posicion
        # +1 por la que está sonando ahora, que también hay que esperar.
        salida["espera_min"] = (posicion - 1 + (1 if pendiente else 0)) * MINUTOS_POR_CANCION
        mis_pedidos.append(salida)

    ahora = None
    if pendiente is not None:
        ahora = _pedido_to_out(pendiente, canciones.get(pendiente["id_cancion"]), mesas.get(pendiente["id_mesa"]))
        ahora["es_mi_mesa"] = pendiente["id_mesa"] == mesa_row["id"]

    return {
        "mesa": {
            "id": mesa_row["id"],
            "numero": mesa_row["numero"],
            "estado": mesa_row["estado"],
            "tamano": mesa_row["tamano"],
            "cupo_por_ronda": mesa_row["cupo_por_ronda"],
        },
        "abierta": mesa_row["estado"] == "Abierta",
        "ahora": ahora,
        "mis_pedidos": mis_pedidos,
        "total_en_cola": len(cola),
        "max_pedidos": MAX_PEDIDOS_PENDIENTES,
    }


def agregar_sugerencia(id_grupo: str, id_sesion: str, mesa_row: dict, titulo: str, artista: str, pedido_por: str) -> dict:
    """Guarda una canción que el local no tiene. No entra a la rotación (el DJ
    no la puede poner); es la señal de qué le falta al catálogo."""
    _sesion_activa_row(id_grupo, id_sesion)
    titulo = titulo.strip()
    if not titulo:
        raise ValueError("Escribí el nombre de la canción")

    row = db.fetch_one(
        "INSERT INTO sugerencias_mesa (id_grupo, id_sesion, id_mesa, titulo, artista, pedido_por, fecha) "
        "VALUES (%s, %s, %s, %s, %s, %s, %s) RETURNING *",
        (id_grupo, id_sesion, mesa_row["id"], titulo, artista.strip(), pedido_por.strip(), now_iso()),
    )
    return {
        "id": row["id"],
        "titulo": row["titulo"],
        "artista": row["artista"],
        "pedido_por": row["pedido_por"],
        "mesa_numero": mesa_row["numero"],
        "fecha": row["fecha"],
    }


def listar_sugerencias(id_grupo: str, id_sesion: str) -> list[dict]:
    rows = db.fetch_all(
        "SELECT s.*, m.numero AS mesa_numero FROM sugerencias_mesa s "
        "LEFT JOIN mesas m ON m.id = s.id_mesa "
        "WHERE s.id_grupo = %s AND s.id_sesion = %s ORDER BY s.id DESC",
        (id_grupo, id_sesion),
    )
    return [
        {
            "id": r["id"],
            "titulo": r["titulo"],
            "artista": r["artista"],
            "pedido_por": r["pedido_por"],
            "mesa_numero": r["mesa_numero"] or "",
            "fecha": r["fecha"],
        }
        for r in rows
    ]
