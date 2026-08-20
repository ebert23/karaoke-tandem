"""Lógica de negocio de Canciones: alta, listado, votación, favoritos, top 10,
sugerencias por género y export CSV."""
import csv
import io
import re
import unicodedata

from .. import db
from ..curated_data import SUGERENCIAS_POR_GENERO
from . import grupos as grupos_svc
from . import usuarios as usuarios_svc
from .ids import new_id, now_iso

CANCIONES_HEADERS = [
    "ID", "ID Grupo", "Título", "Artista", "Género", "Link YouTube",
    "Agregado por", "Fecha agregado", "Votos", "Veces cantada",
]


# Palabras de adorno que traen los títulos copiados de YouTube y que no
# distinguen una canción de otra: "Mientes (Video Oficial)" y "Mientes" son la
# misma. No se sacan "remix", "acustico" ni "en vivo": ahí sí puede haber dos
# pistas distintas que alguien quiera tener separadas.
_RUIDO = re.compile(
    r"\b(karaoke|version karaoke|lyrics?|letra|con letra|letras|official|oficial"
    r"|video|videoclip|audio|hd|hq|4k|1080p|full|completa|remaster|remastered)\b"
)


def _clave(titulo: str, artista: str) -> str:
    """Forma normalizada de "título de artista", para comparar duplicados.

    Ignora mayúsculas, tildes, puntuación, lo que va entre paréntesis o
    corchetes y las palabras de adorno. Así "Mientes Tan Bien" y
    "MIENTES TAN BIEN (Video Oficial) HD" caen en la misma clave.
    """
    def limpiar(s: str) -> str:
        s = unicodedata.normalize("NFKD", (s or "").strip().lower())
        s = "".join(c for c in s if not unicodedata.combining(c))
        s = re.sub(r"[\(\[][^\)\]]*[\)\]]", " ", s)
        s = _RUIDO.sub(" ", s)
        s = re.sub(r"[^a-z0-9 ]", " ", s)
        return re.sub(r"\s+", " ", s).strip()

    return f"{limpiar(titulo)}|{limpiar(artista)}"


def _video_id(link: str) -> str | None:
    """Id del video de YouTube, en cualquiera de los formatos de link.

    Dos filas con el mismo video son la misma canción aunque las hayan
    titulado distinto — es la forma más confiable de detectar el duplicado,
    porque el título lo escribe cada uno a su manera.
    """
    m = re.search(r"(?:youtu\.be/|[?&]v=|youtube\.com/embed/|youtube\.com/shorts/)([\w-]{11})", link or "")
    return m.group(1) if m else None


def buscar_duplicada(
    id_grupo: str, titulo: str, artista: str, link_youtube: str = "", excluir_id: str = ""
) -> dict | None:
    """La canción del grupo que ya representa a esta, o None.

    Existe para que la lista del grupo no junte la misma canción tres veces:
    pasaba de verdad, porque nadie revisa 50 títulos antes de agregar uno.
    """
    clave_nueva = _clave(titulo, artista)
    video_nuevo = _video_id(link_youtube)
    for row in db.fetch_all("SELECT * FROM canciones WHERE id_grupo = %s", (id_grupo,)):
        if row["id"] == excluir_id:
            continue
        if video_nuevo and _video_id(row["link_youtube"]) == video_nuevo:
            return row
        if clave_nueva != "|" and _clave(row["titulo"], row["artista"]) == clave_nueva:
            return row
    return None


class CancionDuplicada(ValueError):
    """Subclase para que el router pueda responder 400 y no confundirla con
    el otro ValueError de estas rutas ("Canción no encontrada", que es 404)."""


def duplicada(
    id_grupo: str, titulo: str, artista: str, link_youtube: str = "", excluir_id: str = ""
) -> dict | None:
    """Igual que buscar_duplicada pero en el formato que devuelve la API."""
    row = buscar_duplicada(id_grupo, titulo, artista, link_youtube, excluir_id=excluir_id)
    return _row_to_out(row, {}, set(), None) if row else None


def _error_duplicada(existente: dict) -> CancionDuplicada:
    quien = existente["agregado_por"].strip()
    detalle = f" (la agregó {quien})" if quien else ""
    return CancionDuplicada(
        f'"{existente["titulo"]}" de {existente["artista"]} ya está en la lista del grupo{detalle}'
    )


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

    existente = buscar_duplicada(id_grupo, titulo, artista, link_youtube)
    if existente is not None:
        raise _error_duplicada(existente)

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

    # Mismo control que al crear: editar es la otra forma de terminar con dos
    # filas iguales. Se excluye la propia, si no no se podría ni corregir el género.
    existente = buscar_duplicada(id_grupo, titulo, artista, link_youtube, excluir_id=id_cancion)
    if existente is not None:
        raise _error_duplicada(existente)

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


# Nombres de columna que se aceptan al importar, ya normalizados (minúsculas y
# sin tildes). Un local arma su lista en Excel con los encabezados que se le
# ocurren, y rechazarle el archivo por decir "Interprete" en vez de "Artista"
# es la clase de fricción que hace que no vuelva a intentarlo.
_ALIAS_COLUMNAS = {
    "titulo": "titulo", "title": "titulo", "cancion": "titulo", "tema": "titulo",
    "nombre": "titulo", "nombre de la cancion": "titulo",
    "artista": "artista", "artist": "artista", "interprete": "artista",
    "cantante": "artista", "autor": "artista", "grupo": "artista",
    "genero": "genero", "genre": "genero", "estilo": "genero", "categoria": "genero",
    "link youtube": "link_youtube", "link_youtube": "link_youtube", "link": "link_youtube",
    "youtube": "link_youtube", "url": "link_youtube", "video": "link_youtube",
    "enlace": "link_youtube",
}

GENERO_POR_DEFECTO = "Otro"
MAX_FILAS_IMPORTACION = 5000


def _normalizar_encabezado(s: str) -> str:
    s = unicodedata.normalize("NFKD", (s or "").strip().lower())
    s = "".join(c for c in s if not unicodedata.combining(c))
    return re.sub(r"\s+", " ", s.replace("_", " ")).strip()


def _mapear_columnas(encabezados: list[str]) -> dict[str, int]:
    """Posición de cada campo conocido dentro de la fila. Ignora el resto.

    Así el CSV que exporta la app (10 columnas, con id y contadores) se puede
    volver a importar tal cual: las columnas que no se reconocen se descartan
    en vez de romper la lectura.
    """
    mapa: dict[str, int] = {}
    for i, bruto in enumerate(encabezados):
        campo = _ALIAS_COLUMNAS.get(_normalizar_encabezado(bruto))
        if campo and campo not in mapa:
            mapa[campo] = i
    return mapa


def _indice_duplicados(id_grupo: str) -> tuple[set[str], set[str]]:
    """Claves y videos del catálogo, en memoria y de una sola consulta.

    Importar 500 filas llamando a buscar_duplicada por cada una serían 500
    lecturas de toda la tabla; acá se lee una vez y se compara en memoria.
    """
    claves: set[str] = set()
    videos: set[str] = set()
    for row in db.fetch_all("SELECT titulo, artista, link_youtube FROM canciones WHERE id_grupo = %s", (id_grupo,)):
        claves.add(_clave(row["titulo"], row["artista"]))
        vid = _video_id(row["link_youtube"])
        if vid:
            videos.add(vid)
    return claves, videos


def requiere_admin(id_grupo: str, id_usuario: str) -> None:
    """Importar toca el catálogo entero de una, así que se pide admin.

    Distinto de _verificar_permiso, que mira de quién es UNA canción: acá no
    hay una canción todavía.
    """
    grupo = grupos_svc.get_por_id(id_grupo)
    if grupo is None:
        raise ValueError("Grupo no encontrado")
    if id_usuario not in (grupo["admins"] or []):
        raise PermissionError("Solo un admin del grupo puede importar el catálogo")


def importar_csv(id_grupo: str, contenido: str, confirmar: bool = False) -> dict:
    """Lee un CSV y agrega las canciones que falten. Devuelve el resumen.

    Con confirmar=False no escribe nada: sirve para mostrar qué va a pasar
    antes de tocar el catálogo, que con 500 filas es la diferencia entre
    confiar y no animarse a apretar el botón.

    Una fila mala no aborta el archivo: se anota con su número de línea y el
    resto entra igual.
    """
    texto = contenido.lstrip("﻿")
    if not texto.strip():
        raise ValueError("El archivo está vacío")

    # Excel en español exporta con punto y coma, no con coma.
    try:
        delimitador = csv.Sniffer().sniff(texto[:4096], delimiters=",;\t|").delimiter
    except csv.Error:
        delimitador = ","

    filas = list(csv.reader(io.StringIO(texto), delimiter=delimitador))
    filas = [f for f in filas if any((c or "").strip() for c in f)]
    if not filas:
        raise ValueError("El archivo está vacío")

    columnas = _mapear_columnas(filas[0])
    if "titulo" not in columnas or "artista" not in columnas:
        encontradas = ", ".join(c.strip() for c in filas[0] if c.strip()) or "(ninguna)"
        raise ValueError(
            "El archivo necesita una fila de encabezados con al menos las columnas "
            f"Título y Artista. Se encontraron: {encontradas}"
        )

    cuerpo = filas[1:]
    if len(cuerpo) > MAX_FILAS_IMPORTACION:
        raise ValueError(
            f"El archivo tiene {len(cuerpo)} filas y el máximo es {MAX_FILAS_IMPORTACION}. "
            "Partilo en varios archivos."
        )

    claves, videos = _indice_duplicados(id_grupo)
    nuevas: list[dict] = []
    repetidas: list[dict] = []
    errores: list[dict] = []

    def celda(fila: list[str], campo: str) -> str:
        i = columnas.get(campo)
        return (fila[i] or "").strip() if i is not None and i < len(fila) else ""

    for n, fila in enumerate(cuerpo, start=2):  # 1 es el encabezado
        titulo = celda(fila, "titulo")
        artista = celda(fila, "artista")
        if not titulo:
            errores.append({"fila": n, "titulo": titulo, "artista": artista, "motivo": "Falta el título"})
            continue
        if not artista:
            errores.append({"fila": n, "titulo": titulo, "artista": artista, "motivo": "Falta el artista"})
            continue

        genero = celda(fila, "genero") or GENERO_POR_DEFECTO
        link = celda(fila, "link_youtube")
        clave = _clave(titulo, artista)
        vid = _video_id(link)

        if clave in claves or (vid and vid in videos):
            repetidas.append({"fila": n, "titulo": titulo, "artista": artista, "motivo": "Ya está en la lista"})
            continue

        # Se marcan ya como vistas para que el propio archivo no meta la misma
        # canción dos veces.
        claves.add(clave)
        if vid:
            videos.add(vid)
        nuevas.append({"titulo": titulo[:200], "artista": artista[:200],
                       "genero": genero[:60], "link_youtube": link})

    importadas = 0
    if confirmar and nuevas:
        fecha = now_iso()
        db.execute_many(
            "INSERT INTO canciones (id, id_grupo, titulo, artista, genero, link_youtube, "
            "agregado_por, fecha_agregado, votos, veces_cantada) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, 0, 0)",
            [(new_id("C"), id_grupo, c["titulo"], c["artista"], c["genero"], c["link_youtube"],
              "Importadas", fecha) for c in nuevas],
        )
        importadas = len(nuevas)

    return {
        "total_filas": len(cuerpo),
        "listas": len(nuevas),
        "importadas": importadas,
        "repetidas": repetidas[:50],
        "total_repetidas": len(repetidas),
        "errores": errores[:50],
        "total_errores": len(errores),
        "muestra": nuevas[:5],
    }


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


def get_varias_por_id(ids: list[str]) -> dict[str, dict]:
    """Trae varias canciones en UNA sola consulta, indexadas por id.

    Existe para que armar el detalle de una sesión no dispare una consulta
    por turno: cada consulta abre su propia conexión a Postgres y la base
    está en otra región, así que N+1 consultas se notaban como lentitud
    real en la vista de Karaoke (que además se refresca por sondeo).
    """
    unicos = list({i for i in ids if i})
    if not unicos:
        return {}
    rows = db.fetch_all("SELECT * FROM canciones WHERE id = ANY(%s)", (unicos,))
    return {r["id"]: _row_to_out(r, {}, set(), None) for r in rows}
