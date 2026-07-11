import React, { useEffect, useState } from "react";
import { useIdentity } from "../lib/IdentityContext.jsx";
import { useToast } from "../lib/ToastContext.jsx";
import { api } from "../lib/api.js";

function Stat({ label, value }) {
  return (
    <div className="card p-4 text-center">
      <p className="font-display font-extrabold text-2xl text-neon-pinklight">{value}</p>
      <p className="text-xs text-white/50 mt-1">{label}</p>
    </div>
  );
}

export default function Estadisticas() {
  const { usuario } = useIdentity();
  const { push } = useToast();
  const [stats, setStats] = useState(null);

  useEffect(() => {
    api
      .estadisticas(usuario.id)
      .then(setStats)
      .catch((e) => push(e.message, "error"));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  if (!stats) return <p className="text-white/40 text-center py-10">Cargando estadísticas…</p>;

  const maxGenero = Math.max(1, ...Object.values(stats.generos));

  return (
    <div className="flex flex-col gap-6 max-w-lg mx-auto">
      <h2 className="title-glow text-2xl">Tus estadísticas</h2>

      <div className="grid grid-cols-3 gap-3">
        <Stat label="Canciones cantadas" value={stats.canciones_cantadas} />
        <Stat label="Puntuación promedio" value={stats.puntuacion_promedio || "—"} />
        <Stat label="Género favorito" value={stats.genero_favorito || "—"} />
      </div>

      {Object.keys(stats.generos).length > 0 && (
        <div className="card p-4">
          <p className="label mb-3">Géneros cantados</p>
          <div className="flex flex-col gap-2.5">
            {Object.entries(stats.generos)
              .sort((a, b) => b[1] - a[1])
              .map(([genero, count]) => (
                <div key={genero} className="flex items-center gap-3">
                  <span className="text-xs w-20 shrink-0 truncate text-white/60">{genero}</span>
                  <div className="flex-1 h-2.5 rounded-full bg-white/5 overflow-hidden">
                    <div
                      className="h-full bg-gradient-to-r from-neon-purple to-neon-pink rounded-full"
                      style={{ width: `${(count / maxGenero) * 100}%` }}
                    />
                  </div>
                  <span className="text-xs w-5 text-right text-white/40">{count}</span>
                </div>
              ))}
          </div>
        </div>
      )}

      {stats.canciones_top.length > 0 && (
        <div className="card p-4">
          <p className="label mb-3">Tus mejores presentaciones</p>
          <div className="flex flex-col gap-2">
            {stats.canciones_top.map((c, i) => (
              <div key={i} className="flex items-center justify-between text-sm py-1.5 border-b border-white/5 last:border-0">
                <div className="min-w-0">
                  <p className="truncate font-medium">{c.titulo}</p>
                  <p className="text-white/40 text-xs truncate">{c.artista}</p>
                </div>
                <span className="chip shrink-0">★ {c.puntuacion ?? "—"}</span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
