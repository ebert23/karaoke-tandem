import React, { useEffect, useState } from "react";
import { useToast } from "../lib/ToastContext.jsx";
import { api } from "../lib/api.js";

const MEDALLAS = ["🥇", "🥈", "🥉"];

function TarjetaRanking({ entrada, posicion }) {
  return (
    <div className="card p-4 flex items-center gap-3">
      <span className="text-2xl w-8 text-center shrink-0">{MEDALLAS[posicion] ?? posicion + 1}</span>
      <div className="w-10 h-10 rounded-full bg-gradient-to-br from-neon-purple to-neon-pink flex items-center justify-center font-display font-bold shrink-0">
        {entrada.nombre[0]?.toUpperCase()}
      </div>
      <div className="flex-1 min-w-0">
        <p className="font-semibold truncate">{entrada.nombre}</p>
        <div className="flex flex-wrap gap-1 mt-1">
          {entrada.badges.map((b) => (
            <span key={b.codigo} className="chip !py-0.5 !text-[10px]" title={b.descripcion}>
              {b.icono} {b.nombre}
            </span>
          ))}
        </div>
      </div>
      <div className="text-right shrink-0">
        <p className="font-display font-extrabold text-lg text-neon-pinklight">{entrada.puntos}</p>
        <p className="text-[11px] text-white/40">{entrada.canciones_cantadas} canciones</p>
      </div>
    </div>
  );
}

export default function Ranking() {
  const { push } = useToast();
  const [tab, setTab] = useState("historico");
  const [ranking, setRanking] = useState([]);
  const [loading, setLoading] = useState(true);
  const [sesiones, setSesiones] = useState([]);
  const [idSesion, setIdSesion] = useState("");

  useEffect(() => {
    api.historialSesiones().then((data) => {
      setSesiones(data);
      const activaOUltima = data.find((s) => s.estado === "Activa") || data[0];
      if (activaOUltima) setIdSesion(activaOUltima.id_sesion);
    });
  }, []);

  useEffect(() => {
    async function cargar() {
      setLoading(true);
      try {
        if (tab === "historico") {
          setRanking(await api.rankingHistorico());
        } else if (idSesion) {
          setRanking(await api.rankingNoche(idSesion));
        } else {
          setRanking([]);
        }
      } catch (e) {
        push(e.message, "error");
      } finally {
        setLoading(false);
      }
    }
    cargar();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [tab, idSesion]);

  return (
    <div className="flex flex-col gap-5 max-w-lg mx-auto">
      <h2 className="title-glow text-2xl">Ranking</h2>

      <div className="flex gap-2">
        <button onClick={() => setTab("historico")} className={tab === "historico" ? "chip-active" : "chip"}>
          🏆 Histórico
        </button>
        <button onClick={() => setTab("noche")} className={tab === "noche" ? "chip-active" : "chip"}>
          🌙 De una noche
        </button>
      </div>

      {tab === "noche" && (
        <select className="input" value={idSesion} onChange={(e) => setIdSesion(e.target.value)}>
          {sesiones.length === 0 && <option value="">Sin sesiones aún</option>}
          {sesiones.map((s) => (
            <option key={s.id_sesion} value={s.id_sesion}>
              {s.fecha} · {s.participantes.join(", ")} {s.estado === "Activa" ? "(en curso)" : ""}
            </option>
          ))}
        </select>
      )}

      {loading ? (
        <p className="text-white/40 text-center py-10">Cargando…</p>
      ) : ranking.length === 0 ? (
        <p className="text-white/40 text-center py-10">Todavía no hay puntuaciones.</p>
      ) : (
        <div className="flex flex-col gap-2.5">
          {ranking.map((r, i) => (
            <TarjetaRanking key={r.id_usuario} entrada={r} posicion={i} />
          ))}
        </div>
      )}
    </div>
  );
}
