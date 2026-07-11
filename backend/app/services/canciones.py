"""Lógica de negocio de Canciones: alta, listado, votación, favoritos, top 10,
sugerencias por género y export CSV."""
import csv
import io

from ..sheets_client import SUGERENCIAS_POR_GENERO, SheetTable
from .ids import new_id, now_iso


def _table() -> SheetTable:
    return SheetTable("Canciones")


def _votos_table() -> SheetTable:
    return SheetTable("Votos")


def _favoritos_table() -> SheetTable:
    return SheetTable("Favoritos")


def _row_to_out(
    row: dict,
    votantes_por_cancion: dict[str, set[str]],
    favoritos_usuario: set[str],
    id_usuario: str | None,
) -> dict:
    votantes = votantes_por_cancion.get(row["ID"], set())
    return {
        "id": row["ID"],
        "titulo": row["Título"],
        "artista": row["Artista"],
        "genero": row["Género"],
        "link_youtube": row["Link YouTube"],
        "agregado_por": row["Agregado por"],
        "fecha_agregado": row["Fecha agregado"],
        "votos": int(row["Votos"] or 0),
        "veces_cantada": int(row["Veces cantada"] or 0),
        "ya_voto": bool(id_usuario) and id_usuario in votantes,
        "es_favorita": row["ID"] in favoritos_usuario,
    }


def _votantes_por_cancion(id_grupo: str) -> dict[str, set[str]]:
    mapa: dict[str, set[str]] = {}
    for v in _votos_table().all_rows():
        if v["ID Grupo"] != id_grupo:
            continue
        mapa.setdefault(v["ID Canción"], set()).add(v["ID Usuario"])
    return mapa


def _favoritos_de_usuario(id_grupo: str, id_usuario: str | None) -> set[str]:
    if not id_usuario:
        return set()
    return {
        f["ID Canción"]
        for f in _favoritos_table().all_rows()
        if f["ID Grupo"] == id_grupo and f["ID Usuario"] == id_usuario
    }


def listar(
    id_grupo: str,
    id_usuario: str | None = None,
    genero: str | None = None,
    q: str | None = None,
    favoritas: bool = False,
) -> list[dict]:
    votantes = _votantes_por_cancion(id_grupo)
    favoritos = _favoritos_de_usuario(id_grupo, id_usuario)
    rows = [r for r in _table().all_rows() if r["ID Grupo"] == id_grupo]
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
    row = {
        "ID": new_id("C"),
        "ID Grupo": id_grupo,
        "Título": data.titulo.strip(),
        "Artista": data.artista.strip(),
        "Género": data.genero.strip(),
        "Link YouTube": data.link_youtube.strip(),
        "Agregado por": data.agregado_por.strip(),
        "Fecha agregado": now_iso(),
        "Votos": 0,
        "Veces cantada": 0,
    }
    _table().append(row)
    return _row_to_out(row, {}, set(), None)


def votar(id_grupo: str, id_cancion: str, id_usuario: str) -> dict:
    """Alterna el voto del usuario sobre una canción (votar / quitar voto)."""
    canciones = _table()
    row_number, cancion_row = canciones.get_by_id("ID", id_cancion)
    if row_number is None or cancion_row["ID Grupo"] != id_grupo:
        raise ValueError("Canción no encontrada")

    votos_tabla = _votos_table()
    votos_existentes = votos_tabla.all_rows()
    existente = next(
        (v for v in votos_existentes if v["ID Canción"] == id_cancion and v["ID Usuario"] == id_usuario),
        None,
    )
    votos_actuales = int(cancion_row["Votos"] or 0)

    if existente:
        vrow, _ = votos_tabla.get_by_id("ID Voto", existente["ID Voto"])
        votos_tabla.delete_row(vrow)
        nuevos_votos = max(0, votos_actuales - 1)
        ya_voto = False
    else:
        votos_tabla.append({
            "ID Voto": new_id("V"),
            "ID Grupo": id_grupo,
            "ID Canción": id_cancion,
            "ID Usuario": id_usuario,
            "Fecha": now_iso(),
        })
        nuevos_votos = votos_actuales + 1
        ya_voto = True

    canciones.update_row(row_number, {"Votos": nuevos_votos})
    cancion_row["Votos"] = nuevos_votos
    out = _row_to_out(cancion_row, {}, set(), None)
    out["ya_voto"] = ya_voto
    return out


def favorito_toggle(id_grupo: str, id_cancion: str, id_usuario: str) -> dict:
    """Alterna la canción como favorita para ese usuario."""
    _, cancion_row = _table().get_by_id("ID", id_cancion)
    if cancion_row is None or cancion_row["ID Grupo"] != id_grupo:
        raise ValueError("Canción no encontrada")

    favoritos_tabla = _favoritos_table()
    existente = next(
        (
            f for f in favoritos_tabla.all_rows()
            if f["ID Grupo"] == id_grupo and f["ID Canción"] == id_cancion and f["ID Usuario"] == id_usuario
        ),
        None,
    )
    if existente:
        # find_row_number solo matchea por una columna; acá necesitamos la
        # combinación grupo+canción+usuario, así que se busca la fila exacta.
        for i, f in enumerate(favoritos_tabla.all_rows()):
            if f["ID Grupo"] == id_grupo and f["ID Canción"] == id_cancion and f["ID Usuario"] == id_usuario:
                favoritos_tabla.delete_row(i + 2)
                break
        es_favorita = False
    else:
        favoritos_tabla.append({
            "ID Grupo": id_grupo,
            "ID Usuario": id_usuario,
            "ID Canción": id_cancion,
            "Fecha": now_iso(),
        })
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
    rows = [r for r in _table().all_rows() if r["ID Grupo"] == id_grupo]
    buf = io.StringIO()
    writer = csv.writer(buf)
    from ..sheets_client import CANCIONES_HEADERS

    writer.writerow(CANCIONES_HEADERS)
    for r in rows:
        writer.writerow([r.get(h, "") for h in CANCIONES_HEADERS])
    return buf.getvalue()


def registrar_cantada(id_cancion: str) -> None:
    canciones = _table()
    row_number, row = canciones.get_by_id("ID", id_cancion)
    if row_number is None:
        return
    veces = int(row["Veces cantada"] or 0) + 1
    canciones.update_row(row_number, {"Veces cantada": veces})


def get_por_id(id_cancion: str) -> dict | None:
    _, row = _table().get_by_id("ID", id_cancion)
    if row is None:
        return None
    return _row_to_out(row, {}, set(), None)
