"""Estadísticas personales: canciones más cantadas y géneros favoritos."""
from collections import Counter

from .. import db
from . import canciones as canciones_svc
from . import usuarios as usuarios_svc


def estadisticas(id_grupo: str, id_usuario: str) -> dict:
    usuario = usuarios_svc.get_por_id(id_grupo, id_usuario)
    if not usuario:
        raise ValueError("Usuario no encontrado")

    # "Cantada por" puede traer varios nombres separados por coma (dueto o
    # grupal); contamos la fila si el usuario figura entre ellos.
    nombre_lower = usuario["nombre"].strip().lower()
    rows = db.fetch_all(
        "SELECT * FROM canciones_sesion WHERE id_grupo = %s AND estado = 'Cantada'", (id_grupo,)
    )
    filas = [
        r for r in rows
        if nombre_lower in [n.strip().lower() for n in r["cantada_por"].split(",") if n.strip()]
    ]

    detalle = []
    generos = Counter()
    puntuaciones = []
    for r in filas:
        cancion = canciones_svc.get_por_id(r["id_cancion"])
        if not cancion:
            continue
        puntuacion = r["puntuacion"]
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
