"""Gamificación: ranking de la noche, ranking histórico y logros/badges.

Los badges se calculan al vuelo a partir del historial en
Canciones_Sesion + Usuarios — no se guardan en ninguna hoja.
"""
from ..sheets_client import SheetTable
from . import canciones as canciones_svc
from . import usuarios as usuarios_svc

BADGES = {
    "debut": {"nombre": "Debut", "descripcion": "Cantó su primera canción", "icono": "🎤"},
    "maratonista": {"nombre": "Maratonista", "descripcion": "Cantó 5 canciones o más", "icono": "🏃"},
    "voz_de_oro": {"nombre": "Voz de Oro", "descripcion": "Promedio de puntuación 9+", "icono": "🌟"},
    "fiel": {"nombre": "Fiel Asistente", "descripcion": "Participó en 5 sesiones o más", "icono": "📅"},
    "explorador": {"nombre": "Explorador de Géneros", "descripcion": "Cantó 3 géneros distintos", "icono": "🧭"},
}


def _cantadas_de(id_grupo: str, nombre: str) -> list[dict]:
    rows = SheetTable("Canciones_Sesion").all_rows()
    return [
        r for r in rows
        if r["ID Grupo"] == id_grupo and r["Cantada por"] == nombre and r["Estado"] == "Cantada"
    ]


def badges_de_usuario(id_grupo: str, usuario: dict) -> list[dict]:
    cantadas = _cantadas_de(id_grupo, usuario["nombre"])
    codigos: list[str] = []
    if cantadas:
        codigos.append("debut")
    if len(cantadas) >= 5:
        codigos.append("maratonista")

    puntuaciones = [int(t["Puntuación"]) for t in cantadas if str(t["Puntuación"]).strip().isdigit()]
    if puntuaciones and sum(puntuaciones) / len(puntuaciones) >= 9:
        codigos.append("voz_de_oro")

    if usuario["sesiones_jugadas"] >= 5:
        codigos.append("fiel")

    generos = set()
    for t in cantadas:
        c = canciones_svc.get_por_id(t["ID Canción"])
        if c:
            generos.add(c["genero"])
    if len(generos) >= 3:
        codigos.append("explorador")

    return [{"codigo": c, **BADGES[c]} for c in codigos]


def ranking_noche(id_grupo: str, id_sesion: str) -> list[dict]:
    rows = [
        r for r in SheetTable("Canciones_Sesion").all_rows()
        if r["ID Grupo"] == id_grupo and r["ID Sesión"] == id_sesion and r["Estado"] == "Cantada"
    ]
    acumulado: dict[str, dict] = {}
    for r in rows:
        nombre = r["Cantada por"]
        acumulado.setdefault(nombre, {"puntos": 0, "canciones": 0})
        if str(r["Puntuación"]).strip().isdigit():
            acumulado[nombre]["puntos"] += int(r["Puntuación"])
        acumulado[nombre]["canciones"] += 1

    resultado = []
    for nombre, datos in acumulado.items():
        usuario = usuarios_svc.get_or_create(id_grupo, nombre)
        resultado.append({
            "id_usuario": usuario["id"],
            "nombre": nombre,
            "foto": usuario["foto"],
            "puntos": datos["puntos"],
            "canciones_cantadas": datos["canciones"],
            "badges": badges_de_usuario(id_grupo, usuario),
        })
    resultado.sort(key=lambda r: r["puntos"], reverse=True)
    return resultado


def ranking_historico(id_grupo: str) -> list[dict]:
    usuarios = usuarios_svc.listar(id_grupo)
    resultado = []
    for u in usuarios:
        cantadas = _cantadas_de(id_grupo, u["nombre"])
        resultado.append({
            "id_usuario": u["id"],
            "nombre": u["nombre"],
            "foto": u["foto"],
            "puntos": u["puntos_totales"],
            "canciones_cantadas": len(cantadas),
            "badges": badges_de_usuario(id_grupo, u),
        })
    resultado.sort(key=lambda r: r["puntos"], reverse=True)
    return resultado
