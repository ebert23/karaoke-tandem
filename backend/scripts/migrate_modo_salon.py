"""Migración al modo salón: columnas y tablas nuevas sobre la base existente.

schema.sql solo tiene "create table if not exists", así que no alcanza para
agregarle columnas a tablas que ya existen en producción. Este script aplica
esos ALTER de forma idempotente (todos con IF NOT EXISTS), y se puede correr
tantas veces como haga falta sin romper nada ni tocar los datos que ya están.

Los grupos que ya existen quedan en modo 'grupo' por el default de la columna,
o sea que su comportamiento actual no cambia.

Uso:
    cd backend
    python scripts/migrate_modo_salon.py

Requiere DATABASE_URL en el entorno (o backend/.env).
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app import db  # noqa: E402

PASOS = [
    (
        "grupos.modo",
        "ALTER TABLE grupos ADD COLUMN IF NOT EXISTS modo text NOT NULL DEFAULT 'grupo'",
    ),
    (
        "grupos.codigo_dj",
        "ALTER TABLE grupos ADD COLUMN IF NOT EXISTS codigo_dj text NOT NULL DEFAULT ''",
    ),
    (
        "canciones_sesion.id_mesa",
        "ALTER TABLE canciones_sesion ADD COLUMN IF NOT EXISTS id_mesa text",
    ),
    (
        "canciones_sesion.pedido_por",
        "ALTER TABLE canciones_sesion ADD COLUMN IF NOT EXISTS pedido_por text NOT NULL DEFAULT ''",
    ),
    (
        "canciones_sesion.ronda",
        "ALTER TABLE canciones_sesion ADD COLUMN IF NOT EXISTS ronda int NOT NULL DEFAULT 0",
    ),
    (
        "canciones_sesion.fecha_pedido",
        "ALTER TABLE canciones_sesion ADD COLUMN IF NOT EXISTS fecha_pedido text NOT NULL DEFAULT ''",
    ),
    (
        "canciones_sesion.fecha_cantada",
        "ALTER TABLE canciones_sesion ADD COLUMN IF NOT EXISTS fecha_cantada text NOT NULL DEFAULT ''",
    ),
    (
        "idx_cs_mesa",
        "CREATE INDEX IF NOT EXISTS idx_cs_mesa ON canciones_sesion(id_mesa)",
    ),
    (
        "tabla mesas",
        """
        CREATE TABLE IF NOT EXISTS mesas (
            id text PRIMARY KEY,
            id_grupo text NOT NULL REFERENCES grupos(id),
            numero text NOT NULL,
            codigo text NOT NULL UNIQUE,
            tamano int NOT NULL DEFAULT 2,
            cupo_por_ronda int NOT NULL DEFAULT 2,
            estado text NOT NULL DEFAULT 'Cerrada',
            id_sesion text,
            ronda_base int NOT NULL DEFAULT 0,
            fecha_apertura text NOT NULL DEFAULT ''
        )
        """,
    ),
    (
        "idx_mesas_grupo",
        "CREATE INDEX IF NOT EXISTS idx_mesas_grupo ON mesas(id_grupo)",
    ),
    (
        "idx_mesas_grupo_numero",
        "CREATE UNIQUE INDEX IF NOT EXISTS idx_mesas_grupo_numero ON mesas(id_grupo, numero)",
    ),
    (
        "tabla sugerencias_mesa",
        """
        CREATE TABLE IF NOT EXISTS sugerencias_mesa (
            id bigserial PRIMARY KEY,
            id_grupo text NOT NULL REFERENCES grupos(id),
            id_sesion text NOT NULL,
            id_mesa text NOT NULL,
            titulo text NOT NULL,
            artista text NOT NULL DEFAULT '',
            pedido_por text NOT NULL DEFAULT '',
            fecha text NOT NULL
        )
        """,
    ),
    (
        "idx_sug_mesa_sesion",
        "CREATE INDEX IF NOT EXISTS idx_sug_mesa_sesion ON sugerencias_mesa(id_sesion)",
    ),
]


def main() -> int:
    for nombre, sql in PASOS:
        db.execute(sql)
        print(f"[OK ] {nombre}")

    # Verificación: los grupos que ya existían tienen que haber quedado todos
    # en modo 'grupo'. Si alguno quedó en otra cosa es que la migración corrió
    # sobre una base que no es la esperada.
    print()
    for row in db.fetch_all("SELECT modo, COUNT(*) AS n FROM grupos GROUP BY modo ORDER BY modo"):
        print(f"grupos en modo {row['modo']!r}: {row['n']}")

    pedidos = db.fetch_one("SELECT COUNT(*) AS n FROM canciones_sesion WHERE id_mesa IS NOT NULL")
    print(f"filas de canciones_sesion con mesa asignada: {pedidos['n']} (esperado 0 en la primera corrida)")
    print("\nMigración completa.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
