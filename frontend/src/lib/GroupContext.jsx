import React, { createContext, useContext, useEffect, useState } from "react";
import { api } from "./api.js";

const STORAGE_KEY = "kt_grupo";
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

  async function crearGrupo(nombre, creadoPorNombre, foto = "") {
    setLoading(true);
    setError("");
    try {
      const g = await api.crearGrupo(nombre, foto, creadoPorNombre);
      setGrupo(g);
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
      setGrupo(g);
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
