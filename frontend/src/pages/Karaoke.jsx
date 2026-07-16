import React, { useEffect, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import { IconBell, IconCheck, IconClock, IconDice, IconPlus, IconSkip, IconTrash, IconUsers } from "../components/Icons.jsx";
import RetoModal from "../components/RetoModal.jsx";
import YouTubePlayer from "../components/YouTubePlayer.jsx";
import { useGroup } from "../lib/GroupContext.jsx";
import { useIdentity } from "../lib/IdentityContext.jsx";
import { useToast } from "../lib/ToastContext.jsx";
import { api } from "../lib/api.js";
import { formatCantantes } from "../lib/format.js";
import { POLL_MS } from "../lib/constants.js";

const TIMER_INICIAL = 240; // 4 minutos
const NOTIF_STORAGE_KEY = "kt_notif_enabled";

function cantantesDeTurno(t) {
  return (t.cantada_por || "")
    .split(",")
    .map((n) => n.trim().toLowerCase())
    .filter(Boolean);
}

// Cada cuántas canciones cantadas toca un reto automático: 3 a 5, al azar
// cada vez, para que no se vuelva predecible.
function nuevoUmbralReto() {
  return 3 + Math.floor(Math.random() * 3);
}

function reproducirBeep() {
  try {
    const Ctx = window.AudioContext || window.webkitAudioContext;
    const ctx = new Ctx();
    const osc = ctx.createOscillator();
    const gain = ctx.createGain();
    osc.connect(gain);
    gain.connect(ctx.destination);
    osc.frequency.value = 880;
    gain.gain.setValueAtTime(0.15, ctx.currentTime);
    gain.gain.exponentialRampToValueAtTime(0.001, ctx.currentTime + 0.5);
    osc.start();
    osc.stop(ctx.currentTime + 0.5);
  } catch {
    /* Web Audio no disponible en este navegador */
  }
}

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
      <p className="text-white/50 text-sm mb-4">Agrega a quienes ya sepas que van a cantar hoy — cualquiera del grupo se suma solo en cuanto abre esta pestaña.</p>
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
    const id = setInterval(cargar, 6000);
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
  const { grupo } = useGroup();
  const { push } = useToast();
  const navigate = useNavigate();
  const [sesion, setSesion] = useState(undefined); // undefined = cargando, null = sin sesión
  const [turnos, setTurnos] = useState([]);
  const [canciones, setCanciones] = useState([]);
  const [pidiendo, setPidiendo] = useState(false);
  const [puntuando, setPuntuando] = useState(false);
  const [hayVotos, setHayVotos] = useState(false);
  const [mostrarCola, setMostrarCola] = useState(false);
  const [cancionExpandida, setCancionExpandida] = useState(null);
  const [cantantesElegidos, setCantantesElegidos] = useState([]);
  const [notifActivas, setNotifActivas] = useState(() => localStorage.getItem(NOTIF_STORAGE_KEY) === "1");
  const [modo, setModo] = useState("aleatorio"); // "aleatorio" | "cola" — se carga por sesión al abrirla
  const [moviendoCola, setMoviendoCola] = useState("");
  const [mostrarReto, setMostrarReto] = useState(false);
  const [cancionesDesdeReto, setCancionesDesdeReto] = useState(0);
  const [proximoRetoEn, setProximoRetoEn] = useState(() => nuevoUmbralReto());
  const ultimoTurnoNotificado = useRef(null);
  const esAdmin = grupo.admins?.includes(usuario.id) ?? false;

  // Si alguien abrió la puntuación manual (porque todavía nadie había
  // votado) y justo después entra un voto en vivo, hay que salir de ese
  // modo: si no, quedaba mostrando "Nadie votó" con los botones 1-10 a la
  // vez que la tarjeta de votación en vivo ya mostraba un voto real — y el
  // valor manual ni se iba a usar (el backend siempre prioriza el promedio
  // en vivo sobre la puntuación manual si hay al menos un voto).
  useEffect(() => {
    if (hayVotos) setPuntuando(false);
  }, [hayVotos]);

  async function cargarTodo() {
    try {
      let s = await api.sesionActiva();
      // Cualquiera del grupo que abra esta pestaña con una sesión activa se
      // suma solo — evita que alguien agregue canciones o vote sin figurar
      // como participante (antes había que apretar "Unirme" a mano).
      if (s && !s.participantes.some((p) => p.toLowerCase() === usuario.nombre.toLowerCase())) {
        try {
          s = await api.sesionUnirse(s.id_sesion, usuario.nombre);
        } catch {
          /* si falla el auto-join seguimos mostrando la sesión igual */
        }
      }
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

  useEffect(() => {
    if (!sesion) return;
    setModo(localStorage.getItem(`kt_modo_sesion_${sesion.id_sesion}`) === "cola" ? "cola" : "aleatorio");
  }, [sesion?.id_sesion]);

  function cambiarModo(nuevoModo) {
    setModo(nuevoModo);
    if (sesion) localStorage.setItem(`kt_modo_sesion_${sesion.id_sesion}`, nuevoModo);
  }

  // Sondeo corto mientras la sesión está activa: mantiene la cola/turno al
  // día entre participantes y detecta cuándo le toca cantar al usuario.
  useEffect(() => {
    if (!sesion || sesion.estado !== "Activa") return;
    const id = setInterval(async () => {
      try {
        const nuevosTurnos = await api.detalleSesion(sesion.id_sesion);
        setTurnos(nuevosTurnos);
        const miTurno = nuevosTurnos.find(
          (t) => t.estado === "Pendiente" && cantantesDeTurno(t).includes(usuario.nombre.toLowerCase())
        );
        if (notifActivas && miTurno && ultimoTurnoNotificado.current !== miTurno.turno) {
          ultimoTurnoNotificado.current = miTurno.turno;
          reproducirBeep();
          push(`¡Te toca cantar "${miTurno.cancion?.titulo}"! 🎤`, "success");
          if ("Notification" in window && Notification.permission === "granted") {
            new Notification("¡Te toca cantar! 🎤", { body: miTurno.cancion?.titulo || "" });
          }
        }
      } catch {
        /* sondeo silencioso: no interrumpe la sesión por un fallo puntual */
      }
    }, POLL_MS);
    return () => clearInterval(id);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [sesion?.id_sesion, sesion?.estado, notifActivas]);

  async function alternarNotificaciones() {
    if (!notifActivas) {
      if ("Notification" in window && Notification.permission !== "granted") {
        const permiso = await Notification.requestPermission();
        if (permiso !== "granted") {
          push("No se pudo activar: permiso denegado por el navegador", "error");
          return;
        }
      }
      localStorage.setItem(NOTIF_STORAGE_KEY, "1");
      setNotifActivas(true);
      push("Notificaciones activadas 🔔", "success");
    } else {
      localStorage.setItem(NOTIF_STORAGE_KEY, "0");
      setNotifActivas(false);
    }
  }

  const pendiente = turnos.find((t) => t.estado === "Pendiente");
  const cola = turnos.filter((t) => t.estado === "En cola");
  const resueltos = turnos.filter((t) => t.estado !== "En cola");
  const idsUsadas = new Set(turnos.map((t) => t.id_cancion));
  const disponiblesParaCola = canciones.filter((c) => !idsUsadas.has(c.id));

  async function agregarACola(idCancion, cantantes = []) {
    try {
      const t = await api.agregarACola(sesion.id_sesion, idCancion, cantantes);
      setTurnos((prev) => [...prev, t]);
      push(cantantes.length >= 2 ? "¡Dueto agregado a la cola! 🎤🎤" : "Agregada a la cola 🎶", "success");
    } catch (e) {
      push(e.message, "error");
    } finally {
      setCancionExpandida(null);
      setCantantesElegidos([]);
    }
  }

  async function moverEnCola(idCancion, direccion) {
    setMoviendoCola(idCancion);
    try {
      const nuevaCola = await api.moverEnCola(sesion.id_sesion, idCancion, usuario.id, direccion);
      setTurnos((prev) => [...prev.filter((t) => t.estado !== "En cola"), ...nuevaCola]);
    } catch (e) {
      push(e.message, "error");
    } finally {
      setMoviendoCola("");
    }
  }

  async function quitarDeCola(idCancion) {
    try {
      await api.quitarDeCola(sesion.id_sesion, idCancion, usuario.id);
      setTurnos((prev) => prev.filter((t) => t.id_cancion !== idCancion));
      push("Sacada de la cola", "success");
    } catch (e) {
      push(e.message, "error");
    }
  }

  function abrirSelectorCantantes(idCancion) {
    setCancionExpandida((actual) => (actual === idCancion ? null : idCancion));
    setCantantesElegidos([]);
  }

  function toggleCantante(nombre) {
    setCantantesElegidos((prev) => (prev.includes(nombre) ? prev.filter((n) => n !== nombre) : [...prev, nombre]));
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

      const cancionesNuevas = cancionesDesdeReto + 1;
      if (cancionesNuevas >= proximoRetoEn) {
        setCancionesDesdeReto(0);
        setProximoRetoEn(nuevoUmbralReto());
        setMostrarReto(true);
      } else {
        setCancionesDesdeReto(cancionesNuevas);
      }
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

  return (
    <>
      {mostrarReto && <RetoModal participantes={sesion.participantes} onClose={() => setMostrarReto(false)} />}
      <div className="flex flex-col gap-4 max-w-xl mx-auto">
      <div className="flex items-center justify-between">
        <h2 className="title-glow text-2xl">Karaoke en vivo</h2>
        <div className="flex items-center gap-2">
          <a href="#/tv" target="_blank" rel="noreferrer" className="btn-ghost !text-xs !py-1.5">
            📺 Modo TV
          </a>
          <button onClick={() => setMostrarReto(true)} className="btn-ghost !text-xs !py-1.5" title="Sacar un reto ahora">
            <IconDice /> Reto
          </button>
          <button
            onClick={alternarNotificaciones}
            className={`btn-ghost !text-xs !py-1.5 ${notifActivas ? "!text-neon-pinklight !border-neon-pinklight/40" : ""}`}
            title={notifActivas ? "Notificaciones activadas" : "Avisarme cuando me toque cantar"}
          >
            <IconBell /> {notifActivas ? "Notif. ON" : "Notif."}
          </button>
          <button onClick={finalizar} className="btn-danger !text-xs !py-1.5">
            Finalizar
          </button>
        </div>
      </div>
      <div className="card p-3 flex items-center gap-2 flex-wrap">
        <span className="text-xs text-white/40 flex items-center gap-1 shrink-0">
          <IconUsers /> {sesion.participantes.length} participando
        </span>
        <span className="w-px h-4 bg-white/10 shrink-0" />
        {sesion.participantes.map((p) => (
          <span key={p} className="flex items-center gap-1.5 pl-1 pr-2.5 py-1 rounded-full bg-white/5 border border-white/10">
            <span className="w-5 h-5 rounded-full bg-gradient-to-br from-neon-purple to-neon-pink flex items-center justify-center font-display font-bold text-[10px] shrink-0">
              {p[0]?.toUpperCase()}
            </span>
            <span className="text-xs font-medium">{p}</span>
          </span>
        ))}
      </div>

      {pendiente ? (
        <>
          <div className="card p-6 text-center">
            <p className="text-xs uppercase tracking-widest text-neon-pinklight font-semibold mb-2">
              Turno de {formatCantantes(pendiente.cantada_por)}
            </p>
            <h3 className="font-display font-extrabold text-2xl mb-1">{pendiente.cancion?.titulo}</h3>
            <p className="text-white/60 mb-3">{pendiente.cancion?.artista}</p>
            <div className="mb-4">
              <YouTubePlayer linkYoutube={pendiente.cancion?.link_youtube} />
            </div>
            <p className="text-white/30 text-xs mb-4 -mt-2">
              Tocá el ícono de transmitir en el video para proyectarlo en una TV con Chromecast en la misma wifi
            </p>
            <Temporizador turnoKey={pendiente.turno} />
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
            {cola.length > 0
              ? `Sigue "${cola[0].cancion?.titulo}" (primera en la cola)`
              : modo === "cola"
              ? "La cola está vacía — agregá canciones para seguir"
              : "Listo para el siguiente turno"}
          </p>
          <button
            onClick={siguiente}
            className="btn-primary text-lg !px-8 !py-3"
            disabled={pidiendo || (modo === "cola" && cola.length === 0)}
          >
            {pidiendo ? "Eligiendo…" : cola.length > 0 ? "▶ Siguiente de la cola" : "🎲 Siguiente canción"}
          </button>
        </div>
      )}

      <div className="card p-4">
        <div className="flex items-center justify-between mb-2 flex-wrap gap-2">
          <p className="label !mb-0">Cola ({cola.length})</p>
          <div className="flex items-center gap-1.5">
            <div className="flex rounded-lg border border-white/10 overflow-hidden text-xs">
              <button
                onClick={() => cambiarModo("aleatorio")}
                className={`px-2.5 py-1.5 font-semibold transition-colors ${
                  modo === "aleatorio" ? "bg-gradient-to-r from-neon-purple/80 to-neon-pink/80 text-white" : "text-white/50 hover:text-white"
                }`}
              >
                🎲 Aleatorio
              </button>
              <button
                onClick={() => cambiarModo("cola")}
                className={`px-2.5 py-1.5 font-semibold transition-colors ${
                  modo === "cola" ? "bg-gradient-to-r from-neon-purple/80 to-neon-pink/80 text-white" : "text-white/50 hover:text-white"
                }`}
              >
                📋 Cola
              </button>
            </div>
            <button onClick={() => setMostrarCola((m) => !m)} className="btn-ghost !text-xs !py-1.5">
              <IconPlus /> {mostrarCola ? "Cerrar" : "Agregar canción"}
            </button>
          </div>
        </div>
        {cola.length > 0 && (
          <div className="flex flex-col gap-1.5 mb-2">
            {cola.map((t, i) => (
              <div key={t.id_cancion} className="flex items-center gap-2 text-sm">
                <span className="text-white/30 text-xs w-4">{i + 1}.</span>
                <span className="truncate flex-1">
                  {t.cancion?.titulo} <span className="text-white/40">— {t.cancion?.artista}</span>
                  {t.cantada_por && <span className="text-white/40"> · {formatCantantes(t.cantada_por)}</span>}
                </span>
                {esAdmin && (
                  <div className="flex items-center gap-1 shrink-0">
                    <button
                      onClick={() => moverEnCola(t.id_cancion, "arriba")}
                      disabled={i === 0 || moviendoCola === t.id_cancion}
                      className="text-white/40 hover:text-white disabled:opacity-20 px-1"
                      title="Subir"
                    >
                      ↑
                    </button>
                    <button
                      onClick={() => moverEnCola(t.id_cancion, "abajo")}
                      disabled={i === cola.length - 1 || moviendoCola === t.id_cancion}
                      className="text-white/40 hover:text-white disabled:opacity-20 px-1"
                      title="Bajar"
                    >
                      ↓
                    </button>
                    <button onClick={() => quitarDeCola(t.id_cancion)} className="text-white/40 hover:text-red-400 px-1" title="Quitar de la cola">
                      <IconTrash />
                    </button>
                  </div>
                )}
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
                <div key={c.id} className="rounded-lg hover:bg-white/5">
                  <button
                    type="button"
                    onClick={() => abrirSelectorCantantes(c.id)}
                    className="flex items-center justify-between gap-2 text-sm text-left p-1.5 w-full"
                  >
                    <span className="truncate">
                      {c.titulo} <span className="text-white/40">— {c.artista}</span>
                    </span>
                    <IconPlus className="shrink-0 text-white/40" />
                  </button>
                  {cancionExpandida === c.id && (
                    <div className="px-1.5 pb-2.5 flex flex-col gap-2">
                      <p className="text-[11px] text-white/40">¿Quién canta? (opcional — vacío = se asigna por turno)</p>
                      <div className="flex flex-wrap gap-1.5">
                        {sesion.participantes.map((p) => (
                          <button
                            key={p}
                            type="button"
                            onClick={() => toggleCantante(p)}
                            className={cantantesElegidos.includes(p) ? "chip-active" : "chip"}
                          >
                            {p}
                          </button>
                        ))}
                      </div>
                      <button onClick={() => agregarACola(c.id, cantantesElegidos)} className="btn-primary !py-1.5 !text-xs self-start">
                        <IconPlus /> {cantantesElegidos.length >= 2 ? "Agregar dueto" : "Agregar a la cola"}
                      </button>
                    </div>
                  )}
                </div>
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
                    #{t.turno} {t.cancion?.titulo} <span className="text-white/40">— {formatCantantes(t.cantada_por)}</span>
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
    </>
  );
}
