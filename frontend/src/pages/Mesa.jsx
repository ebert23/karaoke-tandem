import React, { useEffect, useMemo, useRef, useState } from "react";
import { useParams } from "react-router-dom";
import { api } from "../lib/api.js";
import { useToast } from "../lib/ToastContext.jsx";
import { nombreMesaStorageKey } from "../lib/storageKeys.js";

// Más frecuente que el sondeo del modo grupo (20s): acá el dato que importa es
// "cuánto falta para que me toque", y verlo desactualizado es justo lo que
// hace que la gente termine yendo a preguntarle al DJ.
const POLL_MESA_MS = 10000;

function Espera({ minutos }) {
  if (minutos === null || minutos === undefined) return null;
  if (minutos <= 0) return <span className="text-neon-cyan font-semibold">¡Ya casi!</span>;
  if (minutos < 60) return <span>~{minutos} min</span>;
  const h = Math.floor(minutos / 60);
  return (
    <span>
      ~{h}h {minutos % 60}min
    </span>
  );
}

export default function Mesa() {
  const { codigo } = useParams();
  const { push } = useToast();

  const [estado, setEstado] = useState(undefined); // undefined = cargando, null = código inválido
  const [catalogo, setCatalogo] = useState([]);
  const [busqueda, setBusqueda] = useState("");
  const [nombre, setNombre] = useState(() => localStorage.getItem(nombreMesaStorageKey(codigo)) || "");
  const [pidiendo, setPidiendo] = useState("");
  const [mostrarSugerir, setMostrarSugerir] = useState(false);
  const [sugerencia, setSugerencia] = useState({ titulo: "", artista: "" });

  // Mismo patrón anti-carrera que Karaoke.jsx: una respuesta del sondeo que
  // salió antes de que el usuario pidiera algo no debe pisar el estado nuevo.
  const versionRef = useRef(0);

  async function cargar({ desdeSondeo = false } = {}) {
    const version = versionRef.current;
    try {
      const e = await api.estadoMesa(codigo);
      if (desdeSondeo && versionRef.current !== version) return;
      setEstado(e);
    } catch (err) {
      if (!desdeSondeo) {
        push(err.message, "error");
        setEstado(null);
      }
    }
  }

  async function conAccionLocal(fn) {
    versionRef.current += 1;
    try {
      return await fn();
    } finally {
      versionRef.current += 1;
    }
  }

  useEffect(() => {
    cargar();
    api.catalogoMesa(codigo).then(setCatalogo).catch(() => {});
    const id = setInterval(() => cargar({ desdeSondeo: true }), POLL_MESA_MS);
    return () => clearInterval(id);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [codigo]);

  function guardarNombre(v) {
    setNombre(v);
    localStorage.setItem(nombreMesaStorageKey(codigo), v);
  }

  const filtrado = useMemo(() => {
    const q = busqueda.trim().toLowerCase();
    if (!q) return catalogo.slice(0, 40);
    // Busca por título Y por artista: en un karaoke la gente piensa "algo de
    // Alejandro Fernández" mucho más seguido que un título exacto.
    return catalogo
      .filter((c) => c.titulo.toLowerCase().includes(q) || c.artista.toLowerCase().includes(q))
      .slice(0, 40);
  }, [catalogo, busqueda]);

  const idsPedidos = useMemo(
    () => new Set((estado?.mis_pedidos || []).map((p) => p.id_cancion)),
    [estado],
  );

  async function pedir(cancion) {
    if (!nombre.trim()) {
      push("Escribí tu nombre primero así el DJ sabe a quién llamar", "error");
      return;
    }
    setPidiendo(cancion.id);
    try {
      await conAccionLocal(() => api.pedirCancion(codigo, cancion.id, nombre.trim()));
      push(`"${cancion.titulo}" anotada 🎤`, "success");
      await cargar();
      setBusqueda("");
    } catch (e) {
      push(e.message, "error");
    } finally {
      setPidiendo("");
    }
  }

  async function cancelar(pedido) {
    try {
      await conAccionLocal(() => api.cancelarPedido(codigo, pedido.id));
      await cargar();
    } catch (e) {
      push(e.message, "error");
    }
  }

  async function enviarSugerencia(e) {
    e.preventDefault();
    try {
      await api.sugerirCancion(codigo, sugerencia.titulo, sugerencia.artista, nombre.trim());
      push("Se la pasamos al DJ. Puede que no la tengan hoy 🙏", "success");
      setSugerencia({ titulo: "", artista: "" });
      setMostrarSugerir(false);
    } catch (err) {
      push(err.message, "error");
    }
  }

  if (estado === undefined) {
    return <div className="min-h-screen flex items-center justify-center text-white/40">Cargando…</div>;
  }

  if (estado === null) {
    return (
      <div className="min-h-screen flex flex-col items-center justify-center gap-3 p-8 text-center">
        <h1 className="title-glow text-3xl">Código no encontrado</h1>
        <p className="text-white/50">Escaneá de nuevo el QR de tu mesa o pedile ayuda al mozo.</p>
      </div>
    );
  }

  if (!estado.abierta) {
    return (
      <div className="min-h-screen flex flex-col items-center justify-center gap-3 p-8 text-center">
        <h1 className="title-glow text-3xl">Mesa {estado.mesa.numero}</h1>
        <p className="text-white/60">Esta mesa todavía no está abierta.</p>
        <p className="text-white/40 text-sm">Pedile al mozo que la habilite y volvé a escanear.</p>
      </div>
    );
  }

  return (
    <div className="min-h-screen pb-28">
      <header className="p-4 border-b border-white/10 sticky top-0 bg-ink-950/95 backdrop-blur z-10">
        <div className="flex items-center justify-between gap-3">
          <div>
            <p className="text-white/40 text-xs uppercase tracking-widest">Mesa</p>
            <h1 className="title-glow text-2xl leading-none">{estado.mesa.numero}</h1>
          </div>
          {/* Con el nombre ya puesto alcanza con una cajita chica para
              corregirlo. Sin nombre, el pedido no puede salir, y eso merece
              la tarjeta grande de abajo en vez de un input escondido acá. */}
          {nombre.trim() && (
            <div className="flex-1 max-w-[55%]">
              <input
                value={nombre}
                onChange={(e) => guardarNombre(e.target.value)}
                placeholder="Tu nombre"
                maxLength={40}
                className="input !py-2 !text-sm"
              />
            </div>
          )}
        </div>
      </header>

      {!nombre.trim() && (
        <div className="m-4 p-4 rounded-2xl border border-amber-400/40 bg-amber-400/10">
          <p className="font-display font-bold text-amber-200">¿Cómo te llamás?</p>
          <p className="text-white/60 text-sm mt-1 mb-3">
            El DJ va a decir tu nombre por el micrófono cuando te toque.
          </p>
          <input
            value={nombre}
            onChange={(e) => guardarNombre(e.target.value)}
            placeholder="Tu nombre"
            maxLength={40}
            autoFocus
            className="input"
          />
        </div>
      )}

      {estado.ahora && (
        <div
          className={`mx-4 mt-4 p-3 rounded-2xl border ${
            estado.ahora.es_mi_mesa
              ? "border-neon-pink bg-neon-pink/10 animate-pulseGlow"
              : "border-white/10 bg-white/5"
          }`}
        >
          <p className="text-xs uppercase tracking-widest text-neon-pinklight">
            {estado.ahora.es_mi_mesa ? "¡Les toca! 🎤" : "Sonando ahora"}
          </p>
          <p className="font-display font-bold">{estado.ahora.cancion?.titulo}</p>
          <p className="text-white/50 text-sm">
            {estado.ahora.cancion?.artista} · Mesa {estado.ahora.mesa_numero} — {estado.ahora.pedido_por}
          </p>
        </div>
      )}

      <section className="p-4">
        <h2 className="label">Tu lista ({estado.mis_pedidos.length})</h2>
        {estado.mis_pedidos.length === 0 ? (
          <p className="text-white/40 text-sm py-2">
            Todavía no pediste nada. Buscá una canción abajo y anotate.
          </p>
        ) : (
          <ul className="space-y-2">
            {estado.mis_pedidos.map((p) => (
              <li key={p.id} className="card p-3 flex items-center gap-3">
                <div className="w-11 h-11 shrink-0 rounded-xl bg-gradient-to-br from-neon-purple to-neon-pink grid place-items-center font-display font-extrabold">
                  {p.posicion}
                </div>
                <div className="min-w-0 flex-1">
                  <p className="font-semibold truncate">{p.cancion?.titulo}</p>
                  <p className="text-white/45 text-xs truncate">
                    {p.cancion?.artista} · {p.pedido_por}
                  </p>
                  <p className="text-xs text-white/60 mt-0.5">
                    Faltan <Espera minutos={p.espera_min} />
                  </p>
                </div>
                <button onClick={() => cancelar(p)} className="btn-ghost !px-2.5 !py-1.5 !text-xs shrink-0">
                  Quitar
                </button>
              </li>
            ))}
          </ul>
        )}
      </section>

      <section className="px-4">
        <h2 className="label">Buscar en el catálogo</h2>
        <input
          value={busqueda}
          onChange={(e) => setBusqueda(e.target.value)}
          placeholder="Canción o artista…"
          className="input"
        />

        <ul className="mt-3 space-y-2">
          {filtrado.map((c) => {
            const yaPedida = idsPedidos.has(c.id);
            return (
              <li key={c.id} className="card p-3 flex items-center gap-3">
                <div className="min-w-0 flex-1">
                  <p className="font-semibold truncate">{c.titulo}</p>
                  <p className="text-white/45 text-xs truncate">{c.artista}</p>
                </div>
                <button
                  onClick={() => pedir(c)}
                  // Sin nombre el pedido no puede salir: mejor que el botón
                  // lo diga en vez de aceptar el toque y tirar un aviso que
                  // se desvanece.
                  disabled={yaPedida || pidiendo === c.id || !nombre.trim()}
                  className="btn-primary !px-3 !py-1.5 !text-xs shrink-0"
                >
                  {yaPedida
                    ? "Anotada"
                    : pidiendo === c.id
                      ? "…"
                      : !nombre.trim()
                        ? "Poné tu nombre ↑"
                        : "+ Cantar"}
                </button>
              </li>
            );
          })}
        </ul>

        {busqueda.trim() && filtrado.length === 0 && (
          <div className="text-center py-6">
            <p className="text-white/50 text-sm mb-3">No encontramos "{busqueda}" en el catálogo del local.</p>
            <button onClick={() => { setMostrarSugerir(true); setSugerencia({ titulo: busqueda, artista: "" }); }} className="btn-ghost !text-xs">
              Pedirla igual
            </button>
          </div>
        )}
      </section>

      {mostrarSugerir && (
        <div className="fixed inset-0 z-50 bg-black/70 backdrop-blur-sm flex items-end sm:items-center justify-center p-4">
          <form onSubmit={enviarSugerencia} className="card p-5 w-full max-w-sm space-y-3">
            <h3 className="font-display font-bold text-lg">Pedir una que no está</h3>
            <p className="text-white/50 text-xs">
              Le llega al DJ como sugerencia. Puede que hoy no la tenga para poner.
            </p>
            <div>
              <label className="label">Canción</label>
              <input
                value={sugerencia.titulo}
                onChange={(e) => setSugerencia((s) => ({ ...s, titulo: e.target.value }))}
                className="input"
                required
              />
            </div>
            <div>
              <label className="label">Artista</label>
              <input
                value={sugerencia.artista}
                onChange={(e) => setSugerencia((s) => ({ ...s, artista: e.target.value }))}
                className="input"
              />
            </div>
            <div className="flex gap-2 pt-1">
              <button type="submit" className="btn-primary flex-1">Enviar</button>
              <button type="button" onClick={() => setMostrarSugerir(false)} className="btn-ghost">
                Cancelar
              </button>
            </div>
          </form>
        </div>
      )}

      <footer className="fixed bottom-0 inset-x-0 p-3 bg-ink-950/95 backdrop-blur border-t border-white/10 text-center">
        <p className="text-white/40 text-xs">
          {estado.total_en_cola} canciones en la cola del salón · máximo {estado.max_pedidos} por mesa
        </p>
      </footer>
    </div>
  );
}
