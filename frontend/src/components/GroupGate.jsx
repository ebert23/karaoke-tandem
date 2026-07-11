import React, { useState } from "react";
import { useGroup } from "../lib/GroupContext.jsx";

export default function GroupGate({ children }) {
  const { grupo, crearGrupo, unirseAGrupo, loading, error } = useGroup();
  const [modo, setModo] = useState("crear"); // crear | unirse
  const [nombreGrupo, setNombreGrupo] = useState("");
  const [tuNombre, setTuNombre] = useState("");
  const [codigo, setCodigo] = useState("");

  if (grupo) return children;

  async function onCrear(e) {
    e.preventDefault();
    if (!nombreGrupo.trim() || !tuNombre.trim()) return;
    try {
      await crearGrupo(nombreGrupo.trim(), tuNombre.trim());
    } catch {
      /* el error ya se muestra abajo */
    }
  }

  async function onUnirse(e) {
    e.preventDefault();
    if (codigo.trim().length !== 6) return;
    try {
      await unirseAGrupo(codigo.trim());
    } catch {
      /* el error ya se muestra abajo */
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center p-6">
      <div className="w-full max-w-sm text-center">
        <div className="text-6xl mb-4 animate-floatSlow">🎉</div>
        <h1 className="title-glow text-3xl mb-2">KaraokeTandem</h1>
        <p className="text-white/50 text-sm mb-6">Crea la sala de tu grupo o únete con un código</p>

        <div className="flex gap-2 mb-4">
          <button
            onClick={() => setModo("crear")}
            className={modo === "crear" ? "chip-active flex-1" : "chip flex-1"}
          >
            Crear grupo
          </button>
          <button
            onClick={() => setModo("unirse")}
            className={modo === "unirse" ? "chip-active flex-1" : "chip flex-1"}
          >
            Unirme con código
          </button>
        </div>

        {modo === "crear" ? (
          <form onSubmit={onCrear} className="card p-5 flex flex-col gap-3">
            <div className="text-left">
              <label className="label">Nombre del grupo</label>
              <input
                className="input"
                placeholder="Ej: Amigos del barrio"
                value={nombreGrupo}
                onChange={(e) => setNombreGrupo(e.target.value)}
                maxLength={80}
                autoFocus
              />
            </div>
            <div className="text-left">
              <label className="label">Tu nombre</label>
              <input
                className="input"
                placeholder="¿Cómo te llamas?"
                value={tuNombre}
                onChange={(e) => setTuNombre(e.target.value)}
                maxLength={80}
              />
            </div>
            <button className="btn-primary w-full mt-1" disabled={loading || !nombreGrupo.trim() || !tuNombre.trim()}>
              {loading ? "Creando…" : "Crear grupo 🎤"}
            </button>
            {error && <p className="text-red-300 text-sm">{error}</p>}
          </form>
        ) : (
          <form onSubmit={onUnirse} className="card p-5 flex flex-col gap-3">
            <div className="text-left">
              <label className="label">Código de invitación</label>
              <input
                className="input text-center text-lg tracking-[0.3em]"
                placeholder="000000"
                value={codigo}
                onChange={(e) => setCodigo(e.target.value.replace(/\D/g, "").slice(0, 6))}
                inputMode="numeric"
                maxLength={6}
                autoFocus
              />
            </div>
            <button className="btn-primary w-full mt-1" disabled={loading || codigo.length !== 6}>
              {loading ? "Entrando…" : "Unirme 🎉"}
            </button>
            {error && <p className="text-red-300 text-sm">{error}</p>}
          </form>
        )}
      </div>
    </div>
  );
}
