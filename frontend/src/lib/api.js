// Cliente HTTP minimalista para la API de KaraokeTandem.
const BASE = "/api";
const GRUPO_STORAGE_KEY = "kt_grupo";

function idGrupoActual() {
  try {
    const g = JSON.parse(localStorage.getItem(GRUPO_STORAGE_KEY) || "null");
    return g?.id || "";
  } catch {
    return "";
  }
}

async function request(path, options = {}) {
  const idGrupo = idGrupoActual();
  const res = await fetch(`${BASE}${path}`, {
    headers: {
      "Content-Type": "application/json",
      ...(idGrupo ? { "X-Grupo-Id": idGrupo } : {}),
    },
    ...options,
  });
  if (!res.ok) {
    let detail = res.statusText;
    try {
      const body = await res.json();
      detail = body.detail || detail;
    } catch {
      /* respuesta sin JSON */
    }
    throw new Error(detail);
  }
  if (res.status === 204) return null;
  return res.json();
}

const get = (path) => request(path);
const post = (path, body) => request(path, { method: "POST", body: JSON.stringify(body ?? {}) });
const put = (path, body) => request(path, { method: "PUT", body: JSON.stringify(body ?? {}) });
const del = (path, body) => request(path, { method: "DELETE", body: JSON.stringify(body ?? {}) });

function qs(params = {}) {
  const s = new URLSearchParams(Object.entries(params).filter(([, v]) => v !== undefined && v !== null && v !== ""));
  return s.toString() ? `?${s}` : "";
}

export const api = {
  // Grupos
  crearGrupo: (nombre, foto, creadoPorNombre) => post("/grupos", { nombre, foto, creado_por_nombre: creadoPorNombre }),
  unirseGrupo: (codigo) => post("/grupos/unirse", { codigo }),
  grupoActual: (idGrupo) => get(`/grupos/${idGrupo}`),
  reclamarAdmin: (idGrupo, idUsuario) => post(`/grupos/${idGrupo}/reclamar-admin`, { id_usuario: idUsuario }),
  hacerAdmin: (idGrupo, idUsuarioObjetivo, idUsuarioActor) =>
    post(`/grupos/${idGrupo}/miembros/${idUsuarioObjetivo}/admin`, { id_usuario_actor: idUsuarioActor }),
  quitarAdmin: (idGrupo, idUsuarioObjetivo, idUsuarioActor) =>
    del(`/grupos/${idGrupo}/miembros/${idUsuarioObjetivo}/admin`, { id_usuario_actor: idUsuarioActor }),
  expulsarMiembro: (idGrupo, idUsuarioObjetivo, idUsuarioActor) =>
    del(`/grupos/${idGrupo}/miembros/${idUsuarioObjetivo}`, { id_usuario_actor: idUsuarioActor }),

  // Usuarios
  loginOCrear: (nombre, foto = "") => post("/usuarios", { nombre, foto }),
  usuarios: () => get("/usuarios"),

  // Canciones
  canciones: (params = {}) => get(`/canciones${qs(params)}`),
  top10: (idUsuario) => get(`/canciones/top10${qs({ id_usuario: idUsuario })}`),
  agregarCancion: (data) => post("/canciones", data),
  editarCancion: (idCancion, data, idUsuario) => put(`/canciones/${idCancion}`, { ...data, id_usuario: idUsuario }),
  eliminarCancion: (idCancion, idUsuario) => del(`/canciones/${idCancion}`, { id_usuario: idUsuario }),
  votarCancion: (idCancion, idUsuario) => post(`/canciones/${idCancion}/votar`, { id_usuario: idUsuario }),
  favoritoToggle: (idCancion, idUsuario) => post(`/canciones/${idCancion}/favorito`, { id_usuario: idUsuario }),
  sugerencias: (genero) => get(`/canciones/sugerencias${qs({ genero })}`),
  buscarYoutube: (q) => get(`/youtube/buscar${qs({ q })}`),
  exportCsvUrl: () => `${BASE}/canciones/export.csv`,

  // Sesiones
  sesionActiva: () => get("/sesiones/activa"),
  crearSesion: (participantes) => post("/sesiones", { participantes }),
  historialSesiones: () => get("/sesiones"),
  detalleSesion: (id) => get(`/sesiones/${id}/detalle`),
  sesionUnirse: (id, nombre) => post(`/sesiones/${id}/unirse`, { nombre }),
  agregarACola: (id, idCancion, cantantes = []) => post(`/sesiones/${id}/cola`, { id_cancion: idCancion, cantantes }),
  siguienteCancion: (id) => post(`/sesiones/${id}/siguiente`),
  votarTurno: (id, idCancion, idUsuario, puntuacion) =>
    post(`/sesiones/${id}/canciones/${idCancion}/votar_turno`, { id_usuario: idUsuario, puntuacion }),
  votosTurno: (id, idCancion) => get(`/sesiones/${id}/canciones/${idCancion}/votos_turno`),
  marcarCantada: (id, idCancion, puntuacion) =>
    post(`/sesiones/${id}/canciones/${idCancion}/cantada`, { puntuacion: puntuacion ?? null }),
  saltarCancion: (id, idCancion) => post(`/sesiones/${id}/canciones/${idCancion}/saltar`),
  finalizarSesion: (id) => post(`/sesiones/${id}/finalizar`),

  // Retos
  retos: (categoria) => get(`/retos${qs({ categoria })}`),
  retoAleatorio: (categoria) => get(`/retos/aleatorio${qs({ categoria })}`),
  crearReto: (data) => post("/retos", data),

  // Ranking / estadísticas
  rankingNoche: (idSesion) => get(`/ranking/noche/${idSesion}`),
  rankingHistorico: () => get("/ranking/historico"),
  estadisticas: (idUsuario) => get(`/estadisticas/${idUsuario}`),
};
