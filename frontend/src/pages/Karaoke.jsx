import React, { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { IconCheck, IconClock, IconPlus, IconSkip } from "../components/Icons.jsx";
import { useIdentity } from "../lib/IdentityContext.jsx";
import { useToast } from "../lib/ToastContext.jsx";
import { api } from "../lib/api.js";

const TIMER_INICIAL = 240; // 4 minutos

function CrearSesion({ onCreada }) {
  const { usuario } = useIdentity();
  const { push } = useToast();
  const [participantes, setParticipantes] = useState([usuario.nombre]);
  const [nombre, setNombre] = useState("");
  const [creando, setCreando] = useState(false);

  function agregar() {
    const n = nombre.trim();
    if (!n || participantes.some((p) => p.toLowerCase() === n.toLowerCase())) return;
    setParticipantes([...participantes, n]);
    setNombre("");
  }

  async function crear() {
    if (participantes.length === 0) return;
    setCreando(true);
    try {
      const s = await api.crearSesion(participantes);
      push("¡Sesión creada! A cantar 🎤", "success");
      onCreada(s);
    } catch (e) {
      push(e.message, "error");
    } finally {
      setCreando(false);
    }
  }

  return (
    <div className="card p-5 max-w-md mx-auto mt-6">
      <h2 className="title-glow text-xl mb-1">Nueva sesión de karaoke</h2>
      <p className="text-white/50 text-sm mb-4">Agrega a todos los participantes de esta noche (los demás se pueden unir después con "Unirme").</p>
      <div className="flex gap-2 mb-3">
        <input
          className="input"
          placeholder="Nombre del participante"
          value={nombre}
          onChange={(e) => setNombre(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && (e.preventDefault(), agregar())}
        />
        <button type="button" onClick={agregar} className="btn-ghost !px-3">
          <IconPlus />
        </button>
      </div>
      <div className="flex flex-wrap gap-2 mb-5 min-h-[2rem]">
        {participantes.map((p) => (
          <span key={p} className="chip-active flex items-center gap-1.5">
            {p}
            <button onClick={() => setParticipantes(participantes.filter((x) => x !== p))} className="opacity-70 hover:opacity-100">
              ×
            </button>
          </span>
        ))}
      </div>
      <button className="btn-primary w-full" onClick={crear} disabled={creando || participantes.length === 0}>
        {creando ? "Creando…" : "Comenzar karaoke 🎶"}
      </button>
    </div>
  );
}

function Puntuador({ onElegir, onCancelar }) {
  return (
    <div className="card p-4 mt-3">
      <p className="text-sm font-semibold mb-3 text-center">Nadie votó — elige una puntuación manual (1–10)</p>
      <div className="grid grid-cols-5 gap-2">
        {Array.from({ length: 10 }, (_, i) => i + 1).map((n) => (
          <button
            key={n}
            onClick={() => onElegir(n)}
            className="btn-ghost !py-3 font-display font-bold hover:!bg-gradient-to-br hover:from-neon-purple hover:to-neon-pink hover:!border-transparent"
          >
            {n}
          </button>
        ))}
      </div>
      <button onClick={onCancelar} className="text-xs text-white/40 mt-3 w-full text-center hover:text-white/70">
        Cancelar
      </button>
    </div>
  );
}

function Temporizador({ turnoKey }) {
  const [segundos, setSegundos] = useState(TIMER_INICIAL);
  const [corriendo, setCorriendo] = useState(true);

  useEffect(() => {
    setSegundos(TIMER_INICIAL);
    setCorriendo(true);
  }, [turnoKey]);

  useEffect(() => {
    if (!corriendo) return;
    const id = setInterval(() => setSegundos((s) => Math.max(0, s - 1)), 1000);
    return () => clearInterval(id);
  }, [corriendo]);

  const mm = String(Math.floor(segundos / 60)).padStart(2, "0");
  const ss = String(segundos % 60).padStart(2, "0");

  return (
    <div className="flex items-center justify-center gap-3 mb-4">
      <button onClick={() => setSegundos((s) => Math.max(0, s - 30))} className="btn-ghost !px-2.5 !py-1.5 !text-xs">
        −30s
      </button>
      <div
        className={`flex items-center gap-1.5 font-display font-extrabold text-2xl tabular-nums ${
          segundos === 0 ? "text-red-400 animate-pulseGlow" : "text-white"
        }`}
      >
        <IconClock /> {mm}:{ss}
      </div>
      <button onClick={() => setSegundos((s) => s + 30)} className="btn-ghost !px-2.5 !py-1.5 !text-xs">
        +30s
      </button>
      <button onClick={() => setCorriendo((c) => !c)} className="btn-ghost !px-2.5 !py-1.5 !text-xs">
        {corriendo ? "Pausar" : "Seguir"}
      </button>
    </div>
  );
}

function VotacionEnVivo({ sesion, pendiente, usuario, onListoParaMarcar }) {
  const { push } = useToast();
  const [votos, setVotos] = useState({ votos: [], promedio: null });
  const [votando, setVotando] = useState(false);

  const yaVoto = votos.votos.some((v) => v.id_usuario === usuario.id);

  useEffect(() => {
    let vivo = true;
    async function cargar() {
      try {
        const v = await api.votosTurno(sesion.id_sesion, pendiente.id_cancion);
        if (vivo) setVotos(v);
      } catch {
        /* silencioso: sigue con el estado anterior */
      }
    }
    cargar();
    const id = setInterval(cargar, 4000);
    return () => {
      vivo = false;
      clearInterval(id);
    };
  }, [sesion.id_sesion, pendiente.id_cancion]);

  useEffect(() => {
    onListoParaMarcar(votos.promedio !== null);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [votos.promedio]);

  async function votar(puntuacion) {
    setVotando(true);
    try {
      const v = await api.votarTurno(sesion.id_sesion, pendiente.id_cancion, usuario.id, puntuacion);
      setVotos(v);
      push("¡Voto registrado! 🌟", "success");
    } catch (e) {
      push(e.message, "error");
    } finally {
      setVotando(false);
    }
  }

  return (
    <div className="card p-4 mt-3">
      <div className="flex items-center justify-between mb-2">
        <p className="text-sm font-semibold">Votación en vivo</p>
        <p className="text-xs text-white/40">
          {votos.votos.length} voto{votos.votos.length === 1 ? "" : "s"}
          {votos.promedio !== null && <> · promedio {votos.promedio}</>}
        </p>
      </div>
      {yaVoto ? (
        <p className="text-sm text-emerald-300 text-center py-2">¡Ya votaste esta interpretación! ✓</p>
      ) : (
        <div className="grid grid-cols-5 gap-1.5">
          {Array.from({ length: 10 }, (_, i) => i + 1).map((n) => (
            <button
              key={n}
              onClick={() => votar(n)}
              disabled={votando}
              className="btn-ghost !py-2 !text-sm font-display font-bold hover:!bg-gradient-to-br hover:from-neon-purple hover:to-neon-pink hover:!border-transparent"
            >
              {n}
            </button>
          ))}
        </div>
      )}
    </div>
  );
}

export default function Karaoke() {
  const { usuario } = useIdentity();
  const { push } = useToast();
  const navigate = useNavigate();
  const [sesion, setSesion] = useState(undefined); // undefined = cargando, null = sin sesión
  const [turnos, setTurnos] = useState([]);
  const [canciones, setCanciones] = useState([]);
  const [pidiendo, setPidiendo] = useState(false);
  const [puntuando, setPuntuando] = useState(false);
  const [hayVotos, setHayVotos] = useState(false);
  const [mostrarCola, setMostrarCola] = useState(false);
  const [uniendose, setUniendose] = useState(false);

  async function cargarTodo() {
    try {
      const s = await api.sesionActiva();
      setSesion(s);
      if (s) {
        setTurnos(await api.detalleSesion(s.id_sesion));
        setCanciones(await api.canciones({ id_usuario: usuario.id }));
      }
    } catch (e) {
      push(e.message, "error");
      setSesion(null);
    }
  }

  useEffect(() => {
    cargarTodo();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const pendiente = turnos.find((t) => t.estado === "Pendiente");
  const cola = turnos.filter((t) => t.estado === "En cola");
  const resueltos = turnos.filter((t) => t.estado !== "En cola");
  const idsUsadas = new Set(turnos.map((t) => t.id_cancion));
  const disponiblesParaCola = canciones.filter((c) => !idsUsadas.has(c.id));

  async function unirme() {
    setUniendose(true);
    try {
      const s = await api.sesionUnirse(sesion.id_sesion, usuario.nombre);
      setSesion(s);
      push("¡Te uniste a la sesión! 🎉", "success");
    } catch (e) {
      push(e.message, "error");
    } finally {
      setUniendose(false);
    }
  }

  async function agregarACola(idCancion) {
    try {
      const t = await api.agregarACola(sesion.id_sesion, idCancion);
      setTurnos((prev) => [...prev, t]);
      push("Agregada a la cola 🎶", "success");
    } catch (e) {
      push(e.message, "error");
    }
  }

  async function siguiente() {
    setPidiendo(true);
    try {
      const t = await api.siguienteCancion(sesion.id_sesion);
      // Comparamos por id_cancion (no por turno): una canción en cola tiene
      // turno=0 como placeholder hasta que "siguiente" la promueve y le
      // asigna el turno real, así que filtrar por turno dejaría la fila
      // vieja de la cola duplicada en el estado local.
      setTurnos((prev) => [...prev.filter((x) => x.id_cancion !== t.id_cancion), t]);
    } catch (e) {
      push(e.message, "error");
    } finally {
      setPidiendo(false);
    }
  }

  async function marcarCantada(puntuacion) {
    try {
      const actualizado = await api.marcarCantada(sesion.id_sesion, pendiente.id_cancion, puntuacion);
      setTurnos((prev) => prev.map((t) => (t.turno === actualizado.turno ? actualizado : t)));
      setPuntuando(false);
      push("¡Puntuación registrada! 🌟", "success");
    } catch (e) {
      push(e.message, "error");
    }
  }

  async function saltar() {
    try {
      const actualizado = await api.saltarCancion(sesion.id_sesion, pendiente.id_cancion);
      setTurnos((prev) => prev.map((t) => (t.turno === actualizado.turno ? actualizado : t)));
    } catch (e) {
      push(e.message, "error");
    }
  }

  async function finalizar() {
    if (!confirm("¿Terminar la sesión de karaoke?")) return;
    try {
      await api.finalizarSesion(sesion.id_sesion);
      push("Sesión finalizada. ¡Buena noche! 🎉", "success");
      navigate("/ranking");
    } catch (e) {
      push(e.message, "error");
    }
  }

  if (sesion === undefined) return <p className="text-white/40 text-center py-10">Cargando…</p>;
  if (sesion === null) {
    return (
      <CrearSesion
        onCreada={async (s) => {
          setSesion(s);
          setTurnos([]);
          setCanciones(await api.canciones({ id_usuario: usuario.id }));
        }}
      />
    );
  }

  const yaSoyParticipante = sesion.participantes.some((p) => p.toLowerCase() === usuario.nombre.toLowerCase());

  return (
    <div className="flex flex-col gap-4 max-w-xl mx-auto">
      <div className="flex items-center justify-between">
        <h2 className="title-glow text-2xl">Karaoke en vivo</h2>
        <button onClick={finalizar} className="btn-danger !text-xs !py-1.5">
          Finalizar
        </button>
      </div>
      <div className="flex flex-wrap gap-1.5 items-center">
        {sesion.participantes.map((p) => (
          <span key={p} className="chip">
            {p}
          </span>
        ))}
        {!yaSoyParticipante && (
          <button onClick={unirme} className="chip-active" disabled={uniendose}>
            {uniendose ? "Uniendo…" : "+ Unirme"}
          </button>
        )}
      </div>

      {pendiente ? (
        <>
          <div className="card p-6 text-center">
            <p className="text-xs uppercase tracking-widest text-neon-pinklight font-semibold mb-2">
              Turno de {pendiente.cantada_por}
            </p>
            <h3 className="font-display font-extrabold text-2xl mb-1">{pendiente.cancion?.titulo}</h3>
            <p className="text-white/60 mb-3">{pendiente.cancion?.artista}</p>
            <Temporizador turnoKey={pendiente.turno} />
            {pendiente.cancion?.link_youtube && (
              <a href={pendiente.cancion.link_youtube} target="_blank" rel="noreferrer" className="btn-primary mb-4 inline-flex">
                ▶ Abrir en YouTube
              </a>
            )}
            {!puntuando ? (
              <div className="flex gap-2 justify-center mt-2">
                <button
                  onClick={() => (hayVotos ? marcarCantada(undefined) : setPuntuando(true))}
                  className="btn-primary flex-1"
                >
                  <IconCheck /> {hayVotos ? "Cerrar y marcar cantada" : "Cantada"}
                </button>
                <button onClick={saltar} className="btn-ghost flex-1">
                  <IconSkip /> Saltar
                </button>
              </div>
            ) : (
              <Puntuador onElegir={marcarCantada} onCancelar={() => setPuntuando(false)} />
            )}
          </div>
          <VotacionEnVivo sesion={sesion} pendiente={pendiente} usuario={usuario} onListoParaMarcar={setHayVotos} />
        </>
      ) : (
        <div className="card p-8 text-center">
          <p className="text-white/50 mb-4">
            {cola.length > 0 ? `Sigue "${cola[0].cancion?.titulo}" (primera en la cola)` : "Listo para el siguiente turno"}
          </p>
          <button onClick={siguiente} className="btn-primary text-lg !px-8 !py-3" disabled={pidiendo}>
            {pidiendo ? "Eligiendo…" : cola.length > 0 ? "▶ Siguiente de la cola" : "🎲 Siguiente canción"}
          </button>
        </div>
      )}

      <div className="card p-4">
        <div className="flex items-center justify-between mb-2">
          <p className="label !mb-0">Cola ({cola.length})</p>
          <button onClick={() => setMostrarCola((m) => !m)} className="btn-ghost !text-xs !py-1.5">
            <IconPlus /> {mostrarCola ? "Cerrar" : "Agregar canción"}
          </button>
        </div>
        {cola.length > 0 && (
          <div className="flex flex-col gap-1.5 mb-2">
            {cola.map((t, i) => (
              <div key={t.id_cancion} className="flex items-center gap-2 text-sm">
                <span className="text-white/30 text-xs w-4">{i + 1}.</span>
                <span className="truncate flex-1">
                  {t.cancion?.titulo} <span className="text-white/40">— {t.cancion?.artista}</span>
                </span>
              </div>
            ))}
          </div>
        )}
        {mostrarCola && (
          <div className="flex flex-col gap-1.5 max-h-56 overflow-y-auto border-t border-white/10 pt-2 mt-1">
            {disponiblesParaCola.length === 0 ? (
              <p className="text-white/40 text-sm text-center py-2">No quedan canciones disponibles.</p>
            ) : (
              disponiblesParaCola.map((c) => (
                <button
                  key={c.id}
                  onClick={() => agregarACola(c.id)}
                  className="flex items-center justify-between gap-2 text-sm text-left p-1.5 rounded-lg hover:bg-white/5"
                >
                  <span className="truncate">
                    {c.titulo} <span className="text-white/40">— {c.artista}</span>
                  </span>
                  <IconPlus className="shrink-0 text-white/40" />
                </button>
              ))
            )}
          </div>
        )}
      </div>

      {resueltos.length > 0 && (
        <div className="mt-2">
          <p className="label mb-2">Playlist de la noche</p>
          <div className="flex flex-col gap-2">
            {[...resueltos].reverse().map((t) => (
              <div key={`${t.turno}-${t.id_cancion}`} className="card p-3 flex items-center justify-between gap-3 text-sm">
                <div className="min-w-0">
                  <p className="font-medium truncate">
                    #{t.turno} {t.cancion?.titulo} <span className="text-white/40">— {t.cantada_por}</span>
                  </p>
                </div>
                <span
                  className={`chip shrink-0 ${
                    t.estado === "Cantada" ? "!bg-emerald-500/15 !text-emerald-300 !border-emerald-500/30" : t.estado === "Saltada" ? "!bg-white/5 !text-white/40" : ""
                  }`}
                >
                  {t.estado === "Cantada" ? `★ ${t.puntuacion}` : t.estado}
                </span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
