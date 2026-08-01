"""Lógica de negocio de Mesas (modo salón).

Una mesa es una mesa física del salón, con su QR pegado encima. El ciclo de
vida es por noche: el local la abre cuando se sienta gente y la cierra cuando
se va.

Cerrarla cancela sus pedidos pendientes a propósito. Es el fallo más común de
estos sistemas: si los pedidos sobreviven, el DJ termina llamando al micrófono
a una mesa que ya pagó y se fue, y la noche se corta.
"""
import secrets

from .. import db
from .ids import new_id, now_iso

# Alfabeto sin caracteres ambiguos (falta I, O, 0, 1): el código va en el QR
# pero también se puede tipear a mano cuando la cámara no coopera — luz baja,
# lente sucio, celular viejo — y "I" contra "1" a oscuras es una pelea perdida.
_ALFABETO_CODIGO = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"
_LARGO_CODIGO = 8


def _codigo_unico() -> str:
    """Código del QR: 8 caracteres sobre 32 posibles (~1.1e12 combinaciones).

    Deliberadamente mucho más largo que los 6 dígitos de los grupos: ese
    espacio (un millón) se enumera con un script en minutos, y acá el que
    adivina un código puede encolar canciones en un local sin estar adentro.
    """
    existentes = {r["codigo"] for r in db.fetch_all("SELECT codigo FROM mesas")}
    while True:
        codigo = "".join(secrets.choice(_ALFABETO_CODIGO) for _ in range(_LARGO_CODIGO))
        if codigo not in existentes:
            return codigo


def cupo_para(tamano: int) -> int:
    """Cuántas canciones seguidas puede meter la mesa en una misma ronda.

    Una mesa de una persona mete una; de dos o más, dos. Así una mesa grande
    canta más que una chica (que es lo justo por cabeza) sin que eso obligue a
    las demás a esperar una vuelta entera, que es lo que pasaría si a cada
    mesa se le dieran sus 2 canciones en bloque.
    """
    return 1 if tamano <= 1 else 2


def _row_to_out(row: dict) -> dict:
    return {
        "id": row["id"],
        "numero": row["numero"],
        "codigo": row["codigo"],
        "tamano": row["tamano"],
        "cupo_por_ronda": row["cupo_por_ronda"],
        "estado": row["estado"],
        "id_sesion": row["id_sesion"],
        "fecha_apertura": row["fecha_apertura"],
    }


def listar(id_grupo: str) -> list[dict]:
    rows = db.fetch_all(
        # El orden natural de "mesa 2, mesa 10" es alfabético y quedaría
        # 10 antes que 2. Se ordena por el número cuando el texto es
        # numérico, y alfabéticamente para los nombres ("Barra 3", "VIP").
        "SELECT * FROM mesas WHERE id_grupo = %s "
        "ORDER BY (numero ~ '^[0-9]+$') DESC, "
        "         CASE WHEN numero ~ '^[0-9]+$' THEN numero::int ELSE NULL END ASC, "
        "         numero ASC",
        (id_grupo,),
    )
    return [_row_to_out(r) for r in rows]


def get_por_id(id_grupo: str, id_mesa: str) -> dict | None:
    row = db.fetch_one("SELECT * FROM mesas WHERE id = %s", (id_mesa,))
    if row is None or row["id_grupo"] != id_grupo:
        return None
    return _row_to_out(row)


def get_row_por_codigo(codigo: str) -> dict | None:
    """Fila cruda de la mesa a partir del código del QR. Devuelve la fila
    entera (no _row_to_out) porque quien la usa necesita id_grupo y
    ronda_base, que no van en la respuesta pública."""
    return db.fetch_one("SELECT * FROM mesas WHERE codigo = %s", (codigo.strip().upper(),))


def crear(id_grupo: str, numero: str, tamano: int = 2) -> dict:
    numero = numero.strip()
    if not numero:
        raise ValueError("La mesa necesita un número o nombre")
    existente = db.fetch_one("SELECT id FROM mesas WHERE id_grupo = %s AND numero = %s", (id_grupo, numero))
    if existente is not None:
        raise ValueError(f"Ya existe una mesa {numero} en este local")

    row = db.fetch_one(
        "INSERT INTO mesas (id, id_grupo, numero, codigo, tamano, cupo_por_ronda, estado, ronda_base, fecha_apertura) "
        "VALUES (%s, %s, %s, %s, %s, %s, 'Cerrada', 0, '') RETURNING *",
        (new_id("M"), id_grupo, numero, _codigo_unico(), tamano, cupo_para(tamano)),
    )
    return _row_to_out(row)


def abrir(id_grupo: str, id_mesa: str, id_sesion: str, ronda_base: int, tamano: int | None = None) -> dict:
    """Sienta gente en la mesa y la mete en la rotación de la noche.

    `ronda_base` es la ronda que está corriendo ahora mismo en el salón (la
    calcula sesiones._ronda_actual_salon). Guardarla es lo que hace que una
    mesa que llega a las 11 de la noche entre en la vuelta en curso, en vez de
    colarse al principio de la cola o quedar detrás de todo lo ya pedido.
    """
    row = db.fetch_one("SELECT * FROM mesas WHERE id = %s", (id_mesa,))
    if row is None or row["id_grupo"] != id_grupo:
        raise ValueError("Mesa no encontrada")

    nuevo_tamano = row["tamano"] if tamano is None else max(1, tamano)
    row = db.fetch_one(
        "UPDATE mesas SET estado = 'Abierta', id_sesion = %s, ronda_base = %s, tamano = %s, "
        "cupo_por_ronda = %s, fecha_apertura = %s WHERE id = %s RETURNING *",
        (id_sesion, ronda_base, nuevo_tamano, cupo_para(nuevo_tamano), now_iso(), id_mesa),
    )
    return _row_to_out(row)


def cerrar(id_grupo: str, id_mesa: str) -> dict:
    """Cierra la mesa y cancela lo que tenía pedido y todavía no sonó.

    Los pedidos ya cantados no se tocan: son el historial de la noche y de ahí
    sale el reporte del local.
    """
    row = db.fetch_one("SELECT * FROM mesas WHERE id = %s", (id_mesa,))
    if row is None or row["id_grupo"] != id_grupo:
        raise ValueError("Mesa no encontrada")

    cancelados = 0
    if row["id_sesion"]:
        filas = db.fetch_all(
            "UPDATE canciones_sesion SET estado = 'Cancelada' "
            "WHERE id_sesion = %s AND id_mesa = %s AND estado IN ('En cola', 'Pendiente') RETURNING id",
            (row["id_sesion"], id_mesa),
        )
        cancelados = len(filas)

    row = db.fetch_one(
        "UPDATE mesas SET estado = 'Cerrada', id_sesion = NULL, fecha_apertura = '' WHERE id = %s RETURNING *",
        (id_mesa,),
    )
    salida = _row_to_out(row)
    salida["pedidos_cancelados"] = cancelados
    return salida


def eliminar(id_grupo: str, id_mesa: str) -> None:
    row = db.fetch_one("SELECT * FROM mesas WHERE id = %s", (id_mesa,))
    if row is None or row["id_grupo"] != id_grupo:
        raise ValueError("Mesa no encontrada")
    if row["estado"] == "Abierta":
        raise ValueError("Cerrá la mesa antes de eliminarla")
    db.execute("DELETE FROM mesas WHERE id = %s", (id_mesa,))


def cerrar_todas(id_grupo: str) -> int:
    """Cierra todas las mesas del local — el botón de fin de noche."""
    abiertas = db.fetch_all("SELECT id FROM mesas WHERE id_grupo = %s AND estado = 'Abierta'", (id_grupo,))
    for m in abiertas:
        cerrar(id_grupo, m["id"])
    return len(abiertas)
