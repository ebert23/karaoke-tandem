"""Migración única de datos reales a Postgres (Supabase), leyendo desde un
export en Excel de la hoja de Google Sheets (Archivo -> Descargar -> Microsoft
Excel) en vez de pegarle a la API de Sheets — así no hace falta credencial de
Google para correr esto, alcanza con el .xlsx descargado a mano.

Inserta cada fila en la tabla Postgres correspondiente, preservando los IDs
tal cual (se referencian entre tablas). Al final relee Postgres y compara
conteos contra el Excel como verificación básica.

Idempotente: usa ON CONFLICT DO NOTHING, así que se puede volver a correr
sin duplicar filas si algo falló a mitad de camino.

Uso:
    cd backend
    python scripts/migrate_to_supabase.py "C:/ruta/al/export.xlsx"

Requiere DATABASE_URL en el entorno (o backend/.env) apuntando al connection
string con pooler de Supabase (puerto 6543).
"""
import sys
from pathlib import Path

import openpyxl

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app import db  # noqa: E402


def leer_hoja(wb, nombre: str) -> list[dict]:
    ws = wb[nombre]
    filas = ws.iter_rows(values_only=True)
    headers = next(filas)
    out = []
    for row in filas:
        if all(v is None for v in row):
            continue
        # Excel recorta las celdas vacías finales de una fila, así que puede
        # venir más corta que el encabezado — se rellena antes de zippear.
        if len(row) < len(headers):
            row = row + (None,) * (len(headers) - len(row))
        out.append({h: ("" if v is None else str(v)) for h, v in zip(headers, row)})
    return out


def _int(v, default: int = 0) -> int:
    v = str(v).strip()
    return int(v) if v.lstrip("-").isdigit() else default


def _int_or_none(v) -> int | None:
    v = str(v).strip()
    return int(v) if v.lstrip("-").isdigit() else None


def _lista(v: str) -> list[str]:
    return [p.strip() for p in v.split(",") if p.strip()]


def migrar_grupos(wb) -> int:
    rows = leer_hoja(wb, "Grupos")
    for r in rows:
        db.execute(
            "INSERT INTO grupos (id, nombre, codigo, foto, admins, fecha_creacion) "
            "VALUES (%s, %s, %s, %s, %s, %s) ON CONFLICT (id) DO NOTHING",
            (r["ID"], r["Nombre"], r["Código"], r["Foto"], _lista(r["Admins"]), r["Fecha creación"]),
        )
    print(f"grupos: {len(rows)} filas migradas")
    return len(rows)


def migrar_usuarios(wb) -> int:
    rows = leer_hoja(wb, "Usuarios")
    for r in rows:
        db.execute(
            "INSERT INTO usuarios (id, id_grupo, nombre, foto, puntos_totales, sesiones_jugadas) "
            "VALUES (%s, %s, %s, %s, %s, %s) ON CONFLICT (id) DO NOTHING",
            (r["ID"], r["ID Grupo"], r["Nombre"], r["Foto"], _int(r["Puntos totales"]), _int(r["Sesiones jugadas"])),
        )
    print(f"usuarios: {len(rows)} filas migradas")
    return len(rows)


def migrar_canciones(wb) -> int:
    rows = leer_hoja(wb, "Canciones")
    for r in rows:
        db.execute(
            "INSERT INTO canciones (id, id_grupo, titulo, artista, genero, link_youtube, "
            "agregado_por, fecha_agregado, votos, veces_cantada) "
            "VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s) ON CONFLICT (id) DO NOTHING",
            (
                r["ID"], r["ID Grupo"], r["Título"], r["Artista"], r["Género"], r["Link YouTube"],
                r["Agregado por"], r["Fecha agregado"], _int(r["Votos"]), _int(r["Veces cantada"]),
            ),
        )
    print(f"canciones: {len(rows)} filas migradas")
    return len(rows)


def migrar_sesiones(wb) -> int:
    rows = leer_hoja(wb, "Sesiones")
    for r in rows:
        db.execute(
            "INSERT INTO sesiones (id_sesion, id_grupo, fecha, participantes, estado, turno_actual) "
            "VALUES (%s, %s, %s, %s, %s, %s) ON CONFLICT (id_sesion) DO NOTHING",
            (
                r["ID Sesión"], r["ID Grupo"], r["Fecha"], _lista(r["Participantes"]),
                r["Estado"], _int(r["Turno actual"]),
            ),
        )
    print(f"sesiones: {len(rows)} filas migradas")
    return len(rows)


def migrar_retos(wb) -> int:
    rows = leer_hoja(wb, "Retos")
    for r in rows:
        db.execute(
            "INSERT INTO retos (id, id_grupo, texto, dificultad, categoria) "
            "VALUES (%s, %s, %s, %s, %s) ON CONFLICT (id) DO NOTHING",
            (r["ID"], r["ID Grupo"], r["Texto del reto"], r["Dificultad"], r["Categoría"]),
        )
    print(f"retos: {len(rows)} filas migradas")
    return len(rows)


def migrar_votos(wb) -> int:
    rows = leer_hoja(wb, "Votos")
    for r in rows:
        db.execute(
            "INSERT INTO votos (id_voto, id_grupo, id_cancion, id_usuario, fecha) "
            "VALUES (%s, %s, %s, %s, %s) ON CONFLICT (id_voto) DO NOTHING",
            (r["ID Voto"], r["ID Grupo"], r["ID Canción"], r["ID Usuario"], r["Fecha"]),
        )
    print(f"votos: {len(rows)} filas migradas")
    return len(rows)


def migrar_favoritos(wb) -> int:
    rows = leer_hoja(wb, "Favoritos")
    for r in rows:
        db.execute(
            "INSERT INTO favoritos (id_grupo, id_usuario, id_cancion, fecha) "
            "VALUES (%s, %s, %s, %s) ON CONFLICT (id_grupo, id_usuario, id_cancion) DO NOTHING",
            (r["ID Grupo"], r["ID Usuario"], r["ID Canción"], r["Fecha"]),
        )
    print(f"favoritos: {len(rows)} filas migradas")
    return len(rows)


def migrar_canciones_sesion(wb) -> int:
    rows = leer_hoja(wb, "Canciones_Sesion")
    # "orden" para las que sigan "En cola" en el momento de migrar: se
    # respeta el mismo orden físico que tenían en la hoja.
    orden_por_sesion: dict[str, int] = {}
    for r in rows:
        estado = r["Estado"]
        orden = 0
        if estado == "En cola":
            orden_por_sesion[r["ID Sesión"]] = orden_por_sesion.get(r["ID Sesión"], 0) + 1
            orden = orden_por_sesion[r["ID Sesión"]]
        db.execute(
            "INSERT INTO canciones_sesion (id_sesion, id_grupo, id_cancion, orden, turno, "
            "cantada_por, puntuacion, estado) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)",
            (
                r["ID Sesión"], r["ID Grupo"], r["ID Canción"], orden, _int(r["Turno"]),
                r["Cantada por"], _int_or_none(r["Puntuación"]), estado,
            ),
        )
    print(f"canciones_sesion: {len(rows)} filas migradas")
    return len(rows)


def migrar_votos_turno(wb) -> int:
    rows = leer_hoja(wb, "Votos_Turno")
    for r in rows:
        db.execute(
            "INSERT INTO votos_turno (id_grupo, id_sesion, id_cancion, turno, id_usuario, puntuacion, fecha) "
            "VALUES (%s, %s, %s, %s, %s, %s, %s) "
            "ON CONFLICT (id_sesion, id_cancion, turno, id_usuario) DO NOTHING",
            (
                r["ID Grupo"], r["ID Sesión"], r["ID Canción"], _int(r["Turno"]), r["ID Usuario"],
                _int(r["Puntuación"]), r["Fecha"],
            ),
        )
    print(f"votos_turno: {len(rows)} filas migradas")
    return len(rows)


def verificar(conteos: dict[str, int]) -> bool:
    print("\n--- Verificación ---")
    ok = True
    for tabla, esperado in conteos.items():
        en_pg = db.fetch_one(f"SELECT COUNT(*) AS n FROM {tabla}")["n"]
        estado = "OK" if en_pg == esperado else "MISMATCH"
        if en_pg != esperado:
            ok = False
        print(f"[{estado}] {tabla}: Excel={esperado} Postgres={en_pg}")
    print("\nTodos los conteos coinciden." if ok else "\nHay conteos que no coinciden -- revisar antes de continuar.")
    return ok


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Uso: python scripts/migrate_to_supabase.py <ruta al .xlsx exportado>")
        sys.exit(2)

    wb = openpyxl.load_workbook(sys.argv[1], read_only=True, data_only=True)

    conteos: dict[str, int] = {}
    # Orden respeta las FK: grupos primero, sesiones antes de
    # canciones_sesion/votos_turno.
    conteos["grupos"] = migrar_grupos(wb)
    conteos["usuarios"] = migrar_usuarios(wb)
    conteos["canciones"] = migrar_canciones(wb)
    conteos["sesiones"] = migrar_sesiones(wb)
    conteos["retos"] = migrar_retos(wb)
    conteos["votos"] = migrar_votos(wb)
    conteos["favoritos"] = migrar_favoritos(wb)
    conteos["canciones_sesion"] = migrar_canciones_sesion(wb)
    conteos["votos_turno"] = migrar_votos_turno(wb)

    ok = verificar(conteos)
    sys.exit(0 if ok else 1)
