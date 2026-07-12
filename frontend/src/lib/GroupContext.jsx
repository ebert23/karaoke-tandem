import React, { createContext, useContext, useEffect, useState } from "react";
import { api } from "./api.js";
import { GRUPO_STORAGE_KEY as STORAGE_KEY, usuarioStorageKey } from "./storageKeys.js";

const GroupContext = createContext(null);

export function GroupProvider({ children }) {
  const [grupo, setGrupo] = useState(() => {
    try {
      return JSON.parse(localStorage.getItem(STORAGE_KEY) || "null");
    } catch {
      return null;
    }
  });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    if (grupo) localStorage.setItem(STORAGE_KEY, JSON.stringify(grupo));
  }, [grupo]);

  // Escribe localStorage ya mismo (no solo vía el useEffect de abajo): el
  // efecto corre recién después del próximo render, y api.js lee
  // X-Grupo-Id directo de localStorage — cualquier request hecho entre el
  // setGrupo() y ese render (p.ej. loginOCrear justo después de crear el
  // grupo) saldría sin el header y fallaría con 422.
  function guardarGrupo(g) {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(g));
    setGrupo(g);
  }

  async function crearGrupo(nombre, creadoPorNombre, foto = "") {
    setLoading(true);
    setError("");
    try {
      const g = await api.crearGrupo(nombre, foto, creadoPorNombre);
      if (creadoPorNombre.trim()) {
        // El backend ya crea (y hace admin) a este usuario al crear el
        // grupo. Lo dejamos identificado de una para no volver a pedirle
        // el nombre en IdentityGate — pero hay que escribirlo en
        // localStorage ANTES de guardarGrupo()/setGrupo(), porque eso es
        // justo lo que dispara el montaje de IdentityProvider (que lee el
        // usuario de storage una sola vez, al montar).
        localStorage.setItem(STORAGE_KEY, JSON.stringify(g));
        const u = await api.loginOCrear(creadoPorNombre.trim());
        localStorage.setItem(usuarioStorageKey(g.id), JSON.stringify(u));
      }
      guardarGrupo(g);
      return g;
    } catch (e) {
      setError(e.message || "No se pudo crear el grupo.");
      throw e;
    } finally {
      setLoading(false);
    }
  }

  async function unirseAGrupo(codigo) {
    setLoading(true);
    setError("");
    try {
      const g = await api.unirseGrupo(codigo);
      guardarGrupo(g);
      return g;
    } catch (e) {
      setError(e.message || "Código inválido.");
      throw e;
    } finally {
      setLoading(false);
    }
  }

  function salirDelGrupo() {
    localStorage.removeItem(STORAGE_KEY);
    setGrupo(null);
  }

  return (
    <GroupContext.Provider value={{ grupo, setGrupo, crearGrupo, unirseAGrupo, salirDelGrupo, loading, error }}>
      {children}
    </GroupContext.Provider>
  );
}

export function useGroup() {
  const ctx = useContext(GroupContext);
  if (!ctx) throw new Error("useGroup debe usarse dentro de GroupProvider");
  return ctx;
}
