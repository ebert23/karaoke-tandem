import React, { useState } from "react";
import { IconDice, IconPlus } from "../components/Icons.jsx";
import { useToast } from "../lib/ToastContext.jsx";
import { api } from "../lib/api.js";

const CATEGORIAS = [
  { id: "Normal", emoji: "🎈" },
  { id: "Picante", emoji: "🌶️" },
  { id: "Creativo", emoji: "🎨" },
  { id: "Grupo", emoji: "👯" },
];

export default function Retos() {
  const { push } = useToast();
  const [categoria, setCategoria] = useState("");
  const [reto, setReto] = useState(null);
  const [buscando, setBuscando] = useState(false);
  const [showForm, setShowForm] = useState(false);
  const [form, setForm] = useState({ texto: "", dificultad: "Fácil", categoria: "Normal" });
  const [enviando, setEnviando] = useState(false);

  async function darReto() {
    setBuscando(true);
    try {
      const r = await api.retoAleatorio(categoria || undefined);
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
    } catch (e) {
      push(e.message, "error");
    } finally {
      setEnviando(false);
    }
  }

  const colorCategoria = {
    Normal: "from-cyan-500 to-blue-500",
    Picante: "from-orange-500 to-red-500",
    Creativo: "from-emerald-400 to-teal-500",
    Grupo: "from-neon-purple to-neon-pink",
  };

  return (
    <div className="flex flex-col gap-6 max-w-lg mx-auto">
      <div className="flex items-center justify-between">
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
    </div>
  );
}
