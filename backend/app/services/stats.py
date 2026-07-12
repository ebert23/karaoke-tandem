"""Estadísticas personales: canciones más cantadas y géneros favoritos."""
from collections import Counter

from ..sheets_client import SheetTable
from . import canciones as canciones_svc
from . import usuarios as usuarios_svc


def estadisticas(id_grupo: str, id_usuario: str) -> dict:
    usuario = usuarios_svc.get_por_id(id_grupo, id_usuario)
    if not usuario:
        raise ValueError("Usuario no encontrado")

    # "Cantada por" puede traer varios nombres separados por coma (dueto o
    # grupal); contamos la fila si el usuario figura entre ellos.
    nombre_lower = usuario["nombre"].strip().lower()
    filas = [
        r for r in SheetTable("Canciones_Sesion").all_rows()
        if r["ID Grupo"] == id_grupo
        and r["Estado"] == "Cantada"
        and nombre_lower in [n.strip().lower() for n in r["Cantada por"].split(",") if n.strip()]
    ]

    detalle = []
    generos = Counter()
    puntuaciones = []
    for r in filas:
        cancion = canciones_svc.get_por_id(r["ID Canción"])
        if not cancion:
            continue
        puntuacion = int(r["Puntuación"]) if str(r["Puntuación"]).strip().isdigit() else None
        if puntuacion is not None:
            puntuaciones.append(puntuacion)
        generos[cancion["genero"]] += 1
        detalle.append({
            "titulo": cancion["titulo"],
            "artista": cancion["artista"],
            "genero": cancion["genero"],
            "puntuacion": puntuacion,
        })

    detalle.sort(key=lambda d: d["puntuacion"] or 0, reverse=True)
    genero_favorito = generos.most_common(1)[0][0] if generos else None

    return {
        "id_usuario": usuario["id"],
        "nombre": usuario["nombre"],
        "canciones_cantadas": len(filas),
        "puntuacion_promedio": round(sum(puntuaciones) / len(puntuaciones), 2) if puntuaciones else 0.0,
        "genero_favorito": genero_favorito,
        "canciones_top": detalle[:5],
        "generos": dict(generos),
    }
