import React, { useEffect, useState } from "react";
import { INSTALAR_STORAGE_KEY } from "../lib/storageKeys.js";

// Ya instalada: Android/desktop lo dicen por display-mode, iOS por su propia
// bandera no estándar en navigator.
function yaInstalada() {
  return (
    window.matchMedia?.("(display-mode: standalone)").matches ||
    window.navigator.standalone === true
  );
}

function esIOS() {
  return /iphone|ipad|ipod/i.test(window.navigator.userAgent);
}

/**
 * Invitación a instalar la app en el teléfono.
 *
 * Son dos caminos distintos porque los navegadores no se parecen en nada acá:
 * Chrome/Edge/Android disparan `beforeinstallprompt` y dejan abrir el diálogo
 * nativo desde un clic; Safari en iOS nunca lo dispara y solo se puede instalar
 * a mano desde Compartir → "Agregar a inicio", así que ahí lo único que se
 * puede hacer es explicar dónde tocar.
 */
export default function InstalarApp() {
  const [evento, setEvento] = useState(null);
  const [oculto, setOculto] = useState(() => localStorage.getItem(INSTALAR_STORAGE_KEY) === "1");
  const [instalada, setInstalada] = useState(yaInstalada);

  useEffect(() => {
    function alPoderInstalar(e) {
      // Sin preventDefault, Chrome muestra su propia barra y el evento se
      // pierde: hay que guardarlo para poder abrir el diálogo después.
      e.preventDefault();
      setEvento(e);
    }
    function alInstalar() {
      setInstalada(true);
      setEvento(null);
    }
    window.addEventListener("beforeinstallprompt", alPoderInstalar);
    window.addEventListener("appinstalled", alInstalar);
    return () => {
      window.removeEventListener("beforeinstallprompt", alPoderInstalar);
      window.removeEventListener("appinstalled", alInstalar);
    };
  }, []);

  function ocultar() {
    localStorage.setItem(INSTALAR_STORAGE_KEY, "1");
    setOculto(true);
  }

  async function instalar() {
    if (!evento) return;
    evento.prompt();
    const { outcome } = await evento.userChoice;
    // El evento no se puede reusar: si dijo que no, se guarda la decisión para
    // no volver a aparecer en cada pantalla.
    setEvento(null);
    if (outcome === "dismissed") ocultar();
  }

  if (instalada || oculto) return null;
  if (!evento && !esIOS()) return null;

  return (
    <div className="fixed bottom-3 inset-x-3 z-[60] sm:left-auto sm:right-4 sm:w-80">
      <div className="card p-3 flex items-start gap-3 shadow-2xl border-neon-purple/40">
        <img src="/icons/icon-192.png" alt="" className="w-10 h-10 rounded-xl shrink-0" />
        <div className="min-w-0 flex-1">
          <p className="font-display font-bold text-sm">Instalá KaraokeTandem</p>
          {evento ? (
            <>
              <p className="text-white/50 text-xs mt-0.5">
                Queda como una app más en tu teléfono, sin barra del navegador.
              </p>
              <div className="flex gap-2 mt-2">
                <button onClick={instalar} className="btn-primary !px-3 !py-1.5 !text-xs">
                  Instalar
                </button>
                <button onClick={ocultar} className="btn-ghost !px-3 !py-1.5 !text-xs">
                  Ahora no
                </button>
              </div>
            </>
          ) : (
            <>
              <p className="text-white/50 text-xs mt-0.5 leading-relaxed">
                Tocá <strong>Compartir</strong> abajo y elegí{" "}
                <strong>“Agregar a pantalla de inicio”</strong>.
              </p>
              <button onClick={ocultar} className="btn-ghost !px-3 !py-1.5 !text-xs mt-2">
                Entendido
              </button>
            </>
          )}
        </div>
      </div>
    </div>
  );
}
