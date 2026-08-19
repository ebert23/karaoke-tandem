"""Gamificación: ranking de la noche, ranking histórico y logros/badges.

Los badges se calculan al vuelo a partir del historial en
Canciones_Sesion + Usuarios — no se guardan en ninguna hoja.

Todo el módulo trabaja sobre dos listas traídas UNA sola vez (las filas
cantadas del grupo y sus canciones) en vez de consultar por usuario y por
canción. Antes cada persona del ranking disparaba dos consultas de todo el
historial más una por cada canción que había cantado: en un grupo con 3
personas y 50 turnos eso eran cientos de idas a Postgres, y como la base está
en otra región el histórico tardaba más de 7 segundos en responder.
"""
from .. import db
from . import canciones as canciones_svc
from . import usuarios as usuarios_svc

BADGES = {
    "debut": {"nombre": "Debut", "descripcion": "Cantó su primera canción", "icono": "🎤"},
    "maratonista": {"nombre": "Maratonista", "descripcion": "Cantó 5 canciones o más", "icono": "🏃"},
    "voz_de_oro": {"nombre": "Voz de Oro", "descripcion": "Promedio de puntuación 9+", "icono": "🌟"},
    "fiel": {"nombre": "Fiel Asistente", "descripcion": "Participó en 5 sesiones o más", "icono": "📅"},
    "explorador": {"nombre": "Explorador de Géneros", "descripcion": "Cantó 3 géneros distintos", "icono": "🧭"},
}


def _cantantes_de_turno(row: dict) -> list[str]:
    return [n.strip() for n in row["cantada_por"].split(",") if n.strip()]


class _Historial:
    """El historial cantado del grupo, ya cargado y agrupado por persona.

    "Cantada por" puede traer varios nombres separados por coma (dueto o
    grupal) — cada uno cuenta la canción como propia, no solo el primero.
    """

    def __init__(self, id_grupo: str, id_sesion: str | None = None):
        if id_sesion:
            self.filas = db.fetch_all(
                "SELECT * FROM canciones_sesion "
                "WHERE id_grupo = %s AND id_sesion = %s AND estado = 'Cantada'",
                (id_grupo, id_sesion),
            )
        else:
            self.filas = db.fetch_all(
                "SELECT * FROM canciones_sesion WHERE id_grupo = %s AND estado = 'Cantada'",
                (id_grupo,),
            )

        self.por_nombre: dict[str, list[dict]] = {}
        for fila in self.filas:
            for nombre in _cantantes_de_turno(fila):
                self.por_nombre.setdefault(nombre.lower(), []).append(fila)

        canciones = canciones_svc.get_varias_por_id([f["id_cancion"] for f in self.filas])
        self.genero_de = {cid: c["genero"] for cid, c in canciones.items()}

    def cantadas_de(self, nombre: str) -> list[dict]:
        return self.por_nombre.get(nombre.strip().lower(), [])


def _badges(historial: _Historial, usuario: dict) -> list[dict]:
    cantadas = historial.cantadas_de(usuario["nombre"])
    codigos: list[str] = []
    if cantadas:
        codigos.append("debut")
    if len(cantadas) >= 5:
        codigos.append("maratonista")

    puntuaciones = [t["puntuacion"] for t in cantadas if t["puntuacion"] is not None]
    if puntuaciones and sum(puntuaciones) / len(puntuaciones) >= 9:
        codigos.append("voz_de_oro")

    if usuario["sesiones_jugadas"] >= 5:
        codigos.append("fiel")

    generos = {historial.genero_de.get(t["id_cancion"]) for t in cantadas}
    generos.discard(None)
    if len(generos) >= 3:
        codigos.append("explorador")

    return [{"codigo": c, **BADGES[c]} for c in codigos]


def ranking_noche(id_grupo: str, id_sesion: str) -> list[dict]:
    # Los badges son del historial completo (no solo de esta noche), así que
    # se cargan los dos: el de la sesión para los puntos, el general para los
    # logros. Son dos consultas en total, no dos por persona.
    historial_general = _Historial(id_grupo)
    de_la_noche = _Historial(id_grupo, id_sesion)

    acumulado: dict[str, dict] = {}
    for r in de_la_noche.filas:
        puntos_fila = r["puntuacion"] or 0
        for nombre in _cantantes_de_turno(r):
            acumulado.setdefault(nombre, {"puntos": 0, "canciones": 0})
            acumulado[nombre]["puntos"] += puntos_fila
            acumulado[nombre]["canciones"] += 1

    # Los usuarios se resuelven contra una sola lista: get_or_create consulta
    # por nombre, y en una noche larga eso era una consulta por cantante. Solo
    # se crea al que de verdad no existe (pasa si alguien cantó como invitado).
    por_nombre = {u["nombre"].strip().lower(): u for u in usuarios_svc.listar(id_grupo)}

    resultado = []
    for nombre, datos in acumulado.items():
        usuario = por_nombre.get(nombre.strip().lower()) or usuarios_svc.get_or_create(id_grupo, nombre)
        resultado.append({
            "id_usuario": usuario["id"],
            "nombre": nombre,
            "foto": usuario["foto"],
            "puntos": datos["puntos"],
            "canciones_cantadas": datos["canciones"],
            "badges": _badges(historial_general, usuario),
        })
    resultado.sort(key=lambda r: r["puntos"], reverse=True)
    return resultado


def ranking_historico(id_grupo: str) -> list[dict]:
    historial = _Historial(id_grupo)
    resultado = []
    for u in usuarios_svc.listar(id_grupo):
        cantadas = historial.cantadas_de(u["nombre"])
        resultado.append({
            "id_usuario": u["id"],
            "nombre": u["nombre"],
            "foto": u["foto"],
            "puntos": u["puntos_totales"],
            "canciones_cantadas": len(cantadas),
            "badges": _badges(historial, u),
        })
    resultado.sort(key=lambda r: r["puntos"], reverse=True)
    return resultado
