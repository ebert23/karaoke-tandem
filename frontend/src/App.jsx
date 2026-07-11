import React from "react";
import { Navigate, Route, Routes } from "react-router-dom";
import GroupGate from "./components/GroupGate.jsx";
import IdentityGate from "./components/IdentityGate.jsx";
import Shell from "./components/Shell.jsx";
import { GroupProvider } from "./lib/GroupContext.jsx";
import { IdentityProvider } from "./lib/IdentityContext.jsx";
import { ToastProvider } from "./lib/ToastContext.jsx";
import Estadisticas from "./pages/Estadisticas.jsx";
import Grupo from "./pages/Grupo.jsx";
import Historial from "./pages/Historial.jsx";
import Karaoke from "./pages/Karaoke.jsx";
import Ranking from "./pages/Ranking.jsx";
import Retos from "./pages/Retos.jsx";
import Semana from "./pages/Semana.jsx";

export default function App() {
  return (
    <ToastProvider>
      <GroupProvider>
        <GroupGate>
          <IdentityProvider>
            <IdentityGate>
              <Routes>
                <Route element={<Shell />}>
                  <Route index element={<Semana />} />
                  <Route path="karaoke" element={<Karaoke />} />
                  <Route path="retos" element={<Retos />} />
                  <Route path="ranking" element={<Ranking />} />
                  <Route path="estadisticas" element={<Estadisticas />} />
                  <Route path="historial" element={<Historial />} />
                  <Route path="grupo" element={<Grupo />} />
                  <Route path="*" element={<Navigate to="/" replace />} />
                </Route>
              </Routes>
            </IdentityGate>
          </IdentityProvider>
        </GroupGate>
      </GroupProvider>
    </ToastProvider>
  );
}
