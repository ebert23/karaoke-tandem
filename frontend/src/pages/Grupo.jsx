import React, { useEffect, useState } from "react";
import { IconCopy, IconCrown, IconUsers, IconWhatsapp } from "../components/Icons.jsx";
import { useGroup } from "../lib/GroupContext.jsx";
import { useIdentity } from "../lib/IdentityContext.jsx";
import { useToast } from "../lib/ToastContext.jsx";
import { api } from "../lib/api.js";

export default function Grupo() {
  const { grupo, setGrupo, salirDelGrupo } = useGroup();
  const { usuario } = useIdentity();
  const { push } = useToast();
  const [detalle, setDetalle] = useState(null);
  const [ocupado, setOcupado] = useState(""); // id del miembro con una acción en curso

  const esAdmin = grupo.admins?.includes(usuario.id) ?? false;

  useEffect(() => {
    api
      .grupoActual(grupo.id)
      .then(setDetalle)
      .catch((e) => push(e.message, "error"));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [grupo.id]);

  function aplicarDetalle(nuevoDetalle) {
    setDetalle(nuevoDetalle);
    // El grupo cacheado en localStorage (GroupContext) también trae `admins`;
    // si no lo actualizamos acá, el resto de la app (p.ej. permisos en
    // Semana.jsx) seguiría viendo la lista de admins vieja hasta recargar.
    setGrupo({ ...grupo, admins: nuevoDetalle.admins });
  }

  async function copiarCodigo() {
    try {
      await navigator.clipboard.writeText(grupo.codigo);
      push("Código copiado 📋", "success");
    } catch {
      push("No se pudo copiar. Copialo a mano: " + grupo.codigo, "error");
    }
  }

  const textoInvitacion = `¡Únete a "${grupo.nombre}" en KaraokeTandem! Código: ${grupo.codigo}`;

  async function compartir() {
    if (navigator.share) {
      try {
        await navigator.share({ title: "KaraokeTandem", text: textoInvitacion });
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

  async function alternarAdmin(m) {
    const esAdminM = detalle.admins.includes(m.id);
    setOcupado(m.id);
    try {
      const nuevoDetalle = esAdminM
        ? await api.quitarAdmin(grupo.id, m.id, usuario.id)
        : await api.hacerAdmin(grupo.id, m.id, usuario.id);
      aplicarDetalle(nuevoDetalle);
      push(esAdminM ? `${m.nombre} ya no es admin` : `${m.nombre} ahora es admin 👑`, "success");
    } catch (e) {
      push(e.message, "error");
    } finally {
      setOcupado("");
    }
  }

  async function expulsar(m) {
    if (!confirm(`¿Expulsar a "${m.nombre}" del grupo? Perderá sus puntos y su historial en este grupo.`)) return;
    setOcupado(m.id);
    try {
      const nuevoDetalle = await api.expulsarMiembro(grupo.id, m.id, usuario.id);
      aplicarDetalle(nuevoDetalle);
      push(`${m.nombre} fue expulsado del grupo`, "success");
    } catch (e) {
      push(e.message, "error");
    } finally {
      setOcupado("");
    }
  }

  return (
    <div className="flex flex-col gap-5 max-w-md mx-auto">
      <h2 className="title-glow text-2xl">{grupo.nombre}</h2>

      <div className="card p-5 text-center">
        <p className="label mb-2">Código de invitación</p>
        <p className="font-display font-extrabold text-4xl tracking-[0.3em] mb-4">{grupo.codigo}</p>
        <div className="flex gap-2 justify-center flex-wrap">
          <button onClick={copiarCodigo} className="btn-ghost">
            <IconCopy /> Copiar
          </button>
          <a
            href={`https://wa.me/?text=${encodeURIComponent(textoInvitacion)}`}
            target="_blank"
            rel="noreferrer"
            className="btn-ghost !text-emerald-300 !border-emerald-500/30 hover:!border-emerald-400/60"
          >
            <IconWhatsapp /> WhatsApp
          </a>
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
            {detalle.miembros.map((m) => {
              const esAdminM = detalle.admins.includes(m.id);
              const esYo = m.id === usuario.id;
              return (
                <div key={m.id} className="flex items-center gap-3">
                  <div className="w-8 h-8 rounded-full bg-gradient-to-br from-neon-purple to-neon-pink flex items-center justify-center font-display font-bold text-xs shrink-0">
                    {m.nombre[0]?.toUpperCase()}
                  </div>
                  <p className="text-sm font-medium flex-1 truncate flex items-center gap-1.5">
                    {m.nombre}
                    {esAdminM && (
                      <span className="chip !py-0.5 !px-1.5 !text-[10px] !text-amber-300 !border-amber-400/30 flex items-center gap-1">
                        <IconCrown /> admin
                      </span>
                    )}
                  </p>
                  <p className="text-xs text-white/40 shrink-0">{m.puntos_totales} pts</p>
                  {esAdmin && !esYo && (
                    <div className="flex items-center gap-1 shrink-0">
                      <button
                        onClick={() => alternarAdmin(m)}
                        disabled={ocupado === m.id}
                        className="btn-ghost !px-2 !py-1 !text-[11px]"
                      >
                        {esAdminM ? "Quitar admin" : "Hacer admin"}
                      </button>
                      {!esAdminM && (
                        <button
                          onClick={() => expulsar(m)}
                          disabled={ocupado === m.id}
                          className="btn-ghost !px-2 !py-1 !text-[11px] !text-red-300/70 hover:!text-red-300"
                        >
                          Expulsar
                        </button>
                      )}
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        )}
      </div>

      <button onClick={salir} className="btn-danger w-full">
        Salir del grupo en este dispositivo
      </button>
    </div>
  );
}
