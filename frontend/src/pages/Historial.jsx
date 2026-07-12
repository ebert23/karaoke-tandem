import React, { useEffect, useState } from "react";
import { useToast } from "../lib/ToastContext.jsx";
import { api } from "../lib/api.js";
import { formatCantantes } from "../lib/format.js";

function SesionItem({ sesion }) {
  const [abierto, setAbierto] = useState(false);
  const [turnos, setTurnos] = useState(null);
  const { push } = useToast();

  async function toggle() {
    setAbierto((a) => !a);
    if (!turnos) {
      try {
        setTurnos(await api.detalleSesion(sesion.id_sesion));
      } catch (e) {
        push(e.message, "error");
      }
    }
  }

  const cantadas = turnos?.filter((t) => t.estado === "Cantada") ?? [];

  return (
    <div className="card overflow-hidden">
      <button onClick={toggle} className="w-full p-4 flex items-center justify-between text-left">
        <div>
          <p className="font-semibold">{sesion.fecha}</p>
          <p className="text-xs text-white/50">{sesion.participantes.join(", ")}</p>
        </div>
        <span
          className={`chip shrink-0 ${
            sesion.estado === "Activa" ? "!bg-emerald-500/15 !text-emerald-300 !border-emerald-500/30" : ""
          }`}
        >
          {sesion.estado}
        </span>
      </button>
      {abierto && (
        <div className="border-t border-white/10 p-4 flex flex-col gap-2">
          {!turnos ? (
            <p className="text-white/40 text-sm">Cargando…</p>
          ) : cantadas.length === 0 ? (
            <p className="text-white/40 text-sm">No se cantaron canciones en esta sesión.</p>
          ) : (
            cantadas.map((t) => (
              <div key={t.turno} className="flex items-center justify-between text-sm">
                <span className="truncate">
                  {t.cancion?.titulo} — <span className="text-white/40">{formatCantantes(t.cantada_por)}</span>
                </span>
                <span className="chip shrink-0">★ {t.puntuacion}</span>
              </div>
            ))
          )}
        </div>
      )}
    </div>
  );
}

export default function Historial() {
  const { push } = useToast();
  const [sesiones, setSesiones] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api
      .historialSesiones()
      .then(setSesiones)
      .catch((e) => push(e.message, "error"))
      .finally(() => setLoading(false));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  return (
    <div className="flex flex-col gap-4 max-w-lg mx-auto">
      <h2 className="title-glow text-2xl">Historial de sesiones</h2>
      {loading ? (
        <p className="text-white/40 text-center py-10">Cargando…</p>
      ) : sesiones.length === 0 ? (
        <p className="text-white/40 text-center py-10">Aún no hay sesiones registradas.</p>
      ) : (
        sesiones.map((s) => <SesionItem key={s.id_sesion} sesion={s} />)
      )}
    </div>
  );
}
