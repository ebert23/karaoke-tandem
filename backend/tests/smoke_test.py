"""Smoke test de la API contra la base real (Supabase).

Corre todos los flujos principales a través de TestClient, así pasa por el
stack completo de FastAPI (middlewares incluidos) — importante porque la
conexión a Postgres se comparte por request vía middleware, y eso solo se
ejercita yendo por HTTP, no llamando a los servicios directo.

Crea sus propios grupos de prueba y los borra al final, así que se puede
correr contra la base de producción sin ensuciarla.

Uso (desde backend/, con el venv activo y DATABASE_URL en backend/.env):
    python tests/smoke_test.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from fastapi.testclient import TestClient  # noqa: E402

from app import db  # noqa: E402
from app.main import app  # noqa: E402

client = TestClient(app)
_grupos_creados: list[str] = []
_checks = 0


def check(cond: bool, desc: str) -> None:
    global _checks
    _checks += 1
    if not cond:
        print(f"[FALLA] {desc}")
        limpiar()
        sys.exit(1)
    print(f"[OK ] {desc}")


def h(id_grupo: str) -> dict:
    return {"X-Grupo-Id": id_grupo}


def delete(url: str, **kw):
    """DELETE con body: httpx no lo acepta en delete()."""
    return client.request("DELETE", url, **kw)


def crear_grupo(nombre: str, creador: str) -> dict:
    r = client.post("/api/grupos", json={"nombre": nombre, "creado_por_nombre": creador})
    assert r.status_code == 200, r.text
    g = r.json()
    _grupos_creados.append(g["id"])
    return g


def limpiar() -> None:
    """Borra los grupos de prueba respetando el orden de las FK."""
    for gid in _grupos_creados:
        for sql in (
            "DELETE FROM votos_turno WHERE id_sesion IN (SELECT id_sesion FROM sesiones WHERE id_grupo = %s)",
            "DELETE FROM canciones_sesion WHERE id_sesion IN (SELECT id_sesion FROM sesiones WHERE id_grupo = %s)",
            "DELETE FROM votos WHERE id_grupo = %s",
            "DELETE FROM favoritos WHERE id_grupo = %s",
            "DELETE FROM sesiones WHERE id_grupo = %s",
            "DELETE FROM retos WHERE id_grupo = %s",
            "DELETE FROM canciones WHERE id_grupo = %s",
            "DELETE FROM usuarios WHERE id_grupo = %s",
            "DELETE FROM grupos WHERE id = %s",
        ):
            db.execute(sql, (gid,))


def nueva_cancion(gid: str, titulo: str, autor: str = "Ana") -> dict:
    r = client.post(
        "/api/canciones",
        headers=h(gid),
        json={"titulo": titulo, "artista": f"Artista {titulo}", "genero": "Pop", "agregado_por": autor},
    )
    assert r.status_code == 200, r.text
    return r.json()


def main() -> None:
    # ---------------- Grupos ----------------
    g1 = crear_grupo("Smoke Grupo 1", "Ana")
    check(bool(g1["id"]), "crear grupo")
    check(len(g1["codigo"]) == 6 and g1["codigo"].isdigit(), "codigo de 6 digitos")

    r = client.post("/api/grupos/unirse", json={"codigo": g1["codigo"]})
    check(r.status_code == 200 and r.json()["id"] == g1["id"], "unirse por codigo devuelve el mismo grupo")
    check(client.post("/api/grupos/unirse", json={"codigo": "000000"}).status_code == 404, "codigo inexistente da 404")

    retos = client.get("/api/retos", headers=h(g1["id"])).json()
    check(len(retos) >= 10, f"retos default sembrados al crear grupo ({len(retos)})")
    check(client.get("/api/canciones").status_code == 422, "sin X-Grupo-Id el request falla")

    # ---------------- Usuarios ----------------
    ana = client.post("/api/usuarios", headers=h(g1["id"]), json={"nombre": "Ana"}).json()
    check(bool(ana["id"]), "crear/recuperar usuario Ana")
    ana2 = client.post("/api/usuarios", headers=h(g1["id"]), json={"nombre": "ANA"}).json()
    check(ana2["id"] == ana["id"], "get_or_create es case-insensitive")
    luis = client.post("/api/usuarios", headers=h(g1["id"]), json={"nombre": "Luis"}).json()

    g2 = crear_grupo("Smoke Grupo 2", "Bea")
    ana_g2 = client.post("/api/usuarios", headers=h(g2["id"]), json={"nombre": "Ana"}).json()
    check(ana_g2["id"] != ana["id"], "mismo nombre en otro grupo es un usuario distinto")

    # ---------------- Canciones ----------------
    c1 = nueva_cancion(g1["id"], "Uno")
    c2 = nueva_cancion(g1["id"], "Dos")
    c3 = nueva_cancion(g1["id"], "Tres")
    check(c1["votos"] == 0, "cancion nueva arranca con 0 votos")
    check(len(client.get("/api/canciones", headers=h(g1["id"])).json()) == 3, "listado devuelve las 3 canciones")
    check(len(client.get("/api/canciones", headers=h(g2["id"])).json()) == 0, "canciones aisladas por grupo")

    r = client.post(f"/api/canciones/{c1['id']}/votar", headers=h(g1["id"]), json={"id_usuario": ana["id"]})
    check(r.json()["votos"] == 1, "votar incrementa a 1")
    r = client.post(f"/api/canciones/{c1['id']}/votar", headers=h(g1["id"]), json={"id_usuario": ana["id"]})
    check(r.json()["votos"] == 0, "votar de nuevo quita el voto (toggle)")

    r = client.post(f"/api/canciones/{c1['id']}/favorito", headers=h(g1["id"]), json={"id_usuario": ana["id"]})
    check(r.json()["es_favorita"] is True, "marcar favorita")
    favs = client.get("/api/canciones", headers=h(g1["id"]), params={"favoritas": "true", "id_usuario": ana["id"]}).json()
    check(len(favs) == 1 and favs[0]["id"] == c1["id"], "filtro favoritas=true")

    check(len(client.get("/api/canciones/sugerencias").json()) > 0, "sugerencias por genero no vacias")
    exp = client.get("/api/canciones/export.csv", headers=h(g1["id"]))
    check(exp.status_code == 200 and "Uno" in exp.text, "export csv 200 + contiene titulo")

    # Permisos de edicion
    r = client.put(f"/api/canciones/{c1['id']}", headers=h(g1["id"]),
                   json={"titulo": "Uno editada", "artista": "X", "genero": "Rock", "id_usuario": ana["id"]})
    check(r.status_code == 200 and r.json()["titulo"] == "Uno editada", "el autor puede editar su propia cancion")
    c_luis = nueva_cancion(g1["id"], "DeLuis", autor="Luis")
    r = client.put(f"/api/canciones/{c_luis['id']}", headers=h(g1["id"]),
                   json={"titulo": "hack", "artista": "X", "genero": "Pop", "id_usuario": luis["id"]})
    check(r.status_code == 200, "Luis puede editar la suya")

    # ---------------- Sesiones: flujo completo ----------------
    ses = client.post("/api/sesiones", headers=h(g1["id"]), json={"participantes": ["Ana", "Luis"]}).json()
    check(ses["estado"] == "Activa" and ses["turno_actual"] == 0, "crear sesion activa en turno 0")
    sid = ses["id_sesion"]
    check(client.get("/api/sesiones/activa", headers=h(g1["id"])).json()["id_sesion"] == sid, "sesion activa se detecta")

    # Cola
    r = client.post(f"/api/sesiones/{sid}/cola", headers=h(g1["id"]), json={"id_cancion": c2["id"], "cantantes": []})
    check(r.status_code == 200 and r.json()["estado"] == "En cola", "agregar a la cola")

    # Solo admin puede pedir siguiente
    r = client.post(f"/api/sesiones/{sid}/siguiente", headers=h(g1["id"]), json={"id_usuario_actor": luis["id"]})
    check(r.status_code == 403, "un no-admin no puede pedir la siguiente cancion (403)")

    r = client.post(f"/api/sesiones/{sid}/siguiente", headers=h(g1["id"]), json={"id_usuario_actor": ana["id"]})
    check(r.status_code == 200 and r.json()["id_cancion"] == c2["id"], "siguiente promueve la cola antes que el azar")
    turno1 = r.json()
    check(turno1["cancion"] is not None and turno1["cancion"]["id"] == c2["id"], "el turno trae su cancion embebida")

    # Anti-duplicados
    r2 = client.post(f"/api/sesiones/{sid}/siguiente", headers=h(g1["id"]), json={"id_usuario_actor": ana["id"]})
    check(r2.json()["id_cancion"] == turno1["id_cancion"], "pedir siguiente con un pendiente ya armado devuelve el mismo turno")

    # Votacion en vivo
    client.post(f"/api/sesiones/{sid}/canciones/{c2['id']}/votar_turno", headers=h(g1["id"]),
                json={"id_usuario": ana["id"], "puntuacion": 10})
    r = client.post(f"/api/sesiones/{sid}/canciones/{c2['id']}/votar_turno", headers=h(g1["id"]),
                    json={"id_usuario": luis["id"], "puntuacion": 8})
    check(r.json()["promedio"] == 9, "promedio de votos en vivo = 9")
    check(len(client.get(f"/api/sesiones/{sid}/canciones/{c2['id']}/votos_turno", headers=h(g1["id"])).json()["votos"]) == 2,
          "GET votos_turno devuelve 2 votos")

    r = client.post(f"/api/sesiones/{sid}/canciones/{c2['id']}/cantada", headers=h(g1["id"]), json={"puntuacion": None})
    check(r.json()["puntuacion"] == 9, "marcar cantada usa el promedio de la votacion en vivo")
    check(r.json()["cantada_por"].lower() == "ana", "primer turno le toca al primer participante")

    # Siguiente al azar (sin cola)
    r = client.post(f"/api/sesiones/{sid}/siguiente", headers=h(g1["id"]), json={"id_usuario_actor": ana["id"]})
    check(r.status_code == 200, "siguiente sin cola cae a aleatorio")
    az = r.json()
    check(az["cancion"] is not None, "el turno aleatorio tambien trae su cancion")
    r = client.post(f"/api/sesiones/{sid}/canciones/{az['id_cancion']}/cantada", headers=h(g1["id"]), json={"puntuacion": None})
    check(r.status_code == 400, "marcar cantada sin votos y sin puntuacion falla")
    r = client.post(f"/api/sesiones/{sid}/canciones/{az['id_cancion']}/cantada", headers=h(g1["id"]), json={"puntuacion": 7})
    check(r.json()["puntuacion"] == 7, "marcar cantada con puntuacion manual funciona")

    # detalle: valida el batch de canciones (cada turno con SU cancion correcta)
    det = client.get(f"/api/sesiones/{sid}/detalle", headers=h(g1["id"])).json()
    check(len(det) >= 2, f"detalle devuelve los turnos ({len(det)})")
    check(all(t["cancion"] is not None for t in det), "todos los turnos del detalle traen cancion (batch)")
    check(all(t["cancion"]["id"] == t["id_cancion"] for t in det),
          "el batch mapea cada turno con SU cancion (no se cruzan)")

    # Ranking de la noche
    ranking = client.get(f"/api/ranking/noche/{sid}", headers=h(g1["id"])).json()
    por_nombre = {x["nombre"].lower(): x["puntos"] for x in ranking}
    check(por_nombre.get("ana") == 9, "ranking noche: Ana con 9 puntos")

    # ---------------- Duetos ----------------
    # Canción creada recién acá a propósito: el "siguiente aleatorio" de más
    # arriba elige al azar entre las disponibles y podría haberse llevado
    # cualquiera de las anteriores, dejando el test inestable.
    cd = nueva_cancion(g1["id"], "Dueto")
    client.post(f"/api/sesiones/{sid}/cola", headers=h(g1["id"]),
                json={"id_cancion": cd["id"], "cantantes": ["Ana", "Luis"]})
    r = client.post(f"/api/sesiones/{sid}/siguiente", headers=h(g1["id"]), json={"id_usuario_actor": ana["id"]})
    check(r.json()["id_cancion"] == cd["id"], "siguiente promueve el dueto")
    check("," in r.json()["cantada_por"], "el dueto conserva ambos cantantes")
    client.post(f"/api/sesiones/{sid}/canciones/{cd['id']}/cantada", headers=h(g1["id"]), json={"puntuacion": 8})
    ranking = client.get(f"/api/ranking/noche/{sid}", headers=h(g1["id"])).json()
    por_nombre = {x["nombre"].lower(): x["puntos"] for x in ranking}
    # Los puntos del dueto NO se reparten: cada cantante suma el total.
    # Ana venia de 9 (primer turno) y Luis de 7 (el turno aleatorio, que por
    # rotacion le tocaba a el), asi que ambos suman 8 enteros.
    check(por_nombre.get("ana") == 17, "dueto: Ana suma los 8 puntos completos (9+8)")
    check(por_nombre.get("luis") == 15, "dueto: Luis tambien suma los 8 puntos completos (7+8)")

    # ---------------- Cola: reordenar / quitar (solo admin) ----------------
    ca = nueva_cancion(g1["id"], "ColaUno")
    cb = nueva_cancion(g1["id"], "ColaDos")
    for c in (ca, cb):
        client.post(f"/api/sesiones/{sid}/cola", headers=h(g1["id"]), json={"id_cancion": c["id"], "cantantes": []})

    r = client.post(f"/api/sesiones/{sid}/cola/{cb['id']}/mover", headers=h(g1["id"]),
                    json={"id_usuario_actor": luis["id"], "direccion": "arriba"})
    check(r.status_code == 403, "un no-admin no puede reordenar la cola (403)")
    r = client.post(f"/api/sesiones/{sid}/cola/{cb['id']}/mover", headers=h(g1["id"]),
                    json={"id_usuario_actor": ana["id"], "direccion": "arriba"})
    check(r.status_code == 200 and r.json()[0]["id_cancion"] == cb["id"], "admin sube ColaDos al principio")
    check(all(t["cancion"] is not None for t in r.json()), "la cola devuelta trae las canciones (batch)")

    r = delete(f"/api/sesiones/{sid}/cola/{ca['id']}", headers=h(g1["id"]), json={"id_usuario_actor": luis["id"]})
    check(r.status_code == 403, "un no-admin no puede sacar de la cola (403)")
    r = delete(f"/api/sesiones/{sid}/cola/{ca['id']}", headers=h(g1["id"]), json={"id_usuario_actor": ana["id"]})
    check(r.status_code in (200, 204), "admin saca ColaUno de la cola")
    en_cola = [t["id_cancion"] for t in client.get(f"/api/sesiones/{sid}/detalle", headers=h(g1["id"])).json()
               if t["estado"] == "En cola"]
    check(ca["id"] not in en_cola and cb["id"] in en_cola, "la cola queda solo con ColaDos")

    # ---------------- Retos ----------------
    r = client.get("/api/retos/aleatorio", headers=h(g1["id"]), params={"categoria": "Creativo"})
    check(r.status_code == 200 and r.json()["categoria"] == "Creativo", "reto aleatorio respeta categoria")
    r = client.post("/api/retos", headers=h(g1["id"]),
                    json={"texto": "Reto de prueba", "categoria": "Creativo", "dificultad": "Fácil"})
    check(r.status_code == 200, "crear reto personalizado")
    check(len(client.get("/api/retos", headers=h(g2["id"])).json()) == len(retos),
          "retos aislados por grupo: el grupo 2 sigue con los suyos")

    # ---------------- Cierre + estadisticas ----------------
    r = client.post(f"/api/sesiones/{sid}/finalizar", headers=h(g1["id"]))
    check(r.status_code == 200, "finalizar sesion")
    check(client.get("/api/sesiones/activa", headers=h(g1["id"])).json() is None, "ya no hay sesion activa")

    st = client.get(f"/api/estadisticas/{ana['id']}", headers=h(g1["id"])).json()
    check(st["canciones_cantadas"] >= 2, "estadisticas de Ana reflejan las canciones cantadas")
    hist = client.get("/api/ranking/historico", headers=h(g1["id"])).json()
    check(any(x["nombre"].lower() == "ana" for x in hist), "ranking historico incluye a Ana")

    # ---------------- Admin: roles ----------------
    check(ana["id"] in client.get(f"/api/grupos/{g1['id']}").json()["admins"], "Ana (creadora) ya es admin")
    r = client.post(f"/api/grupos/{g1['id']}/miembros/{luis['id']}/admin", json={"id_usuario_actor": luis["id"]})
    check(r.status_code == 403, "un no-admin no puede otorgar el rol de admin (403)")
    r = client.post(f"/api/grupos/{g1['id']}/miembros/{luis['id']}/admin", json={"id_usuario_actor": ana["id"]})
    check(r.status_code == 200 and luis["id"] in r.json()["admins"], "Ana promueve a Luis a admin")
    r = delete(f"/api/grupos/{g1['id']}/miembros/{ana['id']}/admin", json={"id_usuario_actor": ana["id"]})
    check(r.status_code == 200, "Ana se auto-degrada (queda Luis como admin)")
    r = delete(f"/api/grupos/{g1['id']}/miembros/{luis['id']}/admin", json={"id_usuario_actor": luis["id"]})
    check(r.status_code == 400, "no se puede quitar al ultimo admin del grupo (400)")

    # ---------------- Varios requests seguidos (conexion compartida) ----------------
    for _ in range(3):
        check(client.get(f"/api/sesiones/{sid}/detalle", headers=h(g1["id"])).status_code == 200,
              "detalle sigue respondiendo en requests sucesivos")

    check(client.get("/api/youtube/buscar", params={"q": "test"}).status_code in (200, 501),
          "youtube buscar responde (200 con API key, 501 sin ella)")

    print(f"\nTODOS LOS CHECKS PASARON ({_checks})")


if __name__ == "__main__":
    try:
        main()
    finally:
        limpiar()
        print("datos de prueba borrados")
