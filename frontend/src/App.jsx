import React from "react";
import { Navigate, Route, Routes } from "react-router-dom";
import GroupGate from "./components/GroupGate.jsx";
import IdentityGate from "./components/IdentityGate.jsx";
import Shell from "./components/Shell.jsx";
import { GroupProvider } from "./lib/GroupContext.jsx";
import { IdentityProvider } from "./lib/IdentityContext.jsx";
import { ToastProvider } from "./lib/ToastContext.jsx";
import DJ from "./pages/DJ.jsx";
import Estadisticas from "./pages/Estadisticas.jsx";
import Grupo from "./pages/Grupo.jsx";
import Historial from "./pages/Historial.jsx";
import Karaoke from "./pages/Karaoke.jsx";
import Local from "./pages/Local.jsx";
import Mesa from "./pages/Mesa.jsx";
import Ranking from "./pages/Ranking.jsx";
import Retos from "./pages/Retos.jsx";
import Semana from "./pages/Semana.jsx";
import TV from "./pages/TV.jsx";

export default function App() {
  return (
    <ToastProvider>
      <Routes>
        {/* Modo salón: dos flujos que NO pasan por GroupGate/IdentityGate.
            El cliente entra escaneando el QR de su mesa y el DJ con su
            código — ninguno de los dos está unido a una sala ni tiene por
            qué identificarse como miembro de un grupo. */}
        <Route path="mesa/:codigo" element={<Mesa />} />
        <Route path="dj" element={<DJ />} />

        <Route
          path="*"
          element={
            <GroupProvider>
              <GroupGate>
                <IdentityProvider>
                  <IdentityGate>
                    <Routes>
                      <Route path="tv" element={<TV />} />
                      <Route element={<Shell />}>
                        <Route index element={<Semana />} />
                        <Route path="karaoke" element={<Karaoke />} />
                        <Route path="retos" element={<Retos />} />
                        <Route path="ranking" element={<Ranking />} />
                        <Route path="estadisticas" element={<Estadisticas />} />
                        <Route path="historial" element={<Historial />} />
                        <Route path="grupo" element={<Grupo />} />
                        <Route path="local" element={<Local />} />
                        <Route path="*" element={<Navigate to="/" replace />} />
                      </Route>
                    </Routes>
                  </IdentityGate>
                </IdentityProvider>
              </GroupGate>
            </GroupProvider>
          }
        />
      </Routes>
    </ToastProvider>
  );
}
