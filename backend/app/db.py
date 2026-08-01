"""Cliente de Postgres (Supabase): conexión por request + helpers de consulta.

Reemplaza a sheets_client.py como capa de acceso a datos. Usa el connection
string con pooler de Supabase (puerto 6543, modo transacción/pgbouncer) —
el pooling de conexiones lo hace pgbouncer del lado de Supabase, así que acá
NO se mantiene un pool local de psycopg_pool: en Vercel (serverless, procesos
que se congelan/descongelan entre invocaciones) el hilo de fondo que
psycopg_pool usa para mantener el pool no sobrevive bien ese ciclo y termina
en PoolTimeout ("couldn't get a connection").

Lo que sí se hace es reusar UNA conexión por request HTTP (ver request_scope,
que main.py engancha como middleware). Abrir una conexión nueva por consulta
era carísimo: la base está en otra región que la función de Vercel, así que
cada apertura paga handshake TCP+TLS+auth cruzando el continente, y una vista
como el detalle de una sesión (que además se refresca por sondeo) hacía una
consulta por turno. La conexión se abre de forma perezosa —en la primera
consulta real— para que los requests que no tocan la base (archivos
estáticos del frontend, health) no paguen nada.

Si no hay request_scope activo (scripts, tests directos) cada helper abre y
cierra su propia conexión, igual que antes.

autocommit=True porque cada fetch_all/fetch_one/execute es independiente
(no hay transacciones multi-paso en la app) — mismo modelo que tenía cada
llamada a SheetTable antes. Además evita que una consulta fallida deje la
conexión compartida en estado abortado para el resto del request.

prepare_threshold=None: el pooler de Supabase (modo transacción) no sostiene
los prepared statements de psycopg entre conexiones reutilizadas — sin esto
aparece "DuplicatePreparedStatement".
"""
from contextlib import contextmanager
from contextvars import ContextVar
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


class _ConexionDeRequest:
    """Sostiene la conexión de un request, abriéndola recién cuando se usa."""

    def __init__(self) -> None:
        self.conn: psycopg.Connection | None = None

    def obtener(self) -> psycopg.Connection:
        if self.conn is None or self.conn.closed:
            self.conn = _connect()
        return self.conn

    def cerrar(self) -> None:
        if self.conn is not None:
            try:
                self.conn.close()
            finally:
                self.conn = None


_conexion_actual: ContextVar[_ConexionDeRequest | None] = ContextVar("conexion_actual", default=None)


@contextmanager
def request_scope():
    """Reusa una sola conexión para todas las consultas de un request."""
    titular = _ConexionDeRequest()
    token = _conexion_actual.set(titular)
    try:
        yield
    finally:
        _conexion_actual.reset(token)
        titular.cerrar()


@contextmanager
def _cursor():
    titular = _conexion_actual.get()
    if titular is not None:
        with titular.obtener().cursor() as cur:
            yield cur
    else:
        with _connect() as conn:
            with conn.cursor() as cur:
                yield cur


def fetch_all(sql: str, params: tuple = ()) -> list[dict[str, Any]]:
    with _cursor() as cur:
        cur.execute(sql, params)
        return cur.fetchall()


def fetch_one(sql: str, params: tuple = ()) -> dict[str, Any] | None:
    with _cursor() as cur:
        cur.execute(sql, params)
        return cur.fetchone()


def execute(sql: str, params: tuple = ()) -> None:
    with _cursor() as cur:
        cur.execute(sql, params)


def execute_many(sql: str, params_seq: list[tuple]) -> None:
    with _cursor() as cur:
        cur.executemany(sql, params_seq)
