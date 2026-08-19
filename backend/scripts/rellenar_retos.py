"""Lleva los retos por defecto nuevos a los grupos que ya existían.

seed_default_retos solo corre al crear un grupo, así que ampliar
DEFAULT_RETOS no le sirve a nadie que ya esté jugando: los 23 grupos
existentes se quedaban con los 12 originales, y con dos categorías de apenas
2 retos cada una salía siempre el mismo.

Es idempotente y solo agrega: compara por texto normalizado (sin mayúsculas,
tildes ni puntuación) contra lo que el grupo ya tiene, así que correrlo dos
veces no duplica nada, y nunca toca ni borra los retos que el grupo escribió
por su cuenta.

    backend/.venv_check/Scripts/python.exe backend/scripts/rellenar_retos.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app import db  # noqa: E402
from app.curated_data import DEFAULT_RETOS  # noqa: E402
from app.services.ids import new_id  # noqa: E402
from app.services.retos import _clave  # noqa: E402


def main() -> None:
    grupos = db.fetch_all("SELECT id, nombre FROM grupos ORDER BY nombre")
    print(f"{len(grupos)} grupos, {len(DEFAULT_RETOS)} retos por defecto\n")

    total_agregados = 0
    for grupo in grupos:
        existentes = {
            _clave(r["texto"])
            for r in db.fetch_all("SELECT texto FROM retos WHERE id_grupo = %s", (grupo["id"],))
        }
        faltantes = [
            (new_id("R"), grupo["id"], texto, dificultad, categoria)
            for texto, dificultad, categoria in DEFAULT_RETOS
            if _clave(texto) not in existentes
        ]
        if not faltantes:
            print(f"  {grupo['nombre']}: ya estaba completo")
            continue

        db.execute_many(
            "INSERT INTO retos (id, id_grupo, texto, dificultad, categoria) VALUES (%s, %s, %s, %s, %s)",
            faltantes,
        )
        total_agregados += len(faltantes)
        print(f"  {grupo['nombre']}: +{len(faltantes)} retos")

    print(f"\nAgregados en total: {total_agregados}")

    print("\nComo queda cada categoria (minimo entre todos los grupos):")
    for categoria in ("Normal", "Picante", "Creativo", "Grupo"):
        fila = db.fetch_one(
            "SELECT MIN(n) AS minimo, MAX(n) AS maximo FROM ("
            "  SELECT COUNT(*) AS n FROM retos WHERE categoria = %s GROUP BY id_grupo"
            ") t",
            (categoria,),
        )
        print(f"  {categoria:9} {fila['minimo']}-{fila['maximo']} retos por grupo")


if __name__ == "__main__":
    main()
