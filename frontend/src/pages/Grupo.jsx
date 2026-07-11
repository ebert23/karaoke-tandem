import React, { useEffect, useState } from "react";
import { IconCopy, IconUsers } from "../components/Icons.jsx";
import { useGroup } from "../lib/GroupContext.jsx";
import { useToast } from "../lib/ToastContext.jsx";
import { api } from "../lib/api.js";

export default function Grupo() {
  const { grupo, salirDelGrupo } = useGroup();
  const { push } = useToast();
  const [detalle, setDetalle] = useState(null);

  useEffect(() => {
    api
      .grupoActual(grupo.id)
      .then(setDetalle)
      .catch((e) => push(e.message, "error"));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [grupo.id]);

  async function copiarCodigo() {
    try {
      await navigator.clipboard.writeText(grupo.codigo);
      push("Código copiado 📋", "success");
    } catch {
      push("No se pudo copiar. Copialo a mano: " + grupo.codigo, "error");
    }
  }

  async function compartir() {
    const texto = `¡Únete a "${grupo.nombre}" en KaraokeTandem! Código: ${grupo.codigo}`;
    if (navigator.share) {
      try {
        await navigator.share({ title: "KaraokeTandem", text: texto });
      } catch {
        /* usuario canceló el share */
      }
    } else {
      copiarCodigo();
    }
  }

  function salir() {
    if (!confirm(`¿Salir de "${grupo.nombre}" en este dispositivo?`)) return;
    salirDelGrupo();
  }

  return (
    <div className="flex flex-col gap-5 max-w-md mx-auto">
      <h2 className="title-glow text-2xl">{grupo.nombre}</h2>

      <div className="card p-5 text-center">
        <p className="label mb-2">Código de invitación</p>
        <p className="font-display font-extrabold text-4xl tracking-[0.3em] mb-4">{grupo.codigo}</p>
        <div className="flex gap-2 justify-center">
          <button onClick={copiarCodigo} className="btn-ghost">
            <IconCopy /> Copiar
          </button>
          <button onClick={compartir} className="btn-primary">
            Compartir
          </button>
        </div>
      </div>

      <div className="card p-4">
        <p className="label mb-3 flex items-center gap-1.5">
          <IconUsers /> Miembros ({detalle?.miembros?.length ?? "…"})
        </p>
        {!detalle ? (
          <p className="text-white/40 text-sm text-center py-4">Cargando…</p>
        ) : detalle.miembros.length === 0 ? (
          <p className="text-white/40 text-sm text-center py-4">Todavía no hay miembros.</p>
        ) : (
          <div className="flex flex-col gap-2">
            {detalle.miembros.map((m) => (
              <div key={m.id} className="flex items-center gap-3">
                <div className="w-8 h-8 rounded-full bg-gradient-to-br from-neon-purple to-neon-pink flex items-center justify-center font-display font-bold text-xs shrink-0">
                  {m.nombre[0]?.toUpperCase()}
                </div>
                <p className="text-sm font-medium flex-1 truncate">{m.nombre}</p>
                <p className="text-xs text-white/40">{m.puntos_totales} pts</p>
              </div>
            ))}
          </div>
        )}
      </div>

      <button onClick={salir} className="btn-danger w-full">
        Salir del grupo en este dispositivo
      </button>
    </div>
  );
}
