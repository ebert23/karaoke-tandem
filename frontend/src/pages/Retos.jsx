import React, { useEffect, useMemo, useState } from "react";
import { IconDice, IconPlus, IconTrash } from "../components/Icons.jsx";
import { useGroup } from "../lib/GroupContext.jsx";
import { useIdentity } from "../lib/IdentityContext.jsx";
import { useToast } from "../lib/ToastContext.jsx";
import { api } from "../lib/api.js";

const CATEGORIAS = [
  { id: "Normal", emoji: "🎈" },
  { id: "Picante", emoji: "🌶️" },
  { id: "Creativo", emoji: "🎨" },
  { id: "Grupo", emoji: "👯" },
  { id: "Shots", emoji: "🥃" },
];

export default function Retos() {
  const { push } = useToast();
  const { grupo } = useGroup();
  const { usuario } = useIdentity();
  const [categoria, setCategoria] = useState("");
  const [reto, setReto] = useState(null);
  const [buscando, setBuscando] = useState(false);
  const [showForm, setShowForm] = useState(false);
  const [form, setForm] = useState({ texto: "", dificultad: "Fácil", categoria: "Normal" });
  const [enviando, setEnviando] = useState(false);
  const [baraja, setBaraja] = useState([]);
  const [verBaraja, setVerBaraja] = useState(false);
  const [borrando, setBorrando] = useState("");
  const [restaurando, setRestaurando] = useState(false);

  const esAdmin = grupo.admins?.includes(usuario.id) ?? false;

  async function cargarBaraja() {
    try {
      setBaraja(await api.retos());
    } catch (e) {
      push(e.message, "error");
    }
  }

  useEffect(() => {
    cargarBaraja();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  async function darReto() {
    setBuscando(true);
    try {
      // Se manda el que está en pantalla para que no vuelva a salir: con dos
      // o tres retos en la categoría, si no, sale siempre el mismo.
      const r = await api.retoAleatorio(categoria || undefined, reto?.id);
      setReto(r);
    } catch (e) {
      push(e.message, "error");
      setReto(null);
    } finally {
      setBuscando(false);
    }
  }

  async function crearReto(e) {
    e.preventDefault();
    if (!form.texto.trim()) return;
    setEnviando(true);
    try {
      await api.crearReto(form);
      push("¡Reto agregado a la baraja! 🎲", "success");
      setForm({ texto: "", dificultad: "Fácil", categoria: "Normal" });
      setShowForm(false);
      // La baraja se recarga y se abre: si no, el reto nuevo no se ve en
      // ningún lado y parece que no se guardó.
      await cargarBaraja();
      setVerBaraja(true);
    } catch (e) {
      push(e.message, "error");
    } finally {
      setEnviando(false);
    }
  }

  async function eliminarReto(r) {
    if (!confirm(`¿Sacar este reto de la baraja?\n\n"${r.texto}"`)) return;
    setBorrando(r.id);
    try {
      await api.eliminarReto(r.id, usuario.id);
      setBaraja((prev) => prev.filter((x) => x.id !== r.id));
      if (reto?.id === r.id) setReto(null);
    } catch (e) {
      push(e.message, "error");
    } finally {
      setBorrando("");
    }
  }

  async function restaurar() {
    setRestaurando(true);
    try {
      const antes = baraja.length;
      const lista = await api.restaurarRetos(usuario.id);
      setBaraja(lista);
      const sumados = lista.length - antes;
      push(sumados > 0 ? `Se sumaron ${sumados} retos a la baraja 🎲` : "Ya tenías todos", "success");
      setVerBaraja(true);
    } catch (e) {
      push(e.message, "error");
    } finally {
      setRestaurando(false);
    }
  }

  const porCategoria = useMemo(() => {
    const mapa = Object.fromEntries(CATEGORIAS.map((c) => [c.id, []]));
    for (const r of baraja) (mapa[r.categoria] ??= []).push(r);
    return mapa;
  }, [baraja]);

  const colorCategoria = {
    Normal: "from-cyan-500 to-blue-500",
    Picante: "from-orange-500 to-red-500",
    Creativo: "from-emerald-400 to-teal-500",
    Grupo: "from-neon-purple to-neon-pink",
    Shots: "from-amber-500 to-orange-600",
  };

  return (
    <div className="flex flex-col gap-6 max-w-lg mx-auto">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <h2 className="title-glow text-2xl">Retos y diversión</h2>
        <button onClick={() => setShowForm((s) => !s)} className="btn-ghost">
          <IconPlus /> Crear reto
        </button>
      </div>

      {showForm && (
        <form onSubmit={crearReto} className="card p-4 flex flex-col gap-3">
          <div>
            <label className="label">Texto del reto</label>
            <textarea className="input" rows={2} value={form.texto} onChange={(e) => setForm({ ...form, texto: e.target.value })} maxLength={300} required />
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="label">Dificultad</label>
              <select className="input" value={form.dificultad} onChange={(e) => setForm({ ...form, dificultad: e.target.value })}>
                <option>Fácil</option>
                <option>Medio</option>
                <option>Difícil</option>
              </select>
            </div>
            <div>
              <label className="label">Categoría</label>
              <select className="input" value={form.categoria} onChange={(e) => setForm({ ...form, categoria: e.target.value })}>
                {CATEGORIAS.map((c) => (
                  <option key={c.id}>{c.id}</option>
                ))}
              </select>
            </div>
          </div>
          <button className="btn-primary self-end" disabled={enviando}>
            {enviando ? "Guardando…" : "Guardar reto"}
          </button>
        </form>
      )}

      <div className="flex gap-2 justify-center flex-wrap">
        <button onClick={() => setCategoria("")} className={categoria === "" ? "chip-active" : "chip"}>
          Cualquiera
        </button>
        {CATEGORIAS.map((c) => (
          <button key={c.id} onClick={() => setCategoria(c.id)} className={categoria === c.id ? "chip-active" : "chip"}>
            {c.emoji} {c.id}
          </button>
        ))}
      </div>

      <div
        className={`card p-8 text-center min-h-[220px] flex flex-col items-center justify-center bg-gradient-to-br ${
          reto ? colorCategoria[reto.categoria] : ""
        } ${reto ? "!border-transparent shadow-neon" : ""}`}
      >
        {reto ? (
          <>
            <span className="chip !bg-black/20 !border-white/20 mb-3">
              {reto.categoria} · {reto.dificultad}
            </span>
            <p className="font-display font-bold text-xl leading-snug">{reto.texto}</p>
          </>
        ) : (
          <p className="text-white/40">Presiona el botón para sacar un reto</p>
        )}
      </div>

      <button onClick={darReto} className="btn-primary text-lg self-center !px-10 !py-3.5" disabled={buscando}>
        <IconDice /> {buscando ? "Girando…" : reto ? "Otro reto" : "Dar reto"}
      </button>

      {/* --- La baraja --- */}
      <div className="card p-4">
        <button
          onClick={() => setVerBaraja((v) => !v)}
          className="w-full flex items-center justify-between gap-3 text-left"
        >
          <span className="label !mb-0">La baraja ({baraja.length} retos)</span>
          <span className="text-white/40 text-sm shrink-0">{verBaraja ? "Ocultar" : "Ver todos"}</span>
        </button>

        {verBaraja && (
          <div className="mt-3 flex flex-col gap-4">
            {CATEGORIAS.map((c) => {
              const lista = porCategoria[c.id] || [];
              return (
                <div key={c.id}>
                  <p className="text-xs uppercase tracking-wide text-white/40 mb-1.5">
                    {c.emoji} {c.id} · {lista.length}
                  </p>
                  {lista.length === 0 ? (
                    <p className="text-white/30 text-sm">Sin retos en esta categoría.</p>
                  ) : (
                    <ul className="flex flex-col gap-1.5">
                      {lista.map((r) => (
                        <li key={r.id} className="flex items-start gap-2 text-sm">
                          <span className="flex-1 min-w-0 text-white/75">
                            {r.texto}
                            <span className="text-white/30"> · {r.dificultad}</span>
                          </span>
                          {esAdmin && (
                            <button
                              onClick={() => eliminarReto(r)}
                              disabled={borrando === r.id}
                              className="btn-ghost !px-2 !py-1 !text-red-300/70 hover:!text-red-300 shrink-0"
                              title="Sacar de la baraja"
                            >
                              <IconTrash />
                            </button>
                          )}
                        </li>
                      ))}
                    </ul>
                  )}
                </div>
              );
            })}
            {esAdmin ? (
              <button onClick={restaurar} disabled={restaurando} className="btn-ghost !text-xs self-start">
                {restaurando ? "Trayendo…" : "Traer los retos que faltan"}
              </button>
            ) : (
              <p className="text-white/30 text-xs">
                Solo un admin del grupo puede sacar retos de la baraja.
              </p>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
