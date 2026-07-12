import React, { useEffect, useMemo, useState } from "react";
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
    <form onSubmit={submit} className="card p-4 grid sm:grid-cols-2 gap-3">
      <div>
        <label className="label">Título</label>
        <input className="input" value={form.titulo} onChange={(e) => setForm({ ...form, titulo: e.target.value })} maxLength={200} required />
      </div>
      <div>
        <label className="label">Artista</label>
        <input className="input" value={form.artista} onChange={(e) => setForm({ ...form, artista: e.target.value })} maxLength={200} required />
      </div>
      <div>
        <label className="label">Género</label>
        <input className="input" value={form.genero} onChange={(e) => setForm({ ...form, genero: e.target.value })} required />
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
              className="flex items-center gap-2.5 text-left p-1.5 rounded-lg hover:bg-white/5 transition-colors"
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
          <button onClick={() => setShowForm((s) => !s)} className="btn-primary">
            <IconPlus /> Agregar
          </button>
        </div>
      </div>

      {showForm && (
        <form onSubmit={agregar} className="card p-4 grid sm:grid-cols-2 gap-3">
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
          <div>
            <label className="label">Género</label>
            <input className="input" list="generos-list" value={form.genero} onChange={(e) => setForm({ ...form, genero: e.target.value })} required />
            <datalist id="generos-list">
              {GENEROS_SUGERIDOS.map((g) => (
                <option key={g} value={g} />
              ))}
            </datalist>
          </div>
          <div>
            <label className="label">Link de YouTube (opcional)</label>
            <input className="input" type="url" value={form.link_youtube} onChange={(e) => setForm({ ...form, link_youtube: e.target.value })} />
          </div>
          <SugerenciasGenero
            genero={form.genero}
            onElegir={(s) => setForm((f) => ({ ...f, titulo: s.titulo, artista: s.artista, genero: s.genero }))}
          />
          <div className="sm:col-span-2 flex justify-end gap-2 mt-1">
            <button type="button" className="btn-ghost" onClick={() => setShowForm(false)}>
              Cancelar
            </button>
            <button className="btn-primary" disabled={enviando}>
              {enviando ? "Guardando…" : "Guardar canción"}
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
