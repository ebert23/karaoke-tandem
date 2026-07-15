"""Cliente de Postgres (Supabase): conexión por llamada + helpers de consulta.

Reemplaza a sheets_client.py como capa de acceso a datos. Usa el connection
string con pooler de Supabase (puerto 6543, modo transacción/pgbouncer) —
el pooling de conexiones ya lo hace pgbouncer del lado de Supabase, así que
acá se abre una conexión nueva por llamada en vez de mantener un pool local
de psycopg_pool: en Vercel (serverless, procesos que se congelan/descongelan
entre invocaciones) el hilo de fondo que psycopg_pool usa para mantener el
pool no sobrevive bien ese ciclo y termina en PoolTimeout ("couldn't get a
connection") — abrir la conexión directa es más lento por request pero
confiable, y pgbouncer igual reutiliza la conexión física del lado del
servidor.

autocommit=True porque cada fetch_all/fetch_one/execute es independiente
(no hay transacciones multi-paso en la app) — mismo modelo que tenía cada
llamada a SheetTable antes.

prepare_threshold=None: el pooler de Supabase (modo transacción) no sostiene
los prepared statements de psycopg entre conexiones reutilizadas — sin esto
aparece "DuplicatePreparedStatement".
"""
from typing import Any

import psycopg
from psycopg.rows import dict_row

from .config import settings


def _connect() -> psycopg.Connection:
    return psycopg.connect(
        settings.database_url,
        row_factory=dict_row,
        autocommit=True,
        prepare_threshold=None,
    )


def fetch_all(sql: str, params: tuple = ()) -> list[dict[str, Any]]:
    with _connect() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, params)
            return cur.fetchall()


def fetch_one(sql: str, params: tuple = ()) -> dict[str, Any] | None:
    with _connect() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, params)
            return cur.fetchone()


def execute(sql: str, params: tuple = ()) -> None:
    with _connect() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, params)


def execute_many(sql: str, params_seq: list[tuple]) -> None:
    with _connect() as conn:
        with conn.cursor() as cur:
            cur.executemany(sql, params_seq)
