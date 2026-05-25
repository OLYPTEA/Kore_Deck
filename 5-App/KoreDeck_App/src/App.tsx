// =============================================================================
// App.tsx — Composant racine Kore Deck
// =============================================================================

import "./index.css";
import { useEffect, useRef } from "react";
import { useStore }    from "@/store";
import { useSerial }   from "@/hooks/useSerial";
import { Dock }           from "@/components/Dock";
import { TitleBar }       from "@/components/TitleBar";
import { PaletteApplier } from "@/components/PaletteApplier";
import { BgThemeApplier } from "@/components/BgThemeApplier";
import { Dashboard }   from "@/pages/Dashboard";
import { Config }      from "@/pages/Config";
import { Profiles }    from "@/pages/Profiles";
import { Settings }    from "@/pages/Settings";

// Ordre canonique des pages — détermine le sens de la transition (forward/backward).
// Si on va de dashboard→settings : forward (slide depuis la droite).
// Si on revient settings→dashboard : backward (slide depuis la gauche).
const NAV_ORDER = ["dashboard", "config", "profiles", "settings"] as const;

// Simulateur de données — UNIQUEMENT en mode développement (npm run dev).
// En production Tauri, les vraies stats viennent du WebSocket de l'agent Python.
function useDevSimulator() {
  const updateStats = useStore((s) => s.updateStats);
  const setConn     = useStore((s) => s.setConnectionStatus);

  useEffect(() => {
    if (!import.meta.env.DEV) return;   // ← désactivé en build de production

    const connTimer = setTimeout(() => {
      setConn({ status: "connected", port: "COM3", baud: 115200, lastSeen: new Date() });
    }, 1500);

    let cpu = 34, ram = 61, pomoSec = 24 * 60 + 13;

    const interval = setInterval(() => {
      cpu = Math.max(5,  Math.min(95,  cpu + (Math.random() - 0.5) * 4));
      ram = Math.max(30, Math.min(90,  ram + (Math.random() - 0.5) * 1));
      if (pomoSec > 0) pomoSec--;

      updateStats({
        cpu: Math.round(cpu), ram: Math.round(ram), fps: 144,
        micMuted: false, dndActive: false, obsActive: false,
        trackTitle: "Harder Better Faster Stronger",
        trackArtist: "Daft Punk",
        pomoMinutes: Math.floor(pomoSec / 60),
        pomoSeconds: pomoSec % 60,
        pomoSession: 3, pomoRunning: true,
      });
    }, 1000);

    return () => {
      clearTimeout(connTimer);
      clearInterval(interval);
    };
  }, [updateStats, setConn]);
}

export default function App() {
  const selectedPage = useStore((s) => s.selectedPage);
  useSerial();
  useDevSimulator();

  // Détermine le sens de la transition avant le render (pour data-page-dir).
  // `initial` au premier mount évite que la page d'arrivée slide à l'ouverture.
  const prevPageRef = useRef(selectedPage);
  const isFirstRender = useRef(true);
  let direction: "forward" | "backward" | "initial" = "initial";
  if (!isFirstRender.current) {
    const currentIdx = NAV_ORDER.indexOf(selectedPage as typeof NAV_ORDER[number]);
    const prevIdx    = NAV_ORDER.indexOf(prevPageRef.current as typeof NAV_ORDER[number]);
    direction = currentIdx >= prevIdx ? "forward" : "backward";
  }
  useEffect(() => {
    prevPageRef.current = selectedPage;
    isFirstRender.current = false;
  });

  const pages: Record<string, React.ReactNode> = {
    dashboard: <Dashboard />,
    config:    <Config />,
    profiles:  <Profiles />,
    settings:  <Settings />,
  };

  return (
    <div style={{
      display: "flex", flexDirection: "column",
      height: "100vh", overflow: "hidden",
    }}>
      <PaletteApplier />
      <BgThemeApplier />
      <TitleBar />
      {/* Transition style Apple : slide horizontal + crossfade, easing snappy.
          `key` force le remount → l'animation rejoue à chaque changement.
          Pas de view-transition-name (cassait le containing block du Dock). */}
      <div
        key={selectedPage}
        data-page-dir={direction}
        className="kd-page-anim"
        style={{ flex: 1, minHeight: 0, position: "relative" }}>
        {pages[selectedPage]}
      </div>
      <Dock />
    </div>
  );
}
