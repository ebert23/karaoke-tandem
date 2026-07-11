import React from "react";
import { NavLink, Outlet } from "react-router-dom";
import { useGroup } from "../lib/GroupContext.jsx";
import { useIdentity } from "../lib/IdentityContext.jsx";
import { IconChart, IconDice, IconHistory, IconLogout, IconMic, IconMusic, IconTrophy, IconUsers } from "./Icons.jsx";

const NAV_ITEMS = [
  { to: "/", label: "Semana", Icon: IconMusic, end: true },
  { to: "/karaoke", label: "Karaoke", Icon: IconMic },
  { to: "/retos", label: "Retos", Icon: IconDice },
  { to: "/ranking", label: "Ranking", Icon: IconTrophy },
  { to: "/estadisticas", label: "Stats", Icon: IconChart },
  { to: "/historial", label: "Historial", Icon: IconHistory },
];

function NavItemDesktop({ to, label, Icon, end }) {
  return (
    <NavLink
      to={to}
      end={end}
      className={({ isActive }) =>
        `flex items-center gap-3 px-4 py-3 rounded-xl font-display font-semibold text-sm transition-colors ${
          isActive ? "bg-gradient-to-r from-neon-purple/80 to-neon-pink/80 text-white shadow-neon-sm" : "text-white/60 hover:bg-white/5 hover:text-white"
        }`
      }
    >
      <Icon />
      {label}
    </NavLink>
  );
}

function NavItemMobile({ to, label, Icon, end }) {
  return (
    <NavLink
      to={to}
      end={end}
      className={({ isActive }) =>
        `flex flex-col items-center justify-center gap-0.5 flex-1 py-2.5 text-[11px] font-semibold transition-colors ${
          isActive ? "text-neon-pink" : "text-white/40"
        }`
      }
    >
      {({ isActive }) => (
        <>
          <Icon className={isActive ? "animate-pulseGlow" : ""} />
          {label}
        </>
      )}
    </NavLink>
  );
}

export default function Shell() {
  const { usuario, salir } = useIdentity();
  const { grupo } = useGroup();

  return (
    <div className="min-h-screen flex">
      {/* Sidebar desktop */}
      <aside className="hidden md:flex md:flex-col w-64 shrink-0 border-r border-white/10 p-5 gap-1">
        <div className="flex items-center gap-2 mb-6 px-1">
          <span className="text-2xl animate-pulseGlow">🎤</span>
          <h1 className="title-glow text-xl">KaraokeTandem</h1>
        </div>
        {NAV_ITEMS.map((item) => (
          <NavItemDesktop key={item.to} {...item} />
        ))}
        <NavLink
          to="/grupo"
          className={({ isActive }) =>
            `flex items-center gap-3 px-4 py-3 rounded-xl font-display font-semibold text-sm transition-colors ${
              isActive ? "bg-gradient-to-r from-neon-purple/80 to-neon-pink/80 text-white shadow-neon-sm" : "text-white/60 hover:bg-white/5 hover:text-white"
            }`
          }
        >
          <IconUsers />
          {grupo?.nombre || "Grupo"}
        </NavLink>
        <div className="mt-auto pt-4 border-t border-white/10 flex items-center gap-3 px-1">
          <div className="w-9 h-9 rounded-full bg-gradient-to-br from-neon-purple to-neon-pink flex items-center justify-center font-display font-bold text-sm shrink-0">
            {usuario?.nombre?.[0]?.toUpperCase()}
          </div>
          <div className="flex-1 min-w-0">
            <p className="text-sm font-semibold truncate">{usuario?.nombre}</p>
            <p className="text-xs text-white/40">{usuario?.puntos_totales ?? 0} pts</p>
          </div>
          <button onClick={salir} className="text-white/40 hover:text-neon-pink transition-colors" title="Cambiar de usuario">
            <IconLogout />
          </button>
        </div>
      </aside>

      {/* Contenido */}
      <div className="flex-1 min-w-0 flex flex-col">
        <header className="md:hidden flex items-center justify-between px-4 py-3 border-b border-white/10 sticky top-0 bg-ink-950/90 backdrop-blur z-40">
          <div className="flex items-center gap-2">
            <span className="text-xl">🎤</span>
            <h1 className="title-glow text-lg">KaraokeTandem</h1>
          </div>
          <div className="flex items-center gap-2">
            <NavLink to="/grupo" className="w-8 h-8 rounded-full bg-white/5 border border-white/10 flex items-center justify-center text-white/60">
              <IconUsers />
            </NavLink>
            <button onClick={salir} className="w-8 h-8 rounded-full bg-gradient-to-br from-neon-purple to-neon-pink flex items-center justify-center font-display font-bold text-xs">
              {usuario?.nombre?.[0]?.toUpperCase()}
            </button>
          </div>
        </header>

        <main className="flex-1 min-w-0 p-4 md:p-8 pb-24 md:pb-8 max-w-5xl w-full mx-auto">
          <Outlet />
        </main>

        {/* Bottom nav mobile */}
        <nav className="md:hidden fixed bottom-0 inset-x-0 z-40 flex bg-ink-900/95 backdrop-blur border-t border-white/10 pb-[env(safe-area-inset-bottom)]">
          {NAV_ITEMS.map((item) => (
            <NavItemMobile key={item.to} {...item} />
          ))}
        </nav>
      </div>
    </div>
  );
}
