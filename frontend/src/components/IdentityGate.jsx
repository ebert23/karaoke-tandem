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
    <div className="min-h-screen relative flex flex-col justify-end overflow-hidden">
      <img
        src="/images/portada.webp"
        alt="KaraokeTandem — canta juntos, conecta"
        fetchpriority="high"
        className="absolute inset-0 w-full h-full object-cover object-top"
      />
      <div className="absolute inset-0 bg-gradient-to-t from-ink-950 via-ink-950/75 to-transparent" />
      <h1 className="sr-only">KaraokeTandem</h1>

      <div className="relative w-full max-w-sm mx-auto p-6 pt-10 text-center">
        <p className="text-white/60 text-sm mb-6">Escribe tu nombre para entrar a la fiesta</p>
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
