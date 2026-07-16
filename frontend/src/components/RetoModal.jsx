import React, { useEffect, useMemo, useState } from "react";
import { IconDice } from "./Icons.jsx";
import { api } from "../lib/api.js";
import { elegirCancionAsignada } from "../lib/retoCanciones.js";
import { mensajeAleatorio } from "../lib/retoMensajes.js";

const COLOR_CATEGORIA = {
  Normal: "from-cyan-500 to-blue-500",
  Picante: "from-orange-500 to-red-500",
  Creativo: "from-emerald-400 to-teal-500",
  Grupo: "from-neon-purple to-neon-pink",
};

// La mitad de las veces, el reto viene acompañado de una canción sugerida.
const PROB_CANCION_ASIGNADA = 0.5;

function reproducirSonidoReto() {
  try {
    const Ctx = window.AudioContext || window.webkitAudioContext;
    const ctx = new Ctx();
    const ahora = ctx.currentTime;
    // "Stinger" corto: tres tonos ascendentes con glissando, más dramático
    // que el beep simple de "te toca cantar".
    [440, 554, 660].forEach((freq, i) => {
      const osc = ctx.createOscillator();
      const gain = ctx.createGain();
      osc.connect(gain);
      gain.connect(ctx.destination);
      const inicio = ahora + i * 0.12;
      osc.frequency.setValueAtTime(freq, inicio);
      osc.frequency.exponentialRampToValueAtTime(freq * 1.5, inicio + 0.15);
      gain.gain.setValueAtTime(0.18, inicio);
      gain.gain.exponentialRampToValueAtTime(0.001, inicio + 0.2);
      osc.start(inicio);
      osc.stop(inicio + 0.2);
    });
  } catch {
    /* Web Audio no disponible en este navegador */
  }
}

function Confeti() {
  const piezas = useMemo(
    () =>
      Array.from({ length: 40 }, (_, i) => ({
        id: i,
        left: Math.random() * 100,
        delay: Math.random() * 0.6,
        duracion: 1.4 + Math.random() * 1,
        color: ["#ff2fb0", "#a855f7", "#38f4ff", "#fad165", "#4ade80"][i % 5],
        rotar: Math.random() * 360,
      })),
    []
  );
  return (
    <div className="pointer-events-none absolute inset-0 overflow-hidden">
      {piezas.map((p) => (
        <span
          key={p.id}
          className="absolute top-0 w-2 h-3 rounded-sm animate-confettiCaer"
          style={{
            left: `${p.left}%`,
            backgroundColor: p.color,
            animationDelay: `${p.delay}s`,
            animationDuration: `${p.duracion}s`,
            transform: `rotate(${p.rotar}deg)`,
          }}
        />
      ))}
    </div>
  );
}

export default function RetoModal({ participantes = [], onClose }) {
  const [mensaje] = useState(mensajeAleatorio);
  // El "elegido" se sortea una sola vez al abrir el modal — "Otro reto"
  // cambia el desafío, no a quién le toca.
  const [elegido] = useState(() =>
    participantes.length ? participantes[Math.floor(Math.random() * participantes.length)] : null
  );
  const [etapa, setEtapa] = useState("hype"); // "hype" | "reto"
  const [reto, setReto] = useState(null);
  const [cancionAsignada, setCancionAsignada] = useState(null);
  const [pidiendo, setPidiendo] = useState(false);

  async function pedirReto() {
    setPidiendo(true);
    setCancionAsignada(Math.random() < PROB_CANCION_ASIGNADA ? elegirCancionAsignada() : null);
    try {
      const r = await api.retoAleatorio();
      setReto(r);
    } catch {
      setReto({ texto: "No se pudo cargar un reto — probá de nuevo en un rato.", dificultad: "", categoria: "Normal" });
    } finally {
      setPidiendo(false);
    }
  }

  useEffect(() => {
    reproducirSonidoReto();
    pedirReto();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  return (
    <div className="fixed inset-0 z-50 bg-black/85 backdrop-blur-sm flex items-center justify-center p-4">
      <Confeti />
      {etapa === "hype" ? (
        <div className="relative card p-8 max-w-md text-center animate-retoEntrada shadow-neon">
          {elegido && (
            <p className="text-neon-pinklight uppercase tracking-widest text-sm font-semibold mb-2">
              🎯 Le toca a {elegido}
            </p>
          )}
          <p className="font-display font-extrabold text-2xl leading-snug mb-6">{mensaje}</p>
          <button
            onClick={() => setEtapa("reto")}
            disabled={!reto || pidiendo}
            className="btn-primary text-lg !px-8 !py-3"
          >
            {pidiendo || !reto ? "Cargando…" : "🎤 ¡Acepto el reto!"}
          </button>
        </div>
      ) : (
        <div
          className={`relative card p-8 max-w-md text-center animate-retoEntrada shadow-neon bg-gradient-to-br !border-transparent ${
            COLOR_CATEGORIA[reto?.categoria] || COLOR_CATEGORIA.Normal
          }`}
        >
          {elegido && (
            <p className="uppercase tracking-widest text-sm font-semibold mb-2 !text-white/90">🎯 Le toca a {elegido}</p>
          )}
          <span className="chip !bg-black/20 !border-white/20 mb-4 inline-block">
            {reto?.categoria} · {reto?.dificultad}
          </span>
          <p className="font-display font-bold text-xl leading-snug mb-4">{reto?.texto}</p>
          {cancionAsignada && (
            <div className="bg-black/25 rounded-xl px-4 py-3 mb-6 text-sm">
              <p className="text-white/70 mb-0.5">{cancionAsignada.etiqueta}</p>
              <p className="font-display font-bold">
                🎵 {cancionAsignada.titulo} — {cancionAsignada.artista}
              </p>
            </div>
          )}
          <div className="flex gap-2 justify-center flex-wrap">
            <button onClick={pedirReto} disabled={pidiendo} className="btn-ghost">
              <IconDice /> {pidiendo ? "Girando…" : "Otro reto"}
            </button>
            <button onClick={onClose} className="btn-primary">
              ✅ Listo, a cantar
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
