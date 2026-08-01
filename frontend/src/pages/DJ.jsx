import React, { useEffect, useRef, useState } from "react";
import { api, guardarSesionDj, sesionDj } from "../lib/api.js";
import { useToast } from "../lib/ToastContext.jsx";

// El DJ necesita ver los cambios casi al instante: las mesas piden desde el
// celular mientras él está poniendo la canción anterior.
const POLL_DJ_MS = 6000;

function Login({ onEntrar }) {
  const { push } = useToast();
  const [codigo, setCodigo] = useState("");
  const [entrando, setEntrando] = useState(false);

  async function enviar(e) {
    e.preventDefault();
    setEntrando(true);
    try {
      const grupo = await api.djEntrar(codigo.trim());
      guardarSesionDj({ id_grupo: grupo.id, nombre: grupo.nombre, codigo: codigo.trim() });
      onEntrar();
    } catch (err) {
      push(err.message, "error");
    } finally {
      setEntrando(false);
    }
  }

  return (
    <div className="min-h-screen flex flex-col items-center justify-center gap-6 p-6">
      <h1 className="title-glow text-4xl">Consola del DJ</h1>
      <form onSubmit={enviar} className="card p-6 w-full max-w-sm space-y-4">
        <div>
          <label className="label">Código del local</label>
          <input
            value={codigo}
            onChange={(e) => setCodigo(e.target.value)}
            placeholder="Pegá el código que te dio el local"
            className="input"
            autoFocus
          />
        </div>
        <button disabled={entrando || !codigo.trim()} className="btn-primary w-full !py-3">
          {entrando ? "Entrando…" : "Entrar"}
        </button>
      </form>
    </div>
  );
}

// La tarjeta grande de "ahora canta". Lo que el DJ lee al micrófono es la
// mesa y el nombre, así que eso va gigante y la canción abajo.
function Ahora({ pedido, onCantada, onNoVino, ocupado }) {
  if (!pedido) return null;
  return (
    <div className="card p-5 border-neon-pink/50 bg-neon-pink/5">
      <p className="text-xs uppercase tracking-widest text-neon-pinklight mb-2">Ahora canta</p>
      <div className="flex items-baseline gap-3 flex-wrap">
        <span className="font-display font-extrabold text-5xl sm:text-6xl leading-none text-white">
          Mesa {pedido.mesa_numero}
        </span>
        <span className="font-display font-bold text-3xl sm:text-4xl text-neon-pinklight leading-none">
          {pedido.pedido_por || "—"}
        </span>
      </div>
      <p className="text-xl mt-3 text-white/85">{pedido.cancion?.titulo}</p>
      <p className="text-white/45">{pedido.cancion?.artista}</p>
      {pedido.repetida && (
        <p className="mt-2 text-amber-300 text-sm">
          ⚠ Ya se cantó
          {pedido.cantada_hace_min !== null ? ` hace ${pedido.cantada_hace_min} min` : " esta noche"}
        </p>
      )}
      <div className="grid grid-cols-2 gap-3 mt-4">
        <button onClick={onCantada} disabled={ocupado} className="btn-primary !py-4 !text-base">
          ✓ Listo
        </button>
        <button onClick={onNoVino} disabled={ocupado} className="btn-ghost !py-4 !text-base">
          ✗ No vino
        </button>
      </div>
    </div>
  );
}

export default function DJ() {
  const { push } = useToast();
  const [sesion, setSesion] = useState(() => sesionDj());
  const [datos, setDatos] = useState(null);
  const [sugerencias, setSugerencias] = useState([]);
  const [verSugerencias, setVerSugerencias] = useState(false);
  const [ocupado, setOcupado] = useState(false);
  const [error, setError] = useState("");
  const versionRef = useRef(0);

  async function cargar({ desdeSondeo = false } = {}) {
    const version = versionRef.current;
    try {
      const d = await api.djCola();
      if (desdeSondeo && versionRef.current !== version) return;
      setDatos(d);
      setError("");
    } catch (e) {
      // Sin noche abierta no es un error del DJ: el local todavía no arrancó.
      if (!desdeSondeo) setError(e.message);
    }
  }

  async function conAccionLocal(fn) {
    versionRef.current += 1;
    setOcupado(true);
    try {
      return await fn();
    } finally {
      versionRef.current += 1;
      setOcupado(false);
    }
  }

  useEffect(() => {
    if (!sesion) return;
    cargar();
    api.djSugerencias().then(setSugerencias).catch(() => {});
    const id = setInterval(() => cargar({ desdeSondeo: true }), POLL_DJ_MS);
    return () => clearInterval(id);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [sesion]);

  if (!sesion) return <Login onEntrar={() => setSesion(sesionDj())} />;

  async function accion(fn, mensaje) {
    try {
      await conAccionLocal(fn);
      await cargar();
      if (mensaje) push(mensaje, "success");
    } catch (e) {
      push(e.message, "error");
    }
  }

  const ahora = datos?.ahora;
  const cola = datos?.cola || [];

  return (
    <div className="min-h-screen p-4 pb-8 max-w-2xl mx-auto space-y-4">
      <header className="flex items-center justify-between gap-3">
        <div>
          <h1 className="title-glow text-2xl leading-none">{sesion.nombre}</h1>
          <p className="text-white/40 text-xs mt-1">
            {datos ? `${datos.mesas_abiertas} mesas abiertas · ${datos.total_cantadas} cantadas` : "…"}
          </p>
        </div>
        <button
          onClick={() => {
            guardarSesionDj(null);
            setSesion(null);
          }}
          className="btn-ghost !text-xs"
        >
          Salir
        </button>
      </header>

      {error && (
        <div className="card p-4 text-center">
          <p className="text-white/60 text-sm">{error}</p>
        </div>
      )}

      {ahora ? (
        <Ahora
          pedido={ahora}
          ocupado={ocupado}
          onCantada={() => accion(() => api.djCantada(ahora.id))}
          onNoVino={() => accion(() => api.djNoVino(ahora.id), "Se atrasó una vuelta")}
        />
      ) : (
        <div className="card p-6 text-center">
          <p className="text-white/60 mb-4">
            {cola.length > 0 ? "Listo para el siguiente turno" : "No hay nadie esperando todavía"}
          </p>
          <button
            onClick={() => accion(() => api.djSiguiente())}
            disabled={ocupado || cola.length === 0}
            className="btn-primary !py-4 !px-8 !text-base"
          >
            ▶ Llamar al siguiente
          </button>
        </div>
      )}

      <section>
        <div className="flex items-center justify-between mb-2">
          <h2 className="label !mb-0">Siguen ({cola.length})</h2>
          {sugerencias.length > 0 && (
            <button onClick={() => setVerSugerencias((v) => !v)} className="btn-ghost !text-xs !py-1">
              💡 {sugerencias.length} sugerencias
            </button>
          )}
        </div>

        {verSugerencias && (
          <ul className="card p-3 mb-3 space-y-2">
            <li className="text-white/40 text-xs">Canciones que pidieron y el local no tiene:</li>
            {sugerencias.map((s) => (
              <li key={s.id} className="text-sm">
                <span className="font-semibold">{s.titulo}</span>
                {s.artista && <span className="text-white/45"> — {s.artista}</span>}
                <span className="text-white/35 text-xs"> · Mesa {s.mesa_numero}</span>
              </li>
            ))}
          </ul>
        )}

        {cola.length === 0 ? (
          <p className="text-white/40 text-sm py-3">La cola está vacía.</p>
        ) : (
          <ul className="space-y-2">
            {cola.map((p, i) => (
              <li key={p.id} className="card p-3 flex items-center gap-3">
                <div className="w-9 h-9 shrink-0 rounded-lg bg-white/10 grid place-items-center font-display font-bold text-sm">
                  {i + 1}
                </div>
                <div className="min-w-0 flex-1">
                  <p className="font-display font-bold leading-tight">
                    Mesa {p.mesa_numero} <span className="text-neon-pinklight">· {p.pedido_por || "—"}</span>
                  </p>
                  <p className="text-white/60 text-sm truncate">{p.cancion?.titulo}</p>
                  <p className="text-white/35 text-xs truncate">{p.cancion?.artista}</p>
                  {p.repetida && (
                    <p className="text-amber-300/80 text-xs mt-0.5">
                      ⚠ ya se cantó
                      {p.cantada_hace_min !== null ? ` hace ${p.cantada_hace_min} min` : ""}
                    </p>
                  )}
                </div>
                <div className="flex flex-col gap-1 shrink-0">
                  {i > 0 && (
                    <button
                      onClick={() => accion(() => api.djSubir(p.id))}
                      disabled={ocupado}
                      className="btn-ghost !px-2 !py-1 !text-xs"
                      title="Poner primero"
                    >
                      ↑
                    </button>
                  )}
                  <button
                    onClick={() => accion(() => api.djCancelar(p.id))}
                    disabled={ocupado}
                    className="btn-danger !px-2 !py-1 !text-xs"
                    title="Sacar de la cola"
                  >
                    ✕
                  </button>
                </div>
              </li>
            ))}
          </ul>
        )}
      </section>
    </div>
  );
}
