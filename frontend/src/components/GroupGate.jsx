import React, { useEffect, useState } from "react";
import { useSearchParams } from "react-router-dom";
import { useGroup } from "../lib/GroupContext.jsx";

export default function GroupGate({ children }) {
  const { grupo, crearGrupo, unirseAGrupo, loading, error } = useGroup();
  const [searchParams] = useSearchParams();
  const codigoInvitacion = (searchParams.get("codigo") || "").replace(/\D/g, "").slice(0, 6);
  const [modo, setModo] = useState(codigoInvitacion ? "unirse" : "crear"); // crear | unirse
  const [nombreGrupo, setNombreGrupo] = useState("");
  const [tuNombre, setTuNombre] = useState("");
  const [codigo, setCodigo] = useState(codigoInvitacion);
  // Si vinimos de un link de invitación (?codigo=), intentamos unirnos solos
  // antes de mostrar el formulario — el usuario solo tiene que tocar el link.
  const [autoUniendo, setAutoUniendo] = useState(codigoInvitacion.length === 6);

  useEffect(() => {
    if (codigoInvitacion.length !== 6) return;
    unirseAGrupo(codigoInvitacion)
      .catch(() => {
        /* el error ya se muestra abajo; el usuario puede reintentar a mano */
      })
      .finally(() => setAutoUniendo(false));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // Si venimos de un link de invitación, hay que esperar a que termine el
  // auto-join ANTES de decidir si mostrar la sala guardada: si el celular ya
  // tenía otra sala vieja en localStorage, mostrarla de una (grupo truthy)
  // dejaba montado todo el árbol (Karaoke.jsx incluido) con la sala vieja
  // mientras el join a la sala nueva todavía estaba en vuelo — y como
  // Karaoke.jsx carga la sesión activa una sola vez al montar, quedaba
  // pegado mostrando la sesión pasada de la sala vieja para siempre.
  if (autoUniendo) {
    return (
      <div className="min-h-screen flex items-center justify-center p-6">
        <p className="text-white/60 text-center">Uniéndote a la sala…</p>
      </div>
    );
  }

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
        <p className="text-white/60 text-sm mb-6">Crea la sala de tu grupo o únete con un código</p>

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
