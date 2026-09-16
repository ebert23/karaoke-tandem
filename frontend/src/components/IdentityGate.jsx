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
    <div className="min-h-screen relative flex items-end lg:items-center overflow-hidden">
      <img
        src="/images/portada.webp"
        alt="KaraokeTandem — canta juntos, conecta"
        fetchpriority="high"
        className="absolute inset-0 w-full h-full object-cover object-[52%_top] lg:object-center scale-[1.02]"
      />
      <div className="absolute inset-0 bg-gradient-to-t from-ink-950 via-ink-950/70 to-ink-950/10 lg:bg-gradient-to-r lg:from-ink-950/15 lg:via-ink-950/25 lg:to-ink-950" />
      <h1 className="sr-only">KaraokeTandem</h1>

      <div className="relative w-full lg:w-[31rem] lg:ml-auto lg:mr-[8vw] p-5 sm:p-7 lg:p-0 pb-8">
        <div className="mb-6">
          <div className="flex items-center gap-3 mb-4"><span className="equalizer" aria-hidden="true"><i /><i /><i /><i /></span><p className="eyebrow">Ya casi estás dentro</p></div>
          <h2 className="font-display font-bold text-4xl sm:text-5xl tracking-[-0.055em] leading-[0.95]">¿Quién toma<br /><span className="text-neon-pinklight">el micrófono?</span></h2>
          <p className="text-white/55 text-sm mt-4">Usaremos tu nombre para asignar turnos y sumar puntos.</p>
        </div>
        <form onSubmit={onSubmit} className="card p-5 sm:p-6 flex flex-col gap-4">
          <label htmlFor="nombre-usuario" className="label !mb-[-0.25rem]">Tu nombre</label>
          <input
            id="nombre-usuario"
            className="input text-center text-lg"
            placeholder="Tu nombre"
            value={nombre}
            onChange={(e) => setNombre(e.target.value)}
            maxLength={40}
            autoFocus
          />
          <button className="btn-primary w-full" disabled={loading || !nombre.trim()}>
            {loading ? "Entrando…" : "Entrar a la fiesta"}
          </button>
          {error && <p className="text-red-300 text-sm">{error}</p>}
        </form>
      </div>
    </div>
  );
}
