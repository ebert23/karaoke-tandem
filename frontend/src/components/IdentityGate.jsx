import React, { useState } from "react";
import { useIdentity } from "../lib/IdentityContext.jsx";

export default function IdentityGate({ children }) {
  const { usuario, ingresar, loading, error } = useIdentity();
  const [nombre, setNombre] = useState("");

  if (usuario) return children;

  async function onSubmit(e) {
    e.preventDefault();
    if (!nombre.trim()) return;
    try {
      await ingresar(nombre.trim());
    } catch {
      /* el error ya se muestra abajo */
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center p-6">
      <div className="w-full max-w-sm text-center">
        <div className="text-6xl mb-4 animate-floatSlow">🎤</div>
        <h1 className="title-glow text-3xl mb-2">KaraokeTandem</h1>
        <p className="text-white/50 text-sm mb-8">Escribe tu nombre para entrar a la fiesta</p>
        <form onSubmit={onSubmit} className="card p-5 flex flex-col gap-3">
          <input
            className="input text-center text-lg"
            placeholder="Tu nombre"
            value={nombre}
            onChange={(e) => setNombre(e.target.value)}
            maxLength={40}
            autoFocus
          />
          <button className="btn-primary w-full" disabled={loading || !nombre.trim()}>
            {loading ? "Entrando…" : "Entrar 🎉"}
          </button>
          {error && <p className="text-red-300 text-sm">{error}</p>}
        </form>
      </div>
    </div>
  );
}
