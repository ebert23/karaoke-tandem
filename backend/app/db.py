"""Cliente de Postgres (Supabase): pool de conexiones + helpers de consulta.

Reemplaza a sheets_client.py como capa de acceso a datos. Usa el connection
string con pooler de Supabase (puerto 6543, modo transacción/pgbouncer):
imprescindible en serverless, porque cada invocación podría abrir una
conexión nueva y agotar el límite de conexiones directas de Postgres.

autocommit=True porque cada fetch_all/fetch_one/execute es independiente
(no hay transacciones multi-paso en la app) — mismo modelo que tenía cada
llamada a SheetTable antes.
"""
from functools import lru_cache
from typing import Any

from psycopg.rows import dict_row
from psycopg_pool import ConnectionPool

from .config import settings


@lru_cache
def _get_pool() -> ConnectionPool:
    return ConnectionPool(
        settings.database_url,
        min_size=0,
        max_size=5,
        # prepare_threshold=None: el pooler de Supabase (puerto 6543, modo
        # transacción/pgbouncer) no sostiene los prepared statements de
        # psycopg entre conexiones reutilizadas — sin esto, tras varias
        # queries aparece "DuplicatePreparedStatement".
        kwargs={"row_factory": dict_row, "autocommit": True, "prepare_threshold": None},
    )


def fetch_all(sql: str, params: tuple = ()) -> list[dict[str, Any]]:
    with _get_pool().connection() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, params)
            return cur.fetchall()


def fetch_one(sql: str, params: tuple = ()) -> dict[str, Any] | None:
    with _get_pool().connection() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, params)
            return cur.fetchone()


def execute(sql: str, params: tuple = ()) -> None:
    with _get_pool().connection() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, params)


def execute_many(sql: str, params_seq: list[tuple]) -> None:
    with _get_pool().connection() as conn:
        with conn.cursor() as cur:
            cur.executemany(sql, params_seq)
