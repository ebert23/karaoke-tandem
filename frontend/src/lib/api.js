// Cliente HTTP minimalista para la API de KaraokeTandem.
import { DJ_STORAGE_KEY, GRUPO_STORAGE_KEY } from "./storageKeys.js";

const BASE = "/api";

function idGrupoActual() {
  try {
    const g = JSON.parse(localStorage.getItem(GRUPO_STORAGE_KEY) || "null");
    return g?.id || "";
  } catch {
    return "";
  }
}

// Sesión del DJ: {id_grupo, nombre, codigo}. Vive aparte de la del grupo
// porque el DJ entra por su propio código y su celular no tiene por qué
// estar unido a ninguna sala.
export function sesionDj() {
  try {
    return JSON.parse(localStorage.getItem(DJ_STORAGE_KEY) || "null");
  } catch {
    return null;
  }
}

export function guardarSesionDj(datos) {
  if (datos) localStorage.setItem(DJ_STORAGE_KEY, JSON.stringify(datos));
  else localStorage.removeItem(DJ_STORAGE_KEY);
}

async function request(path, options = {}) {
  const { dj, ...opts } = options;
  // Las rutas del DJ mandan su propio grupo y su código: no dependen de que
  // el celular tenga una sala guardada.
  const sesion = dj ? sesionDj() : null;
  const idGrupo = dj ? sesion?.id_grupo : idGrupoActual();
  const res = await fetch(`${BASE}${path}`, {
    headers: {
      "Content-Type": "application/json",
      ...(idGrupo ? { "X-Grupo-Id": idGrupo } : {}),
      ...(dj && sesion?.codigo ? { "X-DJ-Codigo": sesion.codigo } : {}),
    },
    ...opts,
  });
  if (!res.ok) {
    let detail = res.statusText;
    try {
      const body = await res.json();
      // body.detail suele ser un string (HTTPException de FastAPI), pero en
      // un 422 de validación es una lista de objetos {loc, msg, type} — si
      // se pasa tal cual a Error(), el mensaje termina siendo el inservible
      // "[object Object]" (toString de un objeto/array de objetos).
      if (typeof body.detail === "string") {
        detail = body.detail;
      } else if (Array.isArray(body.detail)) {
        detail = body.detail.map((d) => d.msg || JSON.stringify(d)).join("; ");
      } else if (body.detail) {
        detail = JSON.stringify(body.detail);
      }
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

// Variantes que adjuntan las credenciales del DJ (X-Grupo-Id + X-DJ-Codigo).
const getDj = (path) => request(path, { dj: true });
const postDj = (path, body) => request(path, { method: "POST", body: JSON.stringify(body ?? {}), dj: true });
const delDj = (path) => request(path, { method: "DELETE", dj: true });

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
  quitarDeCola: (id, idCancion, idUsuarioActor) => del(`/sesiones/${id}/cola/${idCancion}`, { id_usuario_actor: idUsuarioActor }),
  moverEnCola: (id, idCancion, idUsuarioActor, direccion) =>
    post(`/sesiones/${id}/cola/${idCancion}/mover`, { id_usuario_actor: idUsuarioActor, direccion }),
  siguienteCancion: (id, idUsuarioActor, modo) =>
    post(`/sesiones/${id}/siguiente`, { id_usuario_actor: idUsuarioActor, modo }),
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

  // --- Modo salón ---
  // Panel del dueño (usa el X-Grupo-Id normal).
  convertirASalon: (idGrupo, idUsuarioActor) =>
    post(`/grupos/${idGrupo}/convertir-a-salon`, { id_usuario_actor: idUsuarioActor }),
  regenerarCodigoDj: (idGrupo, idUsuarioActor) =>
    post(`/grupos/${idGrupo}/codigo-dj`, { id_usuario_actor: idUsuarioActor }),
  mesas: () => get("/mesas"),
  crearMesa: (numero, tamano) => post("/mesas", { numero, tamano }),
  abrirMesa: (idMesa, tamano) => post(`/mesas/${idMesa}/abrir`, { tamano }),
  cerrarMesa: (idMesa) => post(`/mesas/${idMesa}/cerrar`),
  cerrarTodasLasMesas: () => post("/mesas/cerrar-todas"),
  eliminarMesa: (idMesa, idUsuarioActor) => del(`/mesas/${idMesa}`, { id_usuario_actor: idUsuarioActor }),
  pantallaSalon: () => get("/salon/pantalla"),

  // Cliente en la mesa: solo con el código del QR, sin X-Grupo-Id.
  estadoMesa: (codigo) => get(`/mesa/${codigo}`),
  catalogoMesa: (codigo, params = {}) => get(`/mesa/${codigo}/catalogo${qs(params)}`),
  pedirCancion: (codigo, idCancion, pedidoPor) =>
    post(`/mesa/${codigo}/pedidos`, { id_cancion: idCancion, pedido_por: pedidoPor }),
  cancelarPedido: (codigo, idPedido) => del(`/mesa/${codigo}/pedidos/${idPedido}`),
  sugerirCancion: (codigo, titulo, artista, pedidoPor) =>
    post(`/mesa/${codigo}/sugerencias`, { titulo, artista, pedido_por: pedidoPor }),

  // Vista del DJ.
  djEntrar: (codigo) => post("/dj/entrar", { codigo }),
  djCola: () => getDj("/dj/cola"),
  djSiguiente: () => postDj("/dj/siguiente"),
  djCantada: (idPedido) => postDj(`/dj/pedidos/${idPedido}/cantada`),
  djNoVino: (idPedido) => postDj(`/dj/pedidos/${idPedido}/no-vino`),
  djSubir: (idPedido) => postDj(`/dj/pedidos/${idPedido}/subir`),
  djCancelar: (idPedido) => delDj(`/dj/pedidos/${idPedido}`),
  djSugerencias: () => getDj("/dj/sugerencias"),
  djMesas: () => getDj("/dj/mesas"),
};
