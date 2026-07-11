import React, { createContext, useCallback, useContext, useState } from "react";

const ToastContext = createContext(null);
let idCounter = 0;

export function ToastProvider({ children }) {
  const [toasts, setToasts] = useState([]);

  const push = useCallback((message, type = "info") => {
    const id = ++idCounter;
    setToasts((t) => [...t, { id, message, type }]);
    setTimeout(() => setToasts((t) => t.filter((x) => x.id !== id)), 3200);
  }, []);

  return (
    <ToastContext.Provider value={{ push }}>
      {children}
      <div className="fixed bottom-20 md:bottom-6 left-1/2 -translate-x-1/2 z-[100] flex flex-col gap-2 items-center w-[92%] max-w-sm">
        {toasts.map((t) => (
          <div
            key={t.id}
            className={`w-full text-center px-4 py-2.5 rounded-xl text-sm font-medium shadow-lg backdrop-blur-md border animate-[fadeIn_.15s_ease]
              ${
                t.type === "error"
                  ? "bg-red-500/20 border-red-500/40 text-red-200"
                  : t.type === "success"
                    ? "bg-emerald-500/20 border-emerald-500/40 text-emerald-200"
                    : "bg-ink-800/90 border-white/10 text-white"
              }`}
          >
            {t.message}
          </div>
        ))}
      </div>
    </ToastContext.Provider>
  );
}

export function useToast() {
  const ctx = useContext(ToastContext);
  if (!ctx) throw new Error("useToast debe usarse dentro de ToastProvider");
  return ctx;
}
