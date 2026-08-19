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
            "DELETE FROM sugerencias_mesa WHERE id_grupo = %s",
            "DELETE FROM mesas WHERE id_grupo = %s",
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

    # ---------------- Sin canciones repetidas en la lista del grupo ----------------
    base = client.post("/api/canciones", headers=h(g1["id"]), json={
        "titulo": "Mientes Tan Bien", "artista": "Sin Bandera", "genero": "Balada",
        "link_youtube": "https://youtu.be/aBcDeFgHiJ1", "agregado_por": "Ana"}).json()

    def alta(titulo, artista, link="", autor="Luis"):
        return client.post("/api/canciones", headers=h(g1["id"]), json={
            "titulo": titulo, "artista": artista, "genero": "Balada",
            "link_youtube": link, "agregado_por": autor})

    r = alta("Mientes Tan Bien", "Sin Bandera")
    check(r.status_code == 400, "no se puede agregar la misma cancion dos veces")
    check("ya está en la lista" in r.json()["detail"] and "Ana" in r.json()["detail"],
          f"el aviso dice cual es y quien la agrego: {r.json()['detail']}")

    r = alta("MIENTES TAN BIEN (Video Oficial) HD", "sin bandera")
    check(r.status_code == 400, "tampoco con mayusculas, tildes ni adornos de YouTube en el titulo")

    r = alta("Mienten Bien", "Sin Bandera")
    check(r.status_code == 200, "una cancion parecida pero distinta si entra")
    client.request("DELETE", f"/api/canciones/{r.json()['id']}", headers=h(g1["id"]),
                   json={"id_usuario": luis["id"]})

    r = alta("Otro titulo completamente distinto", "Otro Artista",
             "https://www.youtube.com/watch?v=aBcDeFgHiJ1")
    check(r.status_code == 400, "mismo video de YouTube = misma cancion, aunque la titulen distinto")

    # El formulario pregunta antes de que la persona termine de escribir.
    r = client.get("/api/canciones/duplicada", headers=h(g1["id"]),
                   params={"titulo": "mientes tan bien", "artista": "Sin Bandera"})
    check(r.status_code == 200 and r.json() and r.json()["id"] == base["id"],
          "el aviso previo encuentra la repetida antes de guardar")
    r = client.get("/api/canciones/duplicada", headers=h(g1["id"]),
                   params={"titulo": "Algo que nadie cargo", "artista": "Nadie"})
    check(r.status_code == 200 and r.json() is None, "y no avisa de nada cuando la cancion es nueva")

    # Editar es la otra forma de terminar con dos filas iguales...
    r = client.put(f"/api/canciones/{c_luis['id']}", headers=h(g1["id"]), json={
        "titulo": "Mientes Tan Bien", "artista": "Sin Bandera", "genero": "Balada",
        "id_usuario": luis["id"]})
    check(r.status_code == 400, "editar una cancion para dejarla igual que otra tambien se rechaza")
    # ...pero la canción no puede chocar consigo misma.
    r = client.put(f"/api/canciones/{base['id']}", headers=h(g1["id"]), json={
        "titulo": "Mientes Tan Bien", "artista": "Sin Bandera", "genero": "Pop",
        "link_youtube": base["link_youtube"], "id_usuario": ana["id"]})
    check(r.status_code == 200 and r.json()["genero"] == "Pop",
          "se le puede corregir el genero a una cancion sin que se acuse a si misma")
    client.request("DELETE", f"/api/canciones/{base['id']}", headers=h(g1["id"]),
                   json={"id_usuario": ana["id"]})

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

    r = client.post(f"/api/sesiones/{sid}/siguiente", headers=h(g1["id"]),
                    json={"id_usuario_actor": ana["id"], "modo": "cola"})
    check(r.status_code == 200 and r.json()["id_cancion"] == c2["id"], "modo cola promueve la primera de la cola")
    turno1 = r.json()
    check(turno1["cancion"] is not None and turno1["cancion"]["id"] == c2["id"], "el turno trae su cancion embebida")

    # Anti-duplicados
    r2 = client.post(f"/api/sesiones/{sid}/siguiente", headers=h(g1["id"]),
                     json={"id_usuario_actor": ana["id"], "modo": "cola"})
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

    # Modo aleatorio IGNORA la cola: encolamos una y pedimos aleatorio, y lo
    # que sale tiene que ser otra cosa (la encolada queda esperando su turno).
    encolada = nueva_cancion(g1["id"], "Encolada")
    client.post(f"/api/sesiones/{sid}/cola", headers=h(g1["id"]),
                json={"id_cancion": encolada["id"], "cantantes": []})
    r = client.post(f"/api/sesiones/{sid}/siguiente", headers=h(g1["id"]),
                    json={"id_usuario_actor": ana["id"], "modo": "aleatorio"})
    check(r.status_code == 200, "modo aleatorio responde 200 aunque haya cola")
    az = r.json()
    check(az["id_cancion"] != encolada["id"], "modo aleatorio NO promueve la cancion encolada")
    check(az["cancion"] is not None, "el turno aleatorio tambien trae su cancion")
    sigue_en_cola = [t["id_cancion"] for t in client.get(f"/api/sesiones/{sid}/detalle", headers=h(g1["id"])).json()
                     if t["estado"] == "En cola"]
    check(encolada["id"] in sigue_en_cola, "la cancion encolada sigue en la cola tras el sorteo")
    r = client.post(f"/api/sesiones/{sid}/canciones/{az['id_cancion']}/cantada", headers=h(g1["id"]), json={"puntuacion": None})
    check(r.status_code == 400, "marcar cantada sin votos y sin puntuacion falla")
    r = client.post(f"/api/sesiones/{sid}/canciones/{az['id_cancion']}/cantada", headers=h(g1["id"]), json={"puntuacion": 7})
    check(r.json()["puntuacion"] == 7, "marcar cantada con puntuacion manual funciona")

    # Vaciamos la cola (asi los bloques que siguen arrancan limpios) y de paso
    # comprobamos que modo cola con la cola vacia avisa en vez de sortear.
    delete(f"/api/sesiones/{sid}/cola/{encolada['id']}", headers=h(g1["id"]),
           json={"id_usuario_actor": ana["id"]})
    r = client.post(f"/api/sesiones/{sid}/siguiente", headers=h(g1["id"]),
                    json={"id_usuario_actor": ana["id"], "modo": "cola"})
    check(r.status_code == 400, "modo cola con la cola vacia falla (400), no sortea al azar")

    # Cliente viejo (PWA con el bundle anterior en cache) que NO manda "modo":
    # tiene que seguir funcionando como antes -- cola si hay, sorteo si no.
    # Sin esto, un celular con cache vieja recibia 400 y no podia seguir.
    r = client.post(f"/api/sesiones/{sid}/siguiente", headers=h(g1["id"]),
                    json={"id_usuario_actor": ana["id"]})
    check(r.status_code == 200, "sin 'modo' (cliente viejo) sortea igual con la cola vacia")
    legacy = r.json()
    # Lo saltamos en vez de marcarlo cantado: hay que dejar la sesion sin
    # turno pendiente para lo que sigue, pero sin sumar puntos que
    # descuadren las verificaciones de ranking de mas abajo.
    client.post(f"/api/sesiones/{sid}/canciones/{legacy['id_cancion']}/saltar", headers=h(g1["id"]))

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
    r = client.post(f"/api/sesiones/{sid}/siguiente", headers=h(g1["id"]),
                    json={"id_usuario_actor": ana["id"], "modo": "cola"})
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
    nuevo_reto = r.json()
    check(len(client.get("/api/retos", headers=h(g2["id"])).json()) == len(retos),
          "retos aislados por grupo: el grupo 2 sigue con los suyos")

    r = client.post("/api/retos", headers=h(g1["id"]),
                    json={"texto": "  reto DE prueba ", "categoria": "Normal", "dificultad": "Medio"})
    check(r.status_code == 400, "el mismo reto no entra dos veces a la baraja")

    # Cada categoria tiene que dar para una noche: con 2 retos, "Otro reto"
    # devolvia siempre el mismo.
    for categoria in ("Normal", "Picante", "Creativo", "Grupo"):
        n = len(client.get("/api/retos", headers=h(g2["id"]), params={"categoria": categoria}).json())
        check(n >= 6, f"la categoria {categoria} trae {n} retos por defecto")

    # "Otro reto": el excluido no puede volver a salir mientras haya otros.
    actual = client.get("/api/retos/aleatorio", headers=h(g2["id"]), params={"categoria": "Grupo"}).json()
    repetidos = 0
    for _ in range(8):
        otro = client.get("/api/retos/aleatorio", headers=h(g2["id"]),
                          params={"categoria": "Grupo", "excluir": actual["id"]}).json()
        if otro["id"] == actual["id"]:
            repetidos += 1
    check(repetidos == 0, f"'Otro reto' nunca devuelve el que ya estaba en pantalla ({repetidos}/8)")

    # Borrar: solo admins, y solo lo que existe.
    r = delete(f"/api/retos/{nuevo_reto['id']}", headers=h(g1["id"]),
               json={"id_usuario_actor": luis["id"]})
    check(r.status_code == 403, "un no-admin no puede sacar retos de la baraja (403)")
    r = delete(f"/api/retos/{nuevo_reto['id']}", headers=h(g1["id"]),
               json={"id_usuario_actor": ana["id"]})
    check(r.status_code == 204, "un admin saca el reto de la baraja")
    ids = [x["id"] for x in client.get("/api/retos", headers=h(g1["id"])).json()]
    check(nuevo_reto["id"] not in ids, "el reto borrado ya no esta en la baraja")
    r = delete(f"/api/retos/{nuevo_reto['id']}", headers=h(g1["id"]),
               json={"id_usuario_actor": ana["id"]})
    check(r.status_code == 404, "borrar un reto que ya no existe da 404")
    check(delete(f"/api/retos/{ids[0]}", headers=h(g2["id"]),
                 json={"id_usuario_actor": ana["id"]}).status_code == 404,
          "no se puede borrar un reto de otro grupo")

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

    aleatorio_por_jugador()
    badges_del_ranking()
    salon()

    print(f"\nTODOS LOS CHECKS PASARON ({_checks})")


def badges_del_ranking() -> None:
    """Los logros del ranking, que se calculan al vuelo sobre el historial.

    Importa porque el ranking arma ese historial una sola vez y lo comparte
    entre todas las personas: si esa carga compartida quedara mal, los badges
    saldrían de otro o directamente no saldrían.
    """
    gid = crear_grupo("Smoke Badges", "Ana")["id"]
    ana = client.post("/api/usuarios", headers=h(gid), json={"nombre": "Ana"}).json()

    for i, genero in enumerate(("Pop", "Rock", "Balada")):
        client.post("/api/canciones", headers=h(gid), json={
            "titulo": f"Tema {i}", "artista": f"Artista {i}", "genero": genero, "agregado_por": "Ana"})

    sid = client.post("/api/sesiones", headers=h(gid), json={"participantes": ["Ana"]}).json()["id_sesion"]

    def cantar(puntuacion: int) -> None:
        t = client.post(f"/api/sesiones/{sid}/siguiente", headers=h(gid),
                        json={"id_usuario_actor": ana["id"], "modo": "aleatorio"}).json()
        client.post(f"/api/sesiones/{sid}/canciones/{t['id_cancion']}/cantada",
                    headers=h(gid), json={"puntuacion": puntuacion})

    def codigos_de_ana() -> set[str]:
        hist = client.get("/api/ranking/historico", headers=h(gid)).json()
        fila = next(x for x in hist if x["nombre"].lower() == "ana")
        return {b["codigo"] for b in fila["badges"]}

    check(codigos_de_ana() == set(), "sin cantar todavia no hay ningun badge")

    for _ in range(3):
        cantar(10)
    codigos = codigos_de_ana()
    check("debut" in codigos, "badge Debut con la primera cantada")
    check("voz_de_oro" in codigos, "badge Voz de Oro con promedio 9+")
    check("explorador" in codigos, f"badge Explorador con 3 generos distintos: {sorted(codigos)}")
    check("maratonista" not in codigos, "todavia no es Maratonista con 3 canciones")

    # Las dos que faltan ya son repeticiones (solo cargo 3): el conteo tiene
    # que sumarlas igual, porque cantar dos veces la misma es cantar dos veces.
    cantar(10)
    cantar(10)
    check("maratonista" in codigos_de_ana(), "badge Maratonista a las 5 cantadas, contando repeticiones")

    noche = client.get(f"/api/ranking/noche/{sid}", headers=h(gid)).json()
    fila = next(x for x in noche if x["nombre"].lower() == "ana")
    check(fila["canciones_cantadas"] == 5 and fila["puntos"] == 50,
          f"ranking de la noche: 5 canciones y 50 puntos ({fila['canciones_cantadas']}/{fila['puntos']})")
    check({b["codigo"] for b in fila["badges"]} == codigos_de_ana(),
          "el ranking de la noche muestra los mismos badges que el historico")


def aleatorio_por_jugador() -> None:
    """El sorteo le da a cada quien SUS canciones, y de verdad sortea.

    Dos cosas distintas que la gente notó jugando: que salían canciones que
    había cargado otro, y que parecían salir en el orden en que se cargaron.
    Por eso el test verifica las dos: de quién es cada canción, y que el orden
    no sea el de alta.
    """
    gid = crear_grupo("Smoke Aleatorio", "Ana")["id"]
    ana = client.post("/api/usuarios", headers=h(gid), json={"nombre": "Ana"}).json()
    client.post("/api/usuarios", headers=h(gid), json={"nombre": "Luis"}).json()

    # Listas de distinto tamaño a propósito: asi mas adelante a Ana se le
    # acaban las suyas mientras a Luis todavia le sobran.
    de_ana = [nueva_cancion(gid, f"Ana{i}", autor="Ana")["id"] for i in range(6)]
    # "LUÍS" con tilde y en mayusculas a proposito: el nombre se tipea a mano
    # en dos lugares distintos y casi nunca coincide caracter por caracter.
    de_luis = [nueva_cancion(gid, f"Luis{i}", autor="LUÍS")["id"] for i in range(12)]

    sid = client.post("/api/sesiones", headers=h(gid),
                      json={"participantes": ["Ana", "Luis"]}).json()["id_sesion"]

    def un_turno() -> dict:
        t = client.post(f"/api/sesiones/{sid}/siguiente", headers=h(gid),
                        json={"id_usuario_actor": ana["id"], "modo": "aleatorio"}).json()
        client.post(f"/api/sesiones/{sid}/canciones/{t['id_cancion']}/cantada",
                    headers=h(gid), json={"puntuacion": 7})
        return t

    salidas = [un_turno() for _ in range(10)]  # 5 turnos de cada uno
    de_cada = {"Ana": de_ana, "Luis": de_luis}
    check(all(t["id_cancion"] in de_cada[t["cantada_por"]] for t in salidas),
          "a cada uno le tocan solo las canciones que cargo el, no las del otro")
    check(len([t for t in salidas if t["cantada_por"] == "Luis"]) == 5,
          "la rotacion entre los dos participantes se mantiene")

    # Que las 5 de cada uno salgan justo en el orden de alta tiene 1 en 120 de
    # probabilidad; que pase en los dos a la vez, 1 en 14400.
    orden_ana = [de_ana.index(t["id_cancion"]) for t in salidas if t["cantada_por"] == "Ana"]
    orden_luis = [de_luis.index(t["id_cancion"]) for t in salidas if t["cantada_por"] == "Luis"]
    check(orden_ana != sorted(orden_ana) or orden_luis != sorted(orden_luis),
          f"el sorteo no devuelve las canciones en el orden en que se cargaron: {orden_ana} / {orden_luis}")

    # Cuando a alguien se le acaban las propias tiene que seguir cantando: la
    # noche no se corta porque uno cargo menos canciones que el otro. A Ana le
    # queda 1 sola, asi que en 4 turnos mas se queda sin nada propio.
    restantes = [un_turno() for _ in range(4)]
    prestadas = [t for t in restantes if t["cantada_por"] == "Ana" and t["id_cancion"] in de_luis]
    check(len(prestadas) == 1 and prestadas[0]["cancion"] is not None,
          "si al que le toca no le quedan canciones propias, igual se le sortea una del resto")

    # ---- Se acabo el repertorio: el juego sigue, repitiendo ----
    # Van 14 turnos sobre 18 canciones. Con 4 turnos mas no queda nada sin
    # cantar, y a partir de ahi TODO lo que salga es una repeticion.
    for _ in range(4):
        un_turno()
    repeticiones = [un_turno() for _ in range(6)]
    check(all(t["cancion"] is not None for t in repeticiones),
          "sin canciones nuevas el sorteo sigue devolviendo turnos en vez de cortar la noche")
    check(all(t["id_cancion"] in de_cada[t["cantada_por"]] for t in repeticiones),
          "al repetir tambien le toca a cada uno lo suyo")
    check(len({t["id"] for t in repeticiones}) == 6,
          "cada repeticion es un turno propio, no una reescritura del anterior")

    # Con 6 canciones cada uno y 3 repeticiones por cabeza, si el sorteo
    # eligiera a ciegas es facil que insista con la misma: repartir entre las
    # menos cantadas tiene que dar 3 canciones distintas.
    rep_ana = [t["id_cancion"] for t in repeticiones if t["cantada_por"] == "Ana"]
    check(len(set(rep_ana)) == len(rep_ana),
          f"las repeticiones rotan en vez de insistir con la misma cancion: {len(set(rep_ana))}/{len(rep_ana)}")

    # La lista completa tiene que conservar las dos vueltas de cada canción.
    detalle = client.get(f"/api/sesiones/{sid}/detalle", headers=h(gid)).json()
    check(len(detalle) == 24, f"la playlist guarda cada interpretacion por separado ({len(detalle)} turnos)")
    check(len({t["id"] for t in detalle}) == 24, "cada fila de la playlist tiene su propio id")

    # Encolar a mano una ya cantada tambien tiene que poder; lo unico que se
    # rechaza es tenerla dos veces esperando al mismo tiempo.
    ya_cantada = de_ana[0]
    r = client.post(f"/api/sesiones/{sid}/cola", headers=h(gid), json={"id_cancion": ya_cantada, "cantantes": []})
    check(r.status_code == 200, "se puede volver a encolar una cancion que ya se canto")
    r = client.post(f"/api/sesiones/{sid}/cola", headers=h(gid), json={"id_cancion": ya_cantada, "cantantes": []})
    check(r.status_code == 400, "pero no dos veces en la misma cola")


def salon() -> None:
    """Modo salón: mesas con QR, rotación entre mesas y vista del DJ.

    Lo que más importa acá es el ORDEN exacto de la rotación: es la promesa
    del producto ("todas las mesas cantan, las grandes un poco más") y lo
    único que un local va a mirar con lupa la primera noche.
    """
    print("\n--- modo salon ---")
    local = crear_grupo("Karaoke Test Salon", "Duena")
    gid = local["id"]
    duena_id = local["admins"][0]

    # El código de DJ solo viaja en esta respuesta (y al regenerarlo).
    check(client.post(f"/api/grupos/{gid}/convertir-a-salon",
                      json={"id_usuario_actor": "U-cualquiera"}).status_code == 403,
          "solo un admin puede convertir el grupo en local (403)")
    r = client.post(f"/api/grupos/{gid}/convertir-a-salon", json={"id_usuario_actor": duena_id})
    check(r.status_code == 200 and r.json()["modo"] == "salon", "grupo convertido a modo salon")
    codigo_dj = r.json()["codigo_dj"]
    check(len(codigo_dj) >= 20, f"codigo de DJ largo y no adivinable ({len(codigo_dj)} chars)")
    hdj = {"X-Grupo-Id": gid, "X-DJ-Codigo": codigo_dj}

    # ---------------- Puerta del DJ ----------------
    check(client.get("/api/dj/cola", headers=h(gid)).status_code == 403,
          "sin codigo de DJ la vista del DJ responde 403")
    check(client.get("/api/dj/cola", headers={**h(gid), "X-DJ-Codigo": "otracosa"}).status_code == 403,
          "con codigo de DJ equivocado responde 403")

    # ---------------- Catálogo + noche + mesas ----------------
    canciones = {t: nueva_cancion(gid, t, "Duena")["id"] for t in ["A", "B", "C", "D", "E", "F", "G", "H", "I"]}
    sid = client.post("/api/sesiones", json={"participantes": ["Salon"]}, headers=h(gid)).json()["id_sesion"]

    def crear_mesa(numero, tamano):
        r = client.post("/api/mesas", json={"numero": numero, "tamano": tamano}, headers=h(gid))
        assert r.status_code == 200, r.text
        return r.json()

    m1 = crear_mesa("1", 3)   # mesa grande -> cupo 2
    m2 = crear_mesa("2", 1)   # mesa de una persona -> cupo 1
    m3 = crear_mesa("3", 4)   # mesa grande -> cupo 2
    check(m1["cupo_por_ronda"] == 2 and m2["cupo_por_ronda"] == 1,
          "cupo por ronda derivado del tamano (1 persona -> 1, 2+ -> 2)")
    check(len(m1["codigo"]) == 8 and m1["codigo"] != m2["codigo"], "cada mesa tiene su propio codigo de QR")
    check(client.post("/api/mesas", json={"numero": "1", "tamano": 2}, headers=h(gid)).status_code == 400,
          "no se puede repetir el numero de mesa en el mismo local")

    # Pedir con la mesa cerrada no debe funcionar: el QR existe desde que se
    # imprime, pero recién sirve cuando el local sienta gente ahí.
    check(client.post(f"/api/mesa/{m1['codigo']}/pedidos",
                      json={"id_cancion": canciones["A"], "pedido_por": "Juan"}).status_code == 400,
          "con la mesa cerrada no se puede pedir")

    for m, tam in ((m1, 3), (m2, 1), (m3, 4)):
        r = client.post(f"/api/mesas/{m['id']}/abrir", json={"tamano": tam}, headers=h(gid))
        assert r.status_code == 200, r.text

    # ---------------- La rotación ----------------
    def pedir(mesa, titulo, quien):
        r = client.post(f"/api/mesa/{mesa['codigo']}/pedidos",
                        json={"id_cancion": canciones[titulo], "pedido_por": quien})
        assert r.status_code == 200, r.text
        return r.json()

    pedir(m1, "A", "Juan")
    pedir(m1, "B", "Juan")
    pedir(m1, "C", "Juan")   # llenó su cupo de la ronda 0 -> esta va a la 1
    pedir(m2, "D", "Sole")
    pedir(m2, "E", "Sole")   # cupo 1 -> esta va a la ronda 1
    pedir(m3, "F", "Pepe")
    pedir(m3, "G", "Pepe")

    def titulos_en_cola():
        r = client.get("/api/dj/cola", headers=hdj)
        assert r.status_code == 200, r.text
        return r.json(), [p["cancion"]["titulo"] for p in r.json()["cola"]]

    cola, titulos = titulos_en_cola()
    # Mesa 1 mete sus dos, después mesa 2 la suya, después mesa 3 sus dos —
    # y recién entonces arranca la segunda vuelta. Nadie espera una vuelta
    # entera para cantar por primera vez.
    check(titulos == ["A", "B", "D", "F", "G", "C", "E"],
          f"rotacion intercalada con cupo por mesa: {titulos}")
    check(cola["mesas_abiertas"] == 3, "el DJ ve 3 mesas abiertas")

    # ---------------- Mesa que llega tarde ----------------
    r = client.post("/api/dj/siguiente", headers=hdj)
    check(r.status_code == 200 and r.json()["cancion"]["titulo"] == "A", "el DJ promueve la primera de la rotacion")
    check(r.json()["mesa_numero"] == "1" and r.json()["pedido_por"] == "Juan",
          "el pedido trae mesa y nombre (lo que el DJ anuncia al microfono)")
    primera = r.json()
    check(client.post("/api/dj/pedidos/{}/cantada".format(primera["id"]), headers=hdj).status_code == 200,
          "el DJ marca la cancion como cantada")

    m4 = crear_mesa("4", 2)
    client.post(f"/api/mesas/{m4['id']}/abrir", json={"tamano": 2}, headers=h(gid))
    pedir(m4, "H", "Tarde")
    _, titulos = titulos_en_cola()
    check(titulos == ["B", "D", "F", "G", "H", "C", "E"],
          f"la mesa que llega tarde entra en la vuelta en curso, no al principio ni al final: {titulos}")

    # ---------------- No vino ----------------
    r = client.post("/api/dj/siguiente", headers=hdj)
    pedido_b = r.json()
    check(pedido_b["cancion"]["titulo"] == "B", "sigue B")
    r = client.post(f"/api/dj/pedidos/{pedido_b['id']}/no-vino", headers=hdj)
    check(r.status_code == 200, "el DJ marca 'no vino'")
    _, titulos = titulos_en_cola()
    check(titulos[0] == "D" and "B" in titulos,
          f"'no vino' atrasa el pedido pero no lo borra: {titulos}")
    # Pierde su lugar en la vuelta en curso (queda detrás de todo lo que
    # todavía esperaba en ella) pero vuelve al principio de la siguiente: si
    # lo mandáramos al fondo de la cola, el que fue al baño no canta más.
    check(titulos.index("B") > titulos.index("H"),
          f"el que no vino queda detras de toda la vuelta en curso: {titulos}")

    # ---------------- Repetida ----------------
    # "A" ya se cantó. Otra mesa la puede volver a pedir (en un salón con
    # doscientas personas, bloquearla toda la noche sería absurdo), pero el
    # DJ la ve marcada.
    r = client.post(f"/api/mesa/{m3['codigo']}/pedidos",
                    json={"id_cancion": canciones["A"], "pedido_por": "Pepe"})
    check(r.status_code == 200, "otra mesa puede pedir una cancion que ya se canto esta noche")
    cola, _ = titulos_en_cola()
    repetida = next((p for p in cola["cola"] if p["cancion"]["titulo"] == "A"), None)
    check(repetida is not None and repetida["repetida"] is True,
          "el DJ ve el aviso de repetida")
    check(repetida["cantada_hace_min"] is not None, "y hace cuanto se canto")

    # La misma mesa sí tiene bloqueado el duplicado, que es un error de dedo.
    check(client.post(f"/api/mesa/{m3['codigo']}/pedidos",
                      json={"id_cancion": canciones["A"], "pedido_por": "Pepe"}).status_code == 400,
          "la misma mesa no puede pedir dos veces la misma cancion")

    # ---------------- Override del DJ ----------------
    cola, titulos = titulos_en_cola()
    ultimo = cola["cola"][-1]
    r = client.post(f"/api/dj/pedidos/{ultimo['id']}/subir", headers=hdj)
    check(r.status_code == 200, "el DJ sube un pedido al frente")
    _, titulos = titulos_en_cola()
    check(titulos[0] == ultimo["cancion"]["titulo"],
          f"el override del DJ manda sobre la rotacion: {titulos}")

    # ---------------- Vista del cliente ----------------
    r = client.get(f"/api/mesa/{m2['codigo']}")
    check(r.status_code == 200, "el cliente ve el estado de su mesa con solo el codigo del QR")
    estado = r.json()
    check(estado["abierta"] is True and estado["mesa"]["numero"] == "2", "sabe que su mesa esta abierta")
    check(len(estado["mis_pedidos"]) > 0, "ve sus propios pedidos")
    check(all(p["posicion"] is not None and p["espera_min"] is not None for p in estado["mis_pedidos"]),
          "cada pedido trae su posicion en la cola y la espera estimada")
    check(estado["mis_pedidos"][0]["espera_min"] >= 0, "la espera estimada es un numero de minutos")
    # No le filtramos los pedidos de las otras mesas.
    check(all(p["id_mesa"] == m2["id"] for p in estado["mis_pedidos"]), "solo ve los pedidos de su mesa")

    # Cancelar lo propio sí; lo de otra mesa no.
    mio = estado["mis_pedidos"][0]
    check(delete(f"/api/mesa/{m1['codigo']}/pedidos/{mio['id']}").status_code == 403,
          "una mesa no puede cancelar el pedido de otra (403)")
    check(delete(f"/api/mesa/{m2['codigo']}/pedidos/{mio['id']}").status_code == 204,
          "una mesa puede cancelar su propio pedido")

    # ---------------- Catálogo cerrado + sugerencias ----------------
    cat = client.get(f"/api/mesa/{m1['codigo']}/catalogo").json()
    check(len(cat) == len(canciones), "el cliente ve el catalogo del local")
    check(client.post(f"/api/mesa/{m1['codigo']}/pedidos",
                      json={"id_cancion": "C-inexistente", "pedido_por": "Juan"}).status_code == 400,
          "no se puede pedir algo que no esta en el catalogo del local")
    r = client.post(f"/api/mesa/{m1['codigo']}/sugerencias",
                    json={"titulo": "Una que no tienen", "artista": "Alguien", "pedido_por": "Juan"})
    check(r.status_code == 200, "el cliente puede sugerir una cancion que el local no tiene")
    sug = client.get("/api/dj/sugerencias", headers=hdj).json()
    check(len(sug) == 1 and sug[0]["mesa_numero"] == "1", "la sugerencia le llega al DJ con el numero de mesa")
    _, titulos = titulos_en_cola()
    check("Una que no tienen" not in titulos, "la sugerencia NO entra a la rotacion")

    # ---------------- Mesa que se va ----------------
    cola, _ = titulos_en_cola()
    pedidos_m3 = [p for p in cola["cola"] if p["id_mesa"] == m3["id"]]
    check(len(pedidos_m3) > 0, "la mesa 3 todavia tiene pedidos esperando")
    r = client.post(f"/api/mesas/{m3['id']}/cerrar", headers=h(gid))
    check(r.status_code == 200 and r.json()["pedidos_cancelados"] == len(pedidos_m3),
          f"cerrar la mesa cancela sus {len(pedidos_m3)} pedidos pendientes")
    _, titulos = titulos_en_cola()
    cola, _ = titulos_en_cola()
    check(all(p["id_mesa"] != m3["id"] for p in cola["cola"]),
          "el DJ ya no ve pedidos de la mesa que se fue")
    check(client.post(f"/api/mesa/{m3['codigo']}/pedidos",
                      json={"id_cancion": canciones["I"], "pedido_por": "Pepe"}).status_code == 400,
          "una mesa cerrada ya no puede pedir")

    # ---------------- El modo grupo sigue intacto ----------------
    g = crear_grupo("Grupo Normal Test", "Ana")
    check(g["modo"] == "grupo", "un grupo creado sin modo sigue siendo 'grupo'")
    check(client.get("/api/dj/cola", headers={**h(g["id"]), "X-DJ-Codigo": "x"}).status_code == 400,
          "un grupo normal no tiene vista de DJ (400)")


if __name__ == "__main__":
    try:
        main()
    finally:
        limpiar()
        print("datos de prueba borrados")
