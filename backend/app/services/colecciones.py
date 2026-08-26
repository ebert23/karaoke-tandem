"""Colecciones temáticas: agrupan el catálogo por vibra o por momento de la
noche en vez de por género.

Nada se guarda en la base. La pertenencia se calcula al vuelo contra
COLECCIONES, así que las 24 salas que ya existen tienen colecciones desde el
primer deploy sin migración ni etiquetado a mano. El precio es que el dueño no
puede meter una canción suelta en una colección desde la app: para eso haría
falta una tabla de etiquetas, y se puede agregar después sin tirar esto.
"""
import html
import re
import unicodedata

from ..curated_data import COLECCIONES
from . import canciones as canciones_svc
from .ids import new_id, now_iso
from .. import db

# Debajo de esto la colección no se muestra: una fila de chips donde la mitad
# devuelve una sola canción se siente rota, y en catálogos chicos pasaría
# seguido.
MINIMO_PARA_MOSTRAR = 3

# Un artista muy corto normalizado ("rbd", "u2") aparece como pedazo de
# cualquier otro nombre. Debajo de este largo se exige coincidencia exacta.
LARGO_MINIMO_PARCIAL = 4


def _norm(s: str) -> str:
    """Minúsculas, sin tildes y sin puntuación, para comparar nombres.

    Pasa por html.unescape primero porque los títulos y artistas copiados de
    YouTube llegan con entidades: en la base real hay un "JESSE &amp; JOY" que
    sin esto se normaliza a "jesse amp joy" y no coincide con nada.
    """
    s = html.unescape(s or "")
    s = unicodedata.normalize("NFKD", s.strip().lower())
    s = "".join(c for c in s if not unicodedata.combining(c))
    s = re.sub(r"[^a-z0-9 ]", " ", s)
    return re.sub(r"\s+", " ", s).strip()


def _preparar(col: dict) -> dict:
    """Índices de una colección, calculados una sola vez al importar."""
    artistas = [_norm(a) for a in col["artistas"]]
    largos = [a for a in artistas if len(a) >= LARGO_MINIMO_PARCIAL]
    # Con límites de palabra y no subcadena suelta: "mana" tiene que enganchar
    # a "Santana ft. Maná" sin enganchar a "Santana" a secas.
    patron = re.compile(r"\b(?:%s)\b" % "|".join(re.escape(a) for a in largos)) if largos else None
    return {
        **col,
        "_artistas_exactos": {a for a in artistas if a},
        "_artistas_re": patron,
        "_artistas_largos": largos,
        "_generos": [_norm(g) for g in col["generos"] if _norm(g)],
        "_claves": {canciones_svc._clave(t, a) for t, a, _ in col["canciones"]},
        "_titulos": {_norm(t) for t, _, _ in col["canciones"]},
    }


_PREPARADAS: list[dict] = [_preparar(c) for c in COLECCIONES]
_POR_ID: dict[str, dict] = {c["id"]: c for c in _PREPARADAS}


def _pertenece(row: dict, col: dict) -> bool:
    """Tres vías, y con una alcanza.

    Es generoso a propósito. Con catálogos de 50-100 temas, exigir que el
    título esté en la lista curada deja colecciones de dos canciones, que es
    lo mismo que no tenerlas.
    """
    artista = _norm(row["artista"])
    if artista:
        if artista in col["_artistas_exactos"]:
            return True
        if col["_artistas_re"] and col["_artistas_re"].search(artista):
            return True
        # Al revés: el catálogo real tiene "Pedro Suarez" a secas donde la
        # colección dice "Pedro Suárez-Vértiz". Prefijo y no subcadena, para
        # no confundir a dos artistas que apenas comparten unas letras.
        if len(artista) >= LARGO_MINIMO_PARCIAL + 1 and any(
            a.startswith(artista + " ") for a in col["_artistas_largos"]
        ):
            return True

    genero = _norm(row["genero"])
    # Subcadena y no igualdad: el género es texto libre y en la base real hay
    # "Rock en Español", "Hard Rock en Español" y "Synthpop / Rock en Español"
    # conviviendo. Compararlos enteros no acertaría casi ninguno.
    if genero and any(g in genero for g in col["_generos"]):
        return True

    if canciones_svc._clave(row["titulo"], row["artista"]) in col["_claves"]:
        return True
    # Mismo título, otro artista: en el catálogo real los covers vienen
    # atribuidos a quien los subió a YouTube, no a quien la hizo famosa.
    return _norm(row["titulo"]) in col["_titulos"]


def _filas(id_grupo: str) -> list[dict]:
    return db.fetch_all("SELECT * FROM canciones WHERE id_grupo = %s", (id_grupo,))


def listar(id_grupo: str) -> list[dict]:
    """Las colecciones con al menos MINIMO_PARA_MOSTRAR canciones en el grupo.

    Una sola consulta al catálogo: el conteo de las 14 se hace en memoria.
    """
    filas = _filas(id_grupo)
    salida = []
    for col in _PREPARADAS:
        total = sum(1 for row in filas if _pertenece(row, col))
        if total >= MINIMO_PARA_MOSTRAR:
            salida.append(
                {
                    "id": col["id"],
                    "nombre": col["nombre"],
                    "emoji": col["emoji"],
                    "descripcion": col["descripcion"],
                    "color": col["color"],
                    "total": total,
                    "disponibles_para_cargar": 0,
                }
            )
    return salida


def catalogo(id_grupo: str) -> list[dict]:
    """Todas las colecciones, incluso las vacías, con cuántas se podrían
    cargar del pack curado. Es la vista del dueño, no la del que va a cantar."""
    filas = _filas(id_grupo)
    claves = {canciones_svc._clave(f["titulo"], f["artista"]) for f in filas}
    salida = []
    for col in _PREPARADAS:
        faltan = sum(1 for t, a, _ in col["canciones"] if canciones_svc._clave(t, a) not in claves)
        salida.append(
            {
                "id": col["id"],
                "nombre": col["nombre"],
                "emoji": col["emoji"],
                "descripcion": col["descripcion"],
                "color": col["color"],
                "total": sum(1 for row in filas if _pertenece(row, col)),
                "disponibles_para_cargar": faltan,
            }
        )
    return salida


def canciones_de(id_grupo: str, id_coleccion: str, id_usuario: str | None = None) -> list[dict]:
    col = _POR_ID.get(id_coleccion)
    if not col:
        raise ValueError("Colección no encontrada")
    todas = canciones_svc.listar(id_grupo, id_usuario=id_usuario)
    dentro = [c for c in todas if _pertenece(c, col)]
    # Las curadas primero: son las que la colección promete, y en un catálogo
    # grande quedarían enterradas entre las que entraron por artista o género.
    dentro.sort(
        key=lambda c: (
            canciones_svc._clave(c["titulo"], c["artista"]) not in col["_claves"],
            -c["votos"],
            -c["veces_cantada"],
            c["titulo"].lower(),
        )
    )
    return dentro


def cargar_pack(id_grupo: str, id_coleccion: str, confirmar: bool = False) -> dict:
    """Agrega al catálogo las curadas de la colección que el grupo no tenga.

    Misma forma de dos pasos que la importación de CSV: con confirmar=false
    devuelve el resumen sin escribir. Los links de YouTube quedan vacíos por la
    misma razón de siempre — la cuota de la API son 100 búsquedas por día para
    toda la app, y un pack son 14 canciones.
    """
    col = _POR_ID.get(id_coleccion)
    if not col:
        raise ValueError("Colección no encontrada")

    claves, _videos = canciones_svc._indice_duplicados(id_grupo)
    nuevas = []
    for titulo, artista, genero in col["canciones"]:
        clave = canciones_svc._clave(titulo, artista)
        if clave in claves:
            continue
        claves.add(clave)
        nuevas.append({"titulo": titulo, "artista": artista, "genero": genero, "link_youtube": ""})

    if confirmar and nuevas:
        ahora = now_iso()
        db.execute_many(
            "INSERT INTO canciones (id, id_grupo, titulo, artista, genero, link_youtube,"
            " agregado_por, fecha_agregado, votos, veces_cantada)"
            " VALUES (%s, %s, %s, %s, %s, %s, %s, %s, 0, 0)",
            [
                (new_id("C"), id_grupo, c["titulo"], c["artista"], c["genero"], "",
                 col["nombre"], ahora)
                for c in nuevas
            ],
        )

    return {
        "id_coleccion": col["id"],
        "nombre": col["nombre"],
        "listas": len(nuevas),
        "importadas": len(nuevas) if confirmar else 0,
        "ya_estaban": len(col["canciones"]) - len(nuevas),
        "muestra": nuevas[:8],
    }


def requiere_admin(id_grupo: str, id_usuario: str) -> None:
    """Cargar un pack escribe en el catálogo del grupo: mismo permiso que
    importar un CSV, y la regla vive en un solo lugar."""
    canciones_svc.requiere_admin(id_grupo, id_usuario)
