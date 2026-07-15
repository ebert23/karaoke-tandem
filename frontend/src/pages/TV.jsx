import React, { useEffect, useRef, useState } from "react";
import { Link } from "react-router-dom";
import QRCode from "qrcode";
import YouTubePlayer from "../components/YouTubePlayer.jsx";
import { useGroup } from "../lib/GroupContext.jsx";
import { useToast } from "../lib/ToastContext.jsx";
import { api } from "../lib/api.js";
import { formatCantantes } from "../lib/format.js";
import { linkInvitacion } from "../lib/invite.js";
import { POLL_MS } from "../lib/constants.js";

function formatTiempo(segundos) {
  const s = Math.max(0, Math.round(segundos));
  const mm = String(Math.floor(s / 60)).padStart(2, "0");
  const ss = String(s % 60).padStart(2, "0");
  return `${mm}:${ss}`;
}

// Generado 100% client-side (sin pegarle a un servicio externo) con el
// mismo link de invitación que ya usa Grupo.jsx.
function QrInvitacion({ grupo, className }) {
  const [dataUrl, setDataUrl] = useState("");
  useEffect(() => {
    let vivo = true;
    QRCode.toDataURL(linkInvitacion(grupo), { width: 320, margin: 1, color: { dark: "#0a0a12", light: "#ffffff" } })
      .then((url) => vivo && setDataUrl(url))
      .catch(() => {});
    return () => {
      vivo = false;
    };
  }, [grupo.codigo]);
  if (!dataUrl) return null;
  return <img src={dataUrl} alt="Código QR para unirte" className={className} />;
}

export default function TV() {
  const { grupo } = useGroup();
  const { push } = useToast();
  const [sesion, setSesion] = useState(undefined); // undefined = cargando, null = sin sesión
  const [turnos, setTurnos] = useState([]);
  const [progreso, setProgreso] = useState(null); // {segundosTranscurridos, duracion}
  const playerRef = useRef(null);

  async function cargar() {
    try {
      const s = await api.sesionActiva();
      setSesion(s);
      if (s) setTurnos(await api.detalleSesion(s.id_sesion));
    } catch (e) {
      push(e.message, "error");
      setSesion(null);
    }
  }

  useEffect(() => {
    cargar();
    const id = setInterval(cargar, POLL_MS);
    return () => clearInterval(id);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const pendiente = turnos.find((t) => t.estado === "Pendiente");
  const cola = turnos.filter((t) => t.estado === "En cola");

  useEffect(() => {
    setProgreso(null);
  }, [pendiente?.turno]);

  async function pasarSiguiente() {
    if (!sesion) return;
    try {
      const t = await api.siguienteCancion(sesion.id_sesion);
      setTurnos((prev) => [...prev.filter((x) => x.id_cancion !== t.id_cancion), t]);
    } catch {
      /* sin más canciones disponibles o error puntual — la pantalla de espera ya lo refleja */
    }
  }

  function pantallaCompleta() {
    document.documentElement.requestFullscreen?.();
  }

  if (sesion === undefined) {
    return <div className="min-h-screen flex items-center justify-center text-white/40">Cargando…</div>;
  }

  if (sesion === null) {
    return (
      <div className="min-h-screen flex flex-col items-center justify-center gap-6 p-8 text-center">
        <h1 className="title-glow text-4xl">🎤 {grupo.nombre}</h1>
        <p className="text-white/50 text-lg">Todavía no hay una sesión de karaoke activa.</p>
        <QrInvitacion grupo={grupo} className="rounded-xl" />
        <Link to="/karaoke" className="btn-ghost">
          Volver
        </Link>
      </div>
    );
  }

  const tiempoRestante = progreso ? formatTiempo(progreso.duracion - progreso.segundosTranscurridos) : null;

  return (
    <div className="min-h-screen flex flex-col p-6 gap-4 relative">
      <button onClick={pantallaCompleta} className="btn-ghost !text-xs absolute top-4 right-4 z-10">
        ⛶ Pantalla completa
      </button>

      {pendiente ? (
        <div className="flex-1 flex flex-col gap-3 min-h-0">
          <div className="text-center shrink-0">
            <p className="text-neon-pinklight uppercase tracking-widest text-sm font-semibold">Cantando ahora</p>
            <h1 className="title-glow text-5xl font-display font-extrabold">{formatCantantes(pendiente.cantada_por)}</h1>
            <p className="text-2xl text-white/70 mt-1">
              {pendiente.cancion?.titulo} <span className="text-white/40">— {pendiente.cancion?.artista}</span>
            </p>
          </div>
          <div className="flex-1 min-h-0">
            <YouTubePlayer
              ref={playerRef}
              linkYoutube={pendiente.cancion?.link_youtube}
              autoplay
              onEnd={pasarSiguiente}
              onProgress={setProgreso}
            />
          </div>
          <div className="flex items-center justify-center gap-3 flex-wrap shrink-0">
            {tiempoRestante && <span className="font-display font-extrabold text-3xl tabular-nums mr-2">{tiempoRestante}</span>}
            <button onClick={() => playerRef.current?.pause()} className="btn-ghost !text-xs">
              ⏸ Pausar
            </button>
            <button onClick={() => playerRef.current?.play()} className="btn-ghost !text-xs">
              ⏵ Reanudar
            </button>
            <button onClick={() => playerRef.current?.seekForward10()} className="btn-ghost !text-xs">
              ⏩ +10s
            </button>
            <input
              type="range"
              min="0"
              max="100"
              defaultValue="100"
              onChange={(e) => playerRef.current?.setVolume(Number(e.target.value))}
              className="w-24"
              title="Volumen"
            />
            <button onClick={() => playerRef.current?.requestFullscreen()} className="btn-ghost !text-xs">
              ⛶ Video
            </button>
            <button onClick={pasarSiguiente} className="btn-ghost !text-xs">
              ⏭ Saltar
            </button>
          </div>
        </div>
      ) : (
        <div className="flex-1 flex flex-col items-center justify-center gap-6 text-center">
          <h1 className="title-glow text-4xl">{grupo.nombre}</h1>
          <p className="text-white/50 text-xl">
            {cola.length > 0 ? "Preparando la siguiente canción…" : "Esperando la próxima canción 🎶"}
          </p>
          <QrInvitacion grupo={grupo} className="rounded-xl" />
          <p className="text-white/40 text-sm">Escaneá el código para unirte con tu celular</p>
        </div>
      )}

      {cola.length > 0 && (
        <div className="border-t border-white/10 pt-3 flex items-center gap-4 overflow-x-auto shrink-0">
          <span className="text-white/40 text-xs uppercase tracking-widest shrink-0">A seguir</span>
          {cola.map((t, i) => (
            <span key={t.id_cancion} className="chip shrink-0 !text-sm">
              {i + 1}. {t.cancion?.titulo}
            </span>
          ))}
        </div>
      )}

      {pendiente && (
        <div className="absolute bottom-4 right-4">
          <QrInvitacion grupo={grupo} className="w-20 h-20 rounded-lg opacity-80" />
        </div>
      )}
    </div>
  );
}
