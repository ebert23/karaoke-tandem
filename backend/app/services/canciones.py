"""Lógica de negocio de Canciones: alta, listado, votación, favoritos, top 10,
sugerencias por género y export CSV."""
import csv
import io

from .. import db
from ..curated_data import SUGERENCIAS_POR_GENERO
from . import grupos as grupos_svc
from . import usuarios as usuarios_svc
from .ids import new_id, now_iso

CANCIONES_HEADERS = [
    "ID", "ID Grupo", "Título", "Artista", "Género", "Link YouTube",
    "Agregado por", "Fecha agregado", "Votos", "Veces cantada",
]


def _row_to_out(
    row: dict,
    votantes_por_cancion: dict[str, set[str]],
    favoritos_usuario: set[str],
    id_usuario: str | None,
) -> dict:
    votantes = votantes_por_cancion.get(row["id"], set())
    return {
        "id": row["id"],
        "titulo": row["titulo"],
        "artista": row["artista"],
        "genero": row["genero"],
        "link_youtube": row["link_youtube"],
        "agregado_por": row["agregado_por"],
        "fecha_agregado": row["fecha_agregado"],
        "votos": row["votos"],
        "veces_cantada": row["veces_cantada"],
        "ya_voto": bool(id_usuario) and id_usuario in votantes,
        "es_favorita": row["id"] in favoritos_usuario,
    }


def _votantes_por_cancion(id_grupo: str) -> dict[str, set[str]]:
    mapa: dict[str, set[str]] = {}
    for v in db.fetch_all("SELECT id_cancion, id_usuario FROM votos WHERE id_grupo = %s", (id_grupo,)):
        mapa.setdefault(v["id_cancion"], set()).add(v["id_usuario"])
    return mapa


def _favoritos_de_usuario(id_grupo: str, id_usuario: str | None) -> set[str]:
    if not id_usuario:
        return set()
    rows = db.fetch_all(
        "SELECT id_cancion FROM favoritos WHERE id_grupo = %s AND id_usuario = %s",
        (id_grupo, id_usuario),
    )
    return {r["id_cancion"] for r in rows}


def listar(
    id_grupo: str,
    id_usuario: str | None = None,
    genero: str | None = None,
    q: str | None = None,
    favoritas: bool = False,
) -> list[dict]:
    votantes = _votantes_por_cancion(id_grupo)
    favoritos = _favoritos_de_usuario(id_grupo, id_usuario)
    rows = db.fetch_all("SELECT * FROM canciones WHERE id_grupo = %s", (id_grupo,))
    out = [_row_to_out(r, votantes, favoritos, id_usuario) for r in rows]
    if genero:
        out = [c for c in out if c["genero"].lower() == genero.lower()]
    if q:
        ql = q.lower()
        out = [c for c in out if ql in c["titulo"].lower() or ql in c["artista"].lower()]
    if favoritas:
        out = [c for c in out if c["es_favorita"]]
    return out


def top10(id_grupo: str, id_usuario: str | None = None) -> list[dict]:
    out = listar(id_grupo, id_usuario)
    out.sort(key=lambda c: c["votos"], reverse=True)
    return out[:10]


def crear(id_grupo: str, data) -> dict:
    id_cancion = new_id("C")
    fecha_agregado = now_iso()
    titulo = data.titulo.strip()
    artista = data.artista.strip()
    genero = data.genero.strip()
    link_youtube = data.link_youtube.strip()
    agregado_por = data.agregado_por.strip()
    db.execute(
        "INSERT INTO canciones (id, id_grupo, titulo, artista, genero, link_youtube, "
        "agregado_por, fecha_agregado, votos, veces_cantada) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, 0, 0)",
        (id_cancion, id_grupo, titulo, artista, genero, link_youtube, agregado_por, fecha_agregado),
    )
    return {
        "id": id_cancion, "titulo": titulo, "artista": artista, "genero": genero,
        "link_youtube": link_youtube, "agregado_por": agregado_por, "fecha_agregado": fecha_agregado,
        "votos": 0, "veces_cantada": 0, "ya_voto": False, "es_favorita": False,
    }


def _verificar_permiso(id_grupo: str, cancion_row: dict, id_usuario: str) -> None:
    """Solo quien agregó la canción (por nombre, igual que el resto de la app
    identifica "de quién es" algo) o un admin del grupo puede editarla/borrarla."""
    usuario = usuarios_svc.get_por_id(id_grupo, id_usuario)
    if not usuario:
        raise PermissionError("Usuario no encontrado en este grupo")
    es_autor = cancion_row["agregado_por"].strip().lower() == usuario["nombre"].strip().lower()
    if es_autor:
        return
    grupo = grupos_svc.get_por_id(id_grupo)
    if grupo and id_usuario in grupo["admins"]:
        return
    raise PermissionError("Solo quien agregó esta canción o un admin del grupo puede modificarla")


def actualizar(id_grupo: str, id_cancion: str, id_usuario: str, data) -> dict:
    row = db.fetch_one("SELECT * FROM canciones WHERE id = %s", (id_cancion,))
    if row is None or row["id_grupo"] != id_grupo:
        raise ValueError("Canción no encontrada")
    _verificar_permiso(id_grupo, row, id_usuario)
    titulo = data.titulo.strip()
    artista = data.artista.strip()
    genero = data.genero.strip()
    link_youtube = data.link_youtube.strip()
    db.execute(
        "UPDATE canciones SET titulo = %s, artista = %s, genero = %s, link_youtube = %s WHERE id = %s",
        (titulo, artista, genero, link_youtube, id_cancion),
    )
    row.update({"titulo": titulo, "artista": artista, "genero": genero, "link_youtube": link_youtube})
    return _row_to_out(row, {}, set(), id_usuario)


def eliminar(id_grupo: str, id_cancion: str, id_usuario: str) -> None:
    row = db.fetch_one("SELECT * FROM canciones WHERE id = %s", (id_cancion,))
    if row is None or row["id_grupo"] != id_grupo:
        raise ValueError("Canción no encontrada")
    _verificar_permiso(id_grupo, row, id_usuario)
    db.execute("DELETE FROM canciones WHERE id = %s", (id_cancion,))


def votar(id_grupo: str, id_cancion: str, id_usuario: str) -> dict:
    """Alterna el voto del usuario sobre una canción (votar / quitar voto)."""
    cancion_row = db.fetch_one("SELECT * FROM canciones WHERE id = %s", (id_cancion,))
    if cancion_row is None or cancion_row["id_grupo"] != id_grupo:
        raise ValueError("Canción no encontrada")

    existente = db.fetch_one(
        "SELECT id_voto FROM votos WHERE id_cancion = %s AND id_usuario = %s", (id_cancion, id_usuario)
    )
    votos_actuales = cancion_row["votos"]

    if existente:
        db.execute("DELETE FROM votos WHERE id_voto = %s", (existente["id_voto"],))
        nuevos_votos = max(0, votos_actuales - 1)
        ya_voto = False
    else:
        db.execute(
            "INSERT INTO votos (id_voto, id_grupo, id_cancion, id_usuario, fecha) VALUES (%s, %s, %s, %s, %s)",
            (new_id("V"), id_grupo, id_cancion, id_usuario, now_iso()),
        )
        nuevos_votos = votos_actuales + 1
        ya_voto = True

    db.execute("UPDATE canciones SET votos = %s WHERE id = %s", (nuevos_votos, id_cancion))
    cancion_row["votos"] = nuevos_votos
    out = _row_to_out(cancion_row, {}, set(), None)
    out["ya_voto"] = ya_voto
    return out


def favorito_toggle(id_grupo: str, id_cancion: str, id_usuario: str) -> dict:
    """Alterna la canción como favorita para ese usuario."""
    cancion_row = db.fetch_one("SELECT * FROM canciones WHERE id = %s", (id_cancion,))
    if cancion_row is None or cancion_row["id_grupo"] != id_grupo:
        raise ValueError("Canción no encontrada")

    existente = db.fetch_one(
        "SELECT 1 FROM favoritos WHERE id_grupo = %s AND id_cancion = %s AND id_usuario = %s",
        (id_grupo, id_cancion, id_usuario),
    )
    if existente:
        db.execute(
            "DELETE FROM favoritos WHERE id_grupo = %s AND id_cancion = %s AND id_usuario = %s",
            (id_grupo, id_cancion, id_usuario),
        )
        es_favorita = False
    else:
        db.execute(
            "INSERT INTO favoritos (id_grupo, id_usuario, id_cancion, fecha) VALUES (%s, %s, %s, %s)",
            (id_grupo, id_usuario, id_cancion, now_iso()),
        )
        es_favorita = True

    out = _row_to_out(cancion_row, {}, {id_cancion} if es_favorita else set(), None)
    out["es_favorita"] = es_favorita
    return out


def sugerencias(genero: str | None = None) -> list[dict]:
    if genero:
        pares = SUGERENCIAS_POR_GENERO.get(genero, [])
        return [{"titulo": t, "artista": a, "genero": genero} for t, a in pares]
    resultado = []
    for g, pares in SUGERENCIAS_POR_GENERO.items():
        resultado.extend({"titulo": t, "artista": a, "genero": g} for t, a in pares)
    return resultado


def exportar_csv(id_grupo: str) -> str:
    rows = db.fetch_all("SELECT * FROM canciones WHERE id_grupo = %s", (id_grupo,))
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(CANCIONES_HEADERS)
    for r in rows:
        writer.writerow([
            r["id"], r["id_grupo"], r["titulo"], r["artista"], r["genero"], r["link_youtube"],
            r["agregado_por"], r["fecha_agregado"], r["votos"], r["veces_cantada"],
        ])
    return buf.getvalue()


def registrar_cantada(id_cancion: str) -> None:
    db.execute("UPDATE canciones SET veces_cantada = veces_cantada + 1 WHERE id = %s", (id_cancion,))


def get_por_id(id_cancion: str) -> dict | None:
    row = db.fetch_one("SELECT * FROM canciones WHERE id = %s", (id_cancion,))
    if row is None:
        return None
    return _row_to_out(row, {}, set(), None)
