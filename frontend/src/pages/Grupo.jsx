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
  const [errorCarga, setErrorCarga] = useState(false);
  const [intentos, setIntentos] = useState(0);
  const [ocupado, setOcupado] = useState(""); // id del miembro con una acción en curso

  const esAdmin = grupo.admins?.includes(usuario.id) ?? false;
  const linkInvitacion = `${window.location.origin}${window.location.pathname}#/?codigo=${grupo.codigo}`;

  useEffect(() => {
    let cancelado = false;
    setErrorCarga(false);
    api
      .grupoActual(grupo.id)
      .then((d) => {
        if (!cancelado) setDetalle(d);
      })
      .catch((e) => {
        if (cancelado) return;
        if (intentos === 0) {
          // Primer intento fallido: puede ser un arranque en frío del
          // backend o un pico de la cuota de Sheets — reintentamos una vez
          // en silencio antes de pedirle al usuario que lo haga a mano.
          setTimeout(() => !cancelado && setIntentos((n) => n + 1), 1500);
        } else {
          push(e.message, "error");
          setErrorCarga(true);
        }
      });
    return () => {
      cancelado = true;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [grupo.id, intentos]);

  function aplicarDetalle(nuevoDetalle) {
    setDetalle(nuevoDetalle);
    // El grupo cacheado en localStorage (GroupContext) también trae `admins`;
    // si no lo actualizamos acá, el resto de la app (p.ej. permisos en
    // Semana.jsx) seguiría viendo la lista de admins vieja hasta recargar.
    setGrupo({ ...grupo, admins: nuevoDetalle.admins });
  }

  async function copiarLink() {
    try {
      await navigator.clipboard.writeText(linkInvitacion);
      push("Link copiado — pegalo donde quieras 📋", "success");
    } catch {
      push("No se pudo copiar. Compartí el código a mano: " + grupo.codigo, "error");
    }
  }

  // El link lleva directo a la sala (auto-join al abrirlo); el código queda
  // como respaldo por si a alguien no le abre el link.
  const textoInvitacion = `¡Únete a "${grupo.nombre}" en KaraokeTandem! 🎤\n${linkInvitacion}\n(o con el código ${grupo.codigo})`;

  async function compartir() {
    if (navigator.share) {
      try {
        await navigator.share({ title: "KaraokeTandem", text: textoInvitacion, url: linkInvitacion });
      } catch {
        /* usuario canceló el share */
      }
    } else {
      copiarLink();
    }
  }

  async function reclamarAdmin() {
    setOcupado("__reclamar__");
    try {
      const nuevoDetalle = await api.reclamarAdmin(grupo.id, usuario.id);
      aplicarDetalle(nuevoDetalle);
      push("¡Ahora sos admin del grupo! 👑", "success");
    } catch (e) {
      push(e.message, "error");
    } finally {
      setOcupado("");
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
        <p className="text-xs text-white/40 mb-3 -mt-2">
          Compartí el link y quien lo abra entra directo a la sala, sin escribir el código.
        </p>
        <div className="flex gap-2 justify-center flex-wrap">
          <button onClick={copiarLink} className="btn-ghost">
            <IconCopy /> Copiar link
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

      {detalle && detalle.admins.length === 0 && (
        <div className="card p-4 border-amber-400/30 bg-amber-400/5 flex items-center justify-between gap-3 flex-wrap">
          <p className="text-sm text-amber-200/90">
            <IconCrown className="inline mb-0.5" /> Este grupo todavía no tiene ningún admin.
          </p>
          <button onClick={reclamarAdmin} disabled={ocupado === "__reclamar__"} className="btn-primary !text-xs !py-1.5 shrink-0">
            {ocupado === "__reclamar__" ? "Un momento…" : "Ser el primer admin"}
          </button>
        </div>
      )}

      <div className="card p-4">
        <p className="label mb-3 flex items-center gap-1.5">
          <IconUsers /> Miembros ({detalle?.miembros?.length ?? "…"})
        </p>
        {!detalle ? (
          errorCarga ? (
            <div className="text-center py-4">
              <p className="text-white/40 text-sm mb-2">No se pudo cargar. Puede ser un pico de tráfico en la base de datos.</p>
              <button onClick={() => setIntentos((n) => n + 1)} className="btn-ghost !text-xs">
                Reintentar
              </button>
            </div>
          ) : (
            <p className="text-white/40 text-sm text-center py-4">Cargando…</p>
          )
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
