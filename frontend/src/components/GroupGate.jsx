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
          <div className="flex items-center gap-3 mb-4">
            <span className="equalizer" aria-hidden="true"><i /><i /><i /><i /></span>
            <p className="eyebrow">Tu karaoke, tu grupo</p>
          </div>
          <h2 className="font-display font-bold text-4xl sm:text-5xl tracking-[-0.055em] leading-[0.95]">Que empiece<br /><span className="text-neon-pinklight">la noche.</span></h2>
          <p className="text-white/55 text-sm mt-4 max-w-sm">Arma la sala, suma a tus amigos y deja que la música decida quién sigue.</p>
        </div>

        <div className="flex gap-1 mb-3 p-1 rounded-xl bg-ink-950/55 border border-white/10 backdrop-blur-xl">
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
          <form onSubmit={onCrear} className="card p-5 sm:p-6 flex flex-col gap-4">
            <div className="text-left">
              <label htmlFor="nombre-grupo" className="label">Nombre del grupo</label>
              <input
                id="nombre-grupo"
                className="input"
                placeholder="Ej: Amigos del barrio"
                value={nombreGrupo}
                onChange={(e) => setNombreGrupo(e.target.value)}
                maxLength={80}
                autoFocus
              />
            </div>
            <div className="text-left">
              <label htmlFor="tu-nombre" className="label">Tu nombre</label>
              <input
                id="tu-nombre"
                className="input"
                placeholder="¿Cómo te llamas?"
                value={tuNombre}
                onChange={(e) => setTuNombre(e.target.value)}
                maxLength={80}
              />
            </div>
            <button className="btn-primary w-full mt-1" disabled={loading || !nombreGrupo.trim() || !tuNombre.trim()}>
              {loading ? "Creando…" : "Crear sala"}
            </button>
            {error && <p className="text-red-300 text-sm">{error}</p>}
          </form>
        ) : (
          <form onSubmit={onUnirse} className="card p-5 sm:p-6 flex flex-col gap-4">
            <div className="text-left">
              <label htmlFor="codigo-invitacion" className="label">Código de invitación</label>
              <input
                id="codigo-invitacion"
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
              {loading ? "Entrando…" : "Entrar a la sala"}
            </button>
            {error && <p className="text-red-300 text-sm">{error}</p>}
          </form>
        )}
      </div>
    </div>
  );
}
