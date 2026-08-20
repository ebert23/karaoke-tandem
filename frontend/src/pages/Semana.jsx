import React, { useEffect, useMemo, useRef, useState } from "react";
import { IconEdit, IconHeart, IconPlus, IconSearch, IconSparkles, IconStar, IconTrash } from "../components/Icons.jsx";
import { useGroup } from "../lib/GroupContext.jsx";
import { useIdentity } from "../lib/IdentityContext.jsx";
import { useToast } from "../lib/ToastContext.jsx";
import { api } from "../lib/api.js";

const GENEROS_SUGERIDOS = ["Pop", "Rock", "Reggaetón", "Balada", "Cumbia", "Banda", "R&B", "Rap"];

// YouTube no expone "artista" en la búsqueda; muchos videos de karaoke
// siguen la convención "Artista - Título (Karaoke)", así que la
// aproximamos separando por guion y limpiando sufijos típicos. Es una
// suposición razonable, no una garantía — igual queda editable a mano.
function parseResultadoYoutube(r) {
  let titulo = r.titulo;
  let artista = "";
  const partes = titulo.split(/\s+[-–—]\s+/);
  if (partes.length >= 2) {
    artista = partes[0].trim();
    titulo = partes.slice(1).join(" - ").trim();
  }
  titulo = titulo
    .replace(/[([]\s*(karaoke|versi[oó]n karaoke|lyrics?|letra|official\s*(video|audio|music video)?|hd|4k|remaster(ed)?(\s*\d{4})?)\s*[)\]]/gi, "")
    .replace(/\s{2,}/g, " ")
    .replace(/[-–—\s]+$/, "")
    .trim();
  return { titulo, artista, link_youtube: r.link_youtube };
}

function EditarCancionForm({ cancion, onGuardar, onCancelar, guardando }) {
  const [form, setForm] = useState({
    titulo: cancion.titulo,
    artista: cancion.artista,
    genero: cancion.genero,
    link_youtube: cancion.link_youtube,
  });

  function submit(e) {
    e.preventDefault();
    if (!form.titulo.trim() || !form.artista.trim() || !form.genero.trim()) return;
    onGuardar(form);
  }

  return (
    <form onSubmit={submit} className="card p-4 grid grid-cols-1 sm:grid-cols-2 gap-3">
      <div>
        <label className="label">Título</label>
        <input className="input" value={form.titulo} onChange={(e) => setForm({ ...form, titulo: e.target.value })} maxLength={200} required />
      </div>
      <div>
        <label className="label">Artista</label>
        <input className="input" value={form.artista} onChange={(e) => setForm({ ...form, artista: e.target.value })} maxLength={200} required />
      </div>
      <div className="sm:col-span-2">
        <label className="label">Género</label>
        <div className="flex flex-wrap gap-1.5 mb-2">
          {GENEROS_SUGERIDOS.map((g) => (
            <button
              type="button"
              key={g}
              onClick={() => setForm({ ...form, genero: g })}
              className={form.genero === g ? "chip-active" : "chip"}
            >
              {g}
            </button>
          ))}
        </div>
        <input
          className="input"
          placeholder="U otro género…"
          value={form.genero}
          onChange={(e) => setForm({ ...form, genero: e.target.value })}
          required
        />
      </div>
      <div>
        <label className="label">Link de YouTube (opcional)</label>
        <input className="input" type="url" value={form.link_youtube} onChange={(e) => setForm({ ...form, link_youtube: e.target.value })} />
      </div>
      <div className="sm:col-span-2 flex justify-end gap-2 mt-1">
        <button type="button" className="btn-ghost" onClick={onCancelar}>
          Cancelar
        </button>
        <button className="btn-primary" disabled={guardando}>
          {guardando ? "Guardando…" : "Guardar cambios"}
        </button>
      </div>
    </form>
  );
}

function SongCard({ cancion, puedeEditar, onVotar, onFavorito, onEditar, onEliminar }) {
  const [editando, setEditando] = useState(false);
  const [guardando, setGuardando] = useState(false);
  const [eliminando, setEliminando] = useState(false);

  if (editando) {
    return (
      <EditarCancionForm
        cancion={cancion}
        guardando={guardando}
        onCancelar={() => setEditando(false)}
        onGuardar={async (data) => {
          setGuardando(true);
          const ok = await onEditar(cancion.id, data);
          setGuardando(false);
          if (ok) setEditando(false);
        }}
      />
    );
  }

  return (
    <div className="card p-4 flex items-center gap-3">
      <div className="flex-1 min-w-0">
        <p className="font-display font-semibold truncate">{cancion.titulo}</p>
        <p className="text-sm text-white/50 truncate">{cancion.artista}</p>
        <div className="flex items-center gap-2 mt-1.5 flex-wrap">
          <span className="chip">{cancion.genero}</span>
          {cancion.veces_cantada > 0 && <span className="chip">🎶 {cancion.veces_cantada}x cantada</span>}
          <span className="text-xs text-white/30">por {cancion.agregado_por}</span>
        </div>
      </div>
      {puedeEditar && (
        <div className="flex items-center gap-1 shrink-0">
          <button onClick={() => setEditando(true)} className="btn-ghost !px-2 !py-2 !text-white/50" title="Editar">
            <IconEdit />
          </button>
          <button
            onClick={async () => {
              if (!confirm(`¿Eliminar "${cancion.titulo}"? Se perderán sus votos y no se puede deshacer.`)) return;
              setEliminando(true);
              await onEliminar(cancion.id);
            }}
            disabled={eliminando}
            className="btn-ghost !px-2 !py-2 !text-red-300/70 hover:!text-red-300"
            title="Eliminar"
          >
            <IconTrash />
          </button>
        </div>
      )}
      {cancion.link_youtube && (
        <a
          href={cancion.link_youtube}
          target="_blank"
          rel="noreferrer"
          className="btn-ghost !px-2.5 !py-2 shrink-0"
          title="Abrir en YouTube"
        >
          ▶
        </a>
      )}
      <button
        onClick={() => onFavorito(cancion.id)}
        className={`shrink-0 w-9 h-9 rounded-xl border flex items-center justify-center transition-all active:scale-90 ${
          cancion.es_favorita
            ? "bg-amber-400/20 border-amber-400/40 text-amber-300"
            : "bg-white/5 border-white/10 text-white/40 hover:border-amber-400/40"
        }`}
        title="Favorita"
      >
        <IconStar className={cancion.es_favorita ? "fill-current" : ""} />
      </button>
      <button
        onClick={() => onVotar(cancion.id)}
        className={`shrink-0 flex flex-col items-center justify-center w-14 h-14 rounded-xl border transition-all active:scale-90 ${
          cancion.ya_voto
            ? "bg-gradient-to-br from-neon-purple to-neon-pink border-transparent shadow-neon-sm"
            : "bg-white/5 border-white/10 hover:border-neon-pink/50"
        }`}
      >
        <IconHeart className={cancion.ya_voto ? "fill-current" : ""} />
        <span className="text-xs font-bold mt-0.5">{cancion.votos}</span>
      </button>
    </div>
  );
}

function BuscadorYoutube({ onElegir }) {
  const [q, setQ] = useState("");
  const [resultados, setResultados] = useState([]);
  const [buscando, setBuscando] = useState(false);
  const [disponible, setDisponible] = useState(true);
  const { push } = useToast();

  async function buscar(e) {
    e?.preventDefault();
    e?.stopPropagation();
    if (!q.trim()) return;
    setBuscando(true);
    try {
      const r = await api.buscarYoutube(q.trim());
      setResultados(r);
    } catch (err) {
      if (/no configurada/i.test(err.message)) {
        setDisponible(false);
      } else {
        push(err.message, "error");
      }
    } finally {
      setBuscando(false);
    }
  }

  if (!disponible) return null;

  return (
    <div className="sm:col-span-2 border border-white/10 rounded-xl p-3 bg-white/[0.03]">
      {/* div, no <form>: este bloque vive dentro del <form> de "agregar canción" y
          un <form> anidado es HTML inválido (dispara el submit equivocado). */}
      <div className="flex gap-2">
        <input
          className="input"
          placeholder="Buscar en YouTube (título y artista)…"
          value={q}
          onChange={(e) => setQ(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter") {
              e.preventDefault();
              e.stopPropagation();
              buscar();
            }
          }}
        />
        <button type="button" className="btn-ghost shrink-0" onClick={buscar} disabled={buscando}>
          <IconSearch /> {buscando ? "…" : "Buscar"}
        </button>
      </div>
      {resultados.length > 0 && (
        <div className="flex flex-col gap-1.5 mt-3 max-h-56 overflow-y-auto">
          {resultados.map((r) => (
            <button
              type="button"
              key={r.link_youtube}
              onClick={() => onElegir(r)}
              className="flex items-center gap-2.5 text-left p-1.5 rounded-lg hover:bg-white/5 transition-colors min-w-0"
            >
              {r.miniatura && <img src={r.miniatura} alt="" className="w-10 h-10 rounded-md object-cover shrink-0" />}
              <div className="min-w-0">
                <p className="text-sm font-medium truncate">{r.titulo}</p>
                <p className="text-xs text-white/40 truncate">{r.canal}</p>
              </div>
            </button>
          ))}
        </div>
      )}
    </div>
  );
}

function SugerenciasGenero({ genero, onElegir }) {
  const [sugs, setSugs] = useState([]);

  useEffect(() => {
    if (!genero.trim()) {
      setSugs([]);
      return;
    }
    let vivo = true;
    api
      .sugerencias(genero.trim())
      .then((r) => vivo && setSugs(r))
      .catch(() => vivo && setSugs([]));
    return () => {
      vivo = false;
    };
  }, [genero]);

  if (sugs.length === 0) return null;

  return (
    <div className="sm:col-span-2 flex items-center gap-1.5 flex-wrap">
      <span className="text-xs text-white/40 flex items-center gap-1">
        <IconSparkles /> Sugerencias:
      </span>
      {sugs.map((s) => (
        <button
          type="button"
          key={`${s.titulo}-${s.artista}`}
          onClick={() => onElegir(s)}
          className="chip hover:!border-neon-pink/50"
        >
          {s.titulo} — {s.artista}
        </button>
      ))}
    </div>
  );
}

// Lee el archivo resolviendo la codificación: Excel en español todavía
// exporta en Windows-1252 muy seguido, y leerlo como UTF-8 deja "Corazón"
// convertido en "Coraz?n" en todo el catálogo.
async function leerCsv(archivo) {
  const buffer = await archivo.arrayBuffer();
  try {
    return new TextDecoder("utf-8", { fatal: true }).decode(buffer);
  } catch {
    return new TextDecoder("windows-1252").decode(buffer);
  }
}

function ImportarCatalogo({ idUsuario, onImportado }) {
  const { push } = useToast();
  const [contenido, setContenido] = useState("");
  const [nombreArchivo, setNombreArchivo] = useState("");
  const [previa, setPrevia] = useState(null);
  const [ocupado, setOcupado] = useState(false);
  const inputRef = useRef(null);

  function cerrar() {
    setContenido("");
    setNombreArchivo("");
    setPrevia(null);
    if (inputRef.current) inputRef.current.value = "";
  }

  async function elegirArchivo(e) {
    const archivo = e.target.files?.[0];
    if (!archivo) return;
    setOcupado(true);
    try {
      const texto = await leerCsv(archivo);
      setContenido(texto);
      setNombreArchivo(archivo.name);
      setPrevia(await api.importarCanciones(texto, idUsuario, false));
    } catch (err) {
      push(err.message, "error");
      cerrar();
    } finally {
      setOcupado(false);
    }
  }

  async function confirmar() {
    setOcupado(true);
    try {
      const r = await api.importarCanciones(contenido, idUsuario, true);
      push(`Se agregaron ${r.importadas} canciones al catálogo 🎶`, "success");
      cerrar();
      onImportado();
    } catch (err) {
      push(err.message, "error");
    } finally {
      setOcupado(false);
    }
  }

  return (
    <>
      <input ref={inputRef} type="file" accept=".csv,text/csv" onChange={elegirArchivo} className="hidden" />
      <button onClick={() => inputRef.current?.click()} disabled={ocupado} className="btn-ghost">
        Importar
      </button>

      {previa && (
        <div className="fixed inset-0 z-50 bg-black/70 backdrop-blur-sm flex items-end sm:items-center justify-center p-4">
          <div className="card p-5 w-full max-w-sm max-h-[85vh] overflow-y-auto">
            <h3 className="font-display font-bold text-lg">Importar catálogo</h3>
            <p className="text-white/40 text-xs mt-0.5 break-all">{nombreArchivo}</p>

            <div className="grid grid-cols-3 gap-2 mt-4 text-center">
              <div className="rounded-xl bg-white/5 border border-white/10 p-2">
                <p className="font-display font-extrabold text-xl text-neon-cyan">{previa.listas}</p>
                <p className="text-[11px] text-white/50 leading-tight">entran</p>
              </div>
              <div className="rounded-xl bg-white/5 border border-white/10 p-2">
                <p className="font-display font-extrabold text-xl text-amber-300">{previa.total_repetidas}</p>
                <p className="text-[11px] text-white/50 leading-tight">ya estaban</p>
              </div>
              <div className="rounded-xl bg-white/5 border border-white/10 p-2">
                <p className="font-display font-extrabold text-xl text-red-300">{previa.total_errores}</p>
                <p className="text-[11px] text-white/50 leading-tight">con error</p>
              </div>
            </div>
            <p className="text-white/40 text-xs mt-2">{previa.total_filas} filas leídas</p>

            {previa.muestra.length > 0 && (
              <div className="mt-4">
                <p className="label">Primeras que entran</p>
                <ul className="space-y-1">
                  {previa.muestra.map((c, i) => (
                    <li key={i} className="text-sm truncate">
                      {c.titulo} <span className="text-white/40">— {c.artista} · {c.genero}</span>
                    </li>
                  ))}
                </ul>
              </div>
            )}

            {previa.errores.length > 0 && (
              <div className="mt-4">
                <p className="label">Filas con problemas</p>
                <ul className="space-y-1">
                  {previa.errores.slice(0, 8).map((f) => (
                    <li key={f.fila} className="text-sm text-white/60 truncate">
                      <span className="text-red-300">Fila {f.fila}</span> · {f.motivo}
                      {f.titulo || f.artista ? ` (${f.titulo || f.artista})` : ""}
                    </li>
                  ))}
                </ul>
                {previa.total_errores > 8 && (
                  <p className="text-white/30 text-xs mt-1">y {previa.total_errores - 8} más</p>
                )}
              </div>
            )}

            <div className="flex gap-2 pt-4">
              <button onClick={confirmar} disabled={ocupado || previa.listas === 0} className="btn-primary flex-1">
                {ocupado ? "Importando…" : `Importar ${previa.listas}`}
              </button>
              <button onClick={cerrar} className="btn-ghost">Cancelar</button>
            </div>
          </div>
        </div>
      )}
    </>
  );
}

export default function Semana() {
  const { usuario } = useIdentity();
  const { grupo } = useGroup();
  const { push } = useToast();
  const esAdmin = grupo.admins?.includes(usuario.id) ?? false;
  const [canciones, setCanciones] = useState([]);
  const [loading, setLoading] = useState(true);
  const [q, setQ] = useState("");
  const [genero, setGenero] = useState("");
  const [vista, setVista] = useState("todas"); // todas | top10
  const [soloFavoritas, setSoloFavoritas] = useState(false);
  const [showForm, setShowForm] = useState(false);
  const [form, setForm] = useState({ titulo: "", artista: "", genero: "", link_youtube: "" });
  const [enviando, setEnviando] = useState(false);
  const [duplicada, setDuplicada] = useState(null);

  // Avisa mientras se escribe, en vez de dejar que llene todo el formulario
  // para enterarse recién al guardar. Se pregunta al backend (y no se compara
  // contra la lista cargada acá) por dos motivos: esa lista viene filtrada por
  // género o búsqueda, así que la repetida puede no estar; y el criterio de
  // "es la misma canción" tiene que ser uno solo.
  useEffect(() => {
    const titulo = form.titulo.trim();
    const link = form.link_youtube.trim();
    if (!showForm || (!titulo && !link)) {
      setDuplicada(null);
      return;
    }
    let vivo = true;
    const t = setTimeout(() => {
      api
        .cancionDuplicada({ titulo, artista: form.artista.trim(), link_youtube: link })
        .then((c) => vivo && setDuplicada(c))
        .catch(() => vivo && setDuplicada(null));
    }, 400);
    return () => {
      vivo = false;
      clearTimeout(t);
    };
  }, [showForm, form.titulo, form.artista, form.link_youtube]);

  async function cargar() {
    setLoading(true);
    try {
      const data =
        vista === "top10"
          ? await api.top10(usuario.id)
          : await api.canciones({ id_usuario: usuario.id, genero, q, favoritas: soloFavoritas || undefined });
      setCanciones(data);
    } catch (e) {
      push(e.message, "error");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    cargar();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [vista, genero, soloFavoritas]);

  useEffect(() => {
    const t = setTimeout(cargar, 300);
    return () => clearTimeout(t);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [q]);

  const generos = useMemo(() => {
    const deLista = new Set(canciones.map((c) => c.genero).filter(Boolean));
    return Array.from(new Set([...GENEROS_SUGERIDOS, ...deLista]));
  }, [canciones]);

  async function votar(id) {
    setCanciones((prev) =>
      prev.map((c) => (c.id === id ? { ...c, ya_voto: !c.ya_voto, votos: c.votos + (c.ya_voto ? -1 : 1) } : c))
    );
    try {
      await api.votarCancion(id, usuario.id);
    } catch (e) {
      push(e.message, "error");
      cargar();
    }
  }

  async function favorito(id) {
    setCanciones((prev) => prev.map((c) => (c.id === id ? { ...c, es_favorita: !c.es_favorita } : c)));
    try {
      await api.favoritoToggle(id, usuario.id);
    } catch (e) {
      push(e.message, "error");
      cargar();
    }
  }

  async function editar(id, data) {
    try {
      const actualizada = await api.editarCancion(id, data, usuario.id);
      setCanciones((prev) => prev.map((c) => (c.id === id ? { ...c, ...actualizada } : c)));
      push("Canción actualizada ✏️", "success");
      return true;
    } catch (e) {
      push(e.message, "error");
      return false;
    }
  }

  async function eliminar(id) {
    try {
      await api.eliminarCancion(id, usuario.id);
      setCanciones((prev) => prev.filter((c) => c.id !== id));
      push("Canción eliminada 🗑️", "success");
    } catch (e) {
      push(e.message, "error");
    }
  }

  async function agregar(e) {
    e.preventDefault();
    if (!form.titulo.trim() || !form.artista.trim() || !form.genero.trim()) return;
    setEnviando(true);
    try {
      await api.agregarCancion({ ...form, agregado_por: usuario.nombre });
      push("¡Canción agregada! 🎶", "success");
      setForm({ titulo: "", artista: "", genero: "", link_youtube: "" });
      setShowForm(false);
      cargar();
    } catch (e) {
      push(e.message, "error");
    } finally {
      setEnviando(false);
    }
  }

  return (
    <div className="flex flex-col gap-5">
      <div className="flex items-center justify-between gap-3 flex-wrap">
        <h2 className="title-glow text-2xl">Agregá tus canciones 🎶</h2>
        <div className="flex gap-2">
          <a href={api.exportCsvUrl()} className="btn-ghost" download>
            CSV
          </a>
          {esAdmin && <ImportarCatalogo idUsuario={usuario.id} onImportado={cargar} />}
          <button onClick={() => setShowForm((s) => !s)} className="btn-primary">
            <IconPlus /> Agregar
          </button>
        </div>
      </div>

      {showForm && (
        // grid-cols-1 explícito, no solo "grid": sin él la única columna es
        // "auto" y crece hasta el min-content del hijo más ancho — un título
        // largo de YouTube estiraba el formulario más allá de la pantalla y
        // dejaba Guardar fuera de vista. grid-cols-1 usa minmax(0,1fr), que
        // no permite que un hijo empuje la columna.
        <form onSubmit={agregar} className="card p-4 grid grid-cols-1 sm:grid-cols-2 gap-3">
          <BuscadorYoutube
            onElegir={(r) => {
              const { titulo, artista, link_youtube } = parseResultadoYoutube(r);
              setForm((f) => ({ ...f, titulo, artista: artista || f.artista, link_youtube }));
            }}
          />
          <div>
            <label className="label">Título</label>
            <input className="input" value={form.titulo} onChange={(e) => setForm({ ...form, titulo: e.target.value })} maxLength={200} required />
          </div>
          <div>
            <label className="label">Artista</label>
            <input className="input" value={form.artista} onChange={(e) => setForm({ ...form, artista: e.target.value })} maxLength={200} required />
          </div>
          <div className="sm:col-span-2">
            <label className="label">Género</label>
            <div className="flex flex-wrap gap-1.5 mb-2">
              {GENEROS_SUGERIDOS.map((g) => (
                <button
                  type="button"
                  key={g}
                  onClick={() => setForm({ ...form, genero: g })}
                  className={form.genero === g ? "chip-active" : "chip"}
                >
                  {g}
                </button>
              ))}
            </div>
            <input
              className="input"
              placeholder="U otro género…"
              value={form.genero}
              onChange={(e) => setForm({ ...form, genero: e.target.value })}
              required
            />
          </div>
          <div>
            <label className="label">Link de YouTube (opcional)</label>
            <input className="input" type="url" value={form.link_youtube} onChange={(e) => setForm({ ...form, link_youtube: e.target.value })} />
          </div>
          <SugerenciasGenero
            genero={form.genero}
            onElegir={(s) => setForm((f) => ({ ...f, titulo: s.titulo, artista: s.artista, genero: s.genero }))}
          />
          {duplicada && (
            <div className="sm:col-span-2 p-3 rounded-xl border border-amber-400/40 bg-amber-400/10">
              <p className="font-semibold text-sm text-amber-200">Esa canción ya está en la lista</p>
              <p className="text-white/60 text-sm mt-0.5">
                “{duplicada.titulo}” — {duplicada.artista}
                {duplicada.agregado_por ? `, la agregó ${duplicada.agregado_por}` : ""}.
              </p>
            </div>
          )}
          <div className="sm:col-span-2 flex justify-end gap-2 mt-1">
            <button type="button" className="btn-ghost" onClick={() => setShowForm(false)}>
              Cancelar
            </button>
            <button className="btn-primary" disabled={enviando || !!duplicada}>
              {enviando ? "Guardando…" : duplicada ? "Ya está en la lista" : "Guardar canción"}
            </button>
          </div>
        </form>
      )}

      <div className="flex items-center gap-2 overflow-x-auto pb-1 -mx-1 px-1">
        <button onClick={() => setVista("todas")} className={vista === "todas" ? "chip-active" : "chip"}>
          Todas
        </button>
        <button onClick={() => setVista("top10")} className={vista === "top10" ? "chip-active" : "chip"}>
          🏆 Top 10
        </button>
        <button onClick={() => setSoloFavoritas((s) => !s)} className={soloFavoritas ? "chip-active shrink-0" : "chip shrink-0"}>
          ⭐ Favoritas
        </button>
        <span className="w-px h-5 bg-white/10 mx-1 shrink-0" />
        {generos.map((g) => (
          <button
            key={g}
            onClick={() => setGenero(genero === g ? "" : g)}
            className={genero === g ? "chip-active shrink-0" : "chip shrink-0"}
          >
            {g}
          </button>
        ))}
      </div>

      {vista === "todas" && (
        <input className="input" placeholder="Buscar por título o artista…" value={q} onChange={(e) => setQ(e.target.value)} />
      )}

      {loading ? (
        <p className="text-white/40 text-center py-10">Cargando canciones…</p>
      ) : canciones.length === 0 ? (
        <p className="text-white/40 text-center py-10">Aún no hay canciones. ¡Agrega la primera!</p>
      ) : (
        <div className="flex flex-col gap-2.5">
          {canciones.map((c) => (
            <SongCard
              key={c.id}
              cancion={c}
              puedeEditar={esAdmin || c.agregado_por.toLowerCase() === usuario.nombre.toLowerCase()}
              onVotar={votar}
              onFavorito={favorito}
              onEditar={editar}
              onEliminar={eliminar}
            />
          ))}
        </div>
      )}
    </div>
  );
}
