import React, { useEffect, useRef, useState } from "react";
import QRCode from "qrcode";
import { api } from "../lib/api.js";
import { useGroup } from "../lib/GroupContext.jsx";
import { useIdentity } from "../lib/IdentityContext.jsx";
import { useToast } from "../lib/ToastContext.jsx";

export function linkMesa(codigo) {
  return `${window.location.origin}${window.location.pathname}#/mesa/${codigo}`;
}

// Igual que el QR de invitación de TV.jsx: se genera en el navegador, sin
// pegarle a ningún servicio externo.
function QrMesa({ codigo, size = 150 }) {
  const [dataUrl, setDataUrl] = useState("");
  useEffect(() => {
    let vivo = true;
    QRCode.toDataURL(linkMesa(codigo), { width: size * 2, margin: 1, color: { dark: "#0a0a12", light: "#ffffff" } })
      .then((url) => vivo && setDataUrl(url))
      .catch(() => {});
    return () => {
      vivo = false;
    };
  }, [codigo, size]);
  if (!dataUrl) return null;
  return <img src={dataUrl} alt={`QR de la mesa ${codigo}`} style={{ width: size, height: size }} className="rounded-lg" />;
}

export default function Local() {
  const { grupo, setGrupo } = useGroup();
  const { usuario } = useIdentity();
  const { push } = useToast();

  const [mesas, setMesas] = useState([]);
  const [sesion, setSesion] = useState(undefined); // undefined = cargando, null = noche cerrada
  const [codigoDj, setCodigoDj] = useState("");
  const [nueva, setNueva] = useState({ numero: "", tamano: 2 });
  const [ocupado, setOcupado] = useState(false);
  const [verQrs, setVerQrs] = useState(false);
  const areaImpresion = useRef(null);

  const esSalon = grupo?.modo === "salon";
  const esAdmin = usuario && grupo?.admins?.includes(usuario.id);
  const nocheAbierta = !!sesion;

  async function cargar() {
    try {
      const [m, s] = await Promise.all([api.mesas(), api.sesionActiva()]);
      setMesas(m);
      setSesion(s);
    } catch (e) {
      push(e.message, "error");
    }
  }

  useEffect(() => {
    if (esSalon) cargar();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [esSalon]);

  // Sin una sesión activa las mesas no tienen dónde encolar, así que abrirlas
  // fallaba con un 400 que el dueño no tenía forma de anticipar. Ahora la
  // noche se abre desde acá, que es donde está mirando.
  async function abrirNoche() {
    setOcupado(true);
    try {
      await api.crearSesion([grupo.nombre || "Salón"]);
      await cargar();
      push("Noche abierta. Ya podés abrir mesas.", "success");
    } catch (e) {
      push(e.message, "error");
    } finally {
      setOcupado(false);
    }
  }

  async function cerrarNoche() {
    setOcupado(true);
    try {
      await api.cerrarTodasLasMesas();
      await api.finalizarSesion(sesion.id_sesion);
      await cargar();
      push("Noche cerrada y mesas liberadas.", "success");
    } catch (e) {
      push(e.message, "error");
    } finally {
      setOcupado(false);
    }
  }

  async function convertir() {
    setOcupado(true);
    try {
      const g = await api.convertirASalon(grupo.id, usuario.id);
      setCodigoDj(g.codigo_dj);
      setGrupo({ ...grupo, modo: "salon" });
      push("Modo salón activado", "success");
    } catch (e) {
      push(e.message, "error");
    } finally {
      setOcupado(false);
    }
  }

  async function verCodigoDj() {
    try {
      const g = await api.convertirASalon(grupo.id, usuario.id);
      setCodigoDj(g.codigo_dj);
    } catch (e) {
      push(e.message, "error");
    }
  }

  async function regenerar() {
    try {
      const g = await api.regenerarCodigoDj(grupo.id, usuario.id);
      setCodigoDj(g.codigo_dj);
      push("Código nuevo. El anterior ya no sirve.", "success");
    } catch (e) {
      push(e.message, "error");
    }
  }

  async function crearMesa(e) {
    e.preventDefault();
    setOcupado(true);
    try {
      await api.crearMesa(nueva.numero.trim(), Number(nueva.tamano));
      setNueva({ numero: "", tamano: 2 });
      await cargar();
    } catch (err) {
      push(err.message, "error");
    } finally {
      setOcupado(false);
    }
  }

  async function alternar(mesa) {
    setOcupado(true);
    try {
      if (mesa.estado === "Abierta") {
        const r = await api.cerrarMesa(mesa.id);
        if (r.pedidos_cancelados > 0) {
          push(`Mesa ${mesa.numero} cerrada. Se cancelaron ${r.pedidos_cancelados} pedidos.`, "success");
        }
      } else {
        await api.abrirMesa(mesa.id, mesa.tamano);
      }
      await cargar();
    } catch (e) {
      push(e.message, "error");
    } finally {
      setOcupado(false);
    }
  }

  async function eliminar(mesa) {
    try {
      await api.eliminarMesa(mesa.id, usuario.id);
      await cargar();
    } catch (e) {
      push(e.message, "error");
    }
  }

  if (!esAdmin) {
    return (
      <div className="p-6 text-center text-white/50">
        Solo un admin del grupo puede administrar el local.
      </div>
    );
  }

  if (!esSalon) {
    return (
      <div className="max-w-lg mx-auto p-4 space-y-4">
        <h1 className="title-glow text-2xl">Modo salón</h1>
        <div className="card p-5 space-y-3">
          <p className="text-white/70 text-sm leading-relaxed">
            El modo salón convierte esta sala en un <strong>local de karaoke</strong>: cada mesa tiene
            su QR, los clientes encolan desde el celular, y el DJ recibe la lista en orden en su
            propia pantalla.
          </p>
          <p className="text-white/50 text-sm leading-relaxed">
            En este modo la app <strong>no reproduce la música</strong> — el DJ pone las canciones en
            su equipo. Las canciones que cargues acá son el catálogo que ven los clientes.
          </p>
          <button onClick={convertir} disabled={ocupado} className="btn-primary w-full">
            Activar modo salón
          </button>
        </div>
      </div>
    );
  }

  const abiertas = mesas.filter((m) => m.estado === "Abierta").length;

  return (
    <div className="max-w-2xl mx-auto p-4 space-y-5">
      <header className="flex items-end justify-between gap-3">
        <div>
          <h1 className="title-glow text-2xl leading-none">{grupo.nombre}</h1>
          <p className="text-white/40 text-xs mt-1">
            {mesas.length} mesas · {abiertas} abiertas
          </p>
        </div>
        <button onClick={() => setVerQrs((v) => !v)} className="btn-ghost !text-xs">
          {verQrs ? "Ocultar QRs" : "Ver QRs"}
        </button>
      </header>

      {/* --- Estado de la noche --- */}
      {sesion === undefined ? null : nocheAbierta ? (
        <section className="card p-4 flex items-center justify-between gap-3 border-emerald-500/30 bg-emerald-500/5">
          <div>
            <p className="font-display font-semibold text-sm text-emerald-300">Noche abierta</p>
            <p className="text-white/40 text-xs">Las mesas ya pueden pedir canciones.</p>
          </div>
          <button onClick={cerrarNoche} disabled={ocupado} className="btn-danger !text-xs shrink-0">
            Cerrar la noche
          </button>
        </section>
      ) : (
        <section className="card p-4 border-amber-400/30 bg-amber-400/5 space-y-2">
          <p className="font-display font-semibold text-sm text-amber-200">No hay una noche abierta</p>
          <p className="text-white/50 text-xs">
            Abrila para que las mesas puedan encolar canciones y el DJ vea la rotación. Al cerrarla
            se liberan todas las mesas.
          </p>
          <button onClick={abrirNoche} disabled={ocupado} className="btn-primary w-full">
            ▶ Abrir la noche
          </button>
        </section>
      )}

      {/* --- Acceso del DJ --- */}
      <section className="card p-4 space-y-2">
        <h2 className="label !mb-0">Acceso del DJ</h2>
        {codigoDj ? (
          <>
            <code className="block bg-ink-800 rounded-lg p-2.5 text-xs break-all select-all">{codigoDj}</code>
            <p className="text-white/40 text-xs">
              El DJ entra en <strong>/dj</strong> y pega este código. Compartilo en privado: quien lo
              tenga maneja la noche.
            </p>
            <div className="flex gap-2">
              <button
                onClick={() => navigator.clipboard?.writeText(codigoDj).then(() => push("Copiado", "success"))}
                className="btn-ghost !text-xs"
              >
                Copiar
              </button>
              <button onClick={regenerar} className="btn-danger !text-xs">
                Regenerar
              </button>
            </div>
          </>
        ) : (
          <button onClick={verCodigoDj} className="btn-ghost !text-xs">
            Mostrar código del DJ
          </button>
        )}
      </section>

      {/* --- Alta de mesa --- */}
      <form onSubmit={crearMesa} className="card p-4 flex gap-2 items-end">
        <div className="flex-1">
          <label className="label">Mesa</label>
          <input
            value={nueva.numero}
            onChange={(e) => setNueva((n) => ({ ...n, numero: e.target.value }))}
            placeholder="12, Barra 3, VIP…"
            className="input"
            required
          />
        </div>
        <div className="w-24">
          <label className="label">Personas</label>
          <input
            type="number"
            min="1"
            max="30"
            value={nueva.tamano}
            onChange={(e) => setNueva((n) => ({ ...n, tamano: e.target.value }))}
            className="input"
          />
        </div>
        <button disabled={ocupado} className="btn-primary">
          Agregar
        </button>
      </form>

      {/* --- Mesas --- */}
      <ul className="space-y-2" ref={areaImpresion}>
        {mesas.map((m) => (
          <li key={m.id} className="card p-3">
            <div className="flex items-center gap-3">
              <div
                className={`w-12 h-12 shrink-0 rounded-xl grid place-items-center font-display font-extrabold ${
                  m.estado === "Abierta"
                    ? "bg-gradient-to-br from-neon-purple to-neon-pink"
                    : "bg-white/5 text-white/40"
                }`}
              >
                {m.numero}
              </div>
              <div className="min-w-0 flex-1">
                <p className="font-semibold">
                  {m.estado === "Abierta" ? "Abierta" : "Cerrada"}
                  <span className="text-white/40 font-normal text-sm">
                    {" "}· {m.tamano} pers. · {m.cupo_por_ronda} por vuelta
                  </span>
                </p>
                <code className="text-white/35 text-xs">{m.codigo}</code>
              </div>
              <button
                onClick={() => alternar(m)}
                // Sin noche abierta, "Abrir" solo puede terminar en error:
                // mejor que se vea deshabilitado y con el motivo a la vista.
                disabled={ocupado || (m.estado !== "Abierta" && !nocheAbierta)}
                title={m.estado !== "Abierta" && !nocheAbierta ? "Primero abrí la noche" : ""}
                className="btn-ghost !text-xs shrink-0"
              >
                {m.estado === "Abierta" ? "Cerrar" : "Abrir"}
              </button>
              {m.estado !== "Abierta" && (
                <button onClick={() => eliminar(m)} className="btn-danger !px-2 !py-1 !text-xs shrink-0">
                  ✕
                </button>
              )}
            </div>
            {verQrs && (
              <div className="mt-3 pt-3 border-t border-white/10 flex items-center gap-4">
                <QrMesa codigo={m.codigo} />
                <div className="min-w-0">
                  <p className="font-display font-extrabold text-3xl">Mesa {m.numero}</p>
                  <p className="text-white/50 text-sm mt-1">Escaneá para pedir tus canciones</p>
                  <p className="text-white/30 text-xs mt-2 break-all">{linkMesa(m.codigo)}</p>
                </div>
              </div>
            )}
          </li>
        ))}
      </ul>

      {mesas.length === 0 && (
        <p className="text-white/40 text-sm text-center py-6">
          Todavía no hay mesas. Agregá la primera arriba.
        </p>
      )}
    </div>
  );
}
