import React, { createContext, useContext, useEffect, useState } from "react";
import { useGroup } from "./GroupContext.jsx";
import { api } from "./api.js";
import { usuarioStorageKey } from "./storageKeys.js";

const IdentityContext = createContext(null);

export function IdentityProvider({ children }) {
  const { grupo } = useGroup();
  const [usuario, setUsuario] = useState(() => {
    try {
      return JSON.parse(localStorage.getItem(usuarioStorageKey(grupo.id)) || "null");
    } catch {
      return null;
    }
  });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    if (usuario) localStorage.setItem(usuarioStorageKey(grupo.id), JSON.stringify(usuario));
  }, [usuario, grupo.id]);

  async function ingresar(nombre) {
    setLoading(true);
    setError("");
    try {
      const u = await api.loginOCrear(nombre);
      setUsuario(u);
      return u;
    } catch (e) {
      setError(e.message || "No se pudo ingresar. Revisa tu conexión.");
      throw e;
    } finally {
      setLoading(false);
    }
  }

  function salir() {
    localStorage.removeItem(usuarioStorageKey(grupo.id));
    setUsuario(null);
  }

  return (
    <IdentityContext.Provider value={{ usuario, setUsuario, ingresar, salir, loading, error }}>
      {children}
    </IdentityContext.Provider>
  );
}

export function useIdentity() {
  const ctx = useContext(IdentityContext);
  if (!ctx) throw new Error("useIdentity debe usarse dentro de IdentityProvider");
  return ctx;
}
