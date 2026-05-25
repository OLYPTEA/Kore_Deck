// =============================================================================
// TitleBar.tsx — Chrome frameless style Windows 11
// (boutons min/max/close à droite, hover rouge sur close)
// =============================================================================

import { useEffect, useState } from "react";
import { getCurrentWindow } from "@tauri-apps/api/window";
import { useStore } from "@/store";
import { KoreLogo } from "@/components/KoreLogo";

// ─── Icônes Windows 11 (SVG inline, traits 1px nets) ──────────────────────
function IconMinimize() {
  return (
    <svg width="10" height="10" viewBox="0 0 10 10" aria-hidden="true">
      <path d="M0 5 H10" stroke="currentColor" strokeWidth="1" fill="none" />
    </svg>
  );
}
function IconMaximize({ maximized }: { maximized: boolean }) {
  // Maximized = icône "restore" (deux carrés décalés). Normal = un carré.
  return maximized ? (
    <svg width="10" height="10" viewBox="0 0 10 10" aria-hidden="true">
      <rect x="2.5" y="0.5" width="7" height="7" stroke="currentColor" strokeWidth="1" fill="none" />
      <rect x="0.5" y="2.5" width="7" height="7" stroke="currentColor" strokeWidth="1"
        fill="rgba(15,15,18,1)" />
    </svg>
  ) : (
    <svg width="10" height="10" viewBox="0 0 10 10" aria-hidden="true">
      <rect x="0.5" y="0.5" width="9" height="9" stroke="currentColor" strokeWidth="1" fill="none" />
    </svg>
  );
}
function IconClose() {
  return (
    <svg width="10" height="10" viewBox="0 0 10 10" aria-hidden="true">
      <path d="M1 1 L9 9 M9 1 L1 9" stroke="currentColor" strokeWidth="1" fill="none"
        strokeLinecap="square" />
    </svg>
  );
}

// ─── WinButton — rectangle 46×36 plat, hover gris (rouge pour close) ──────
function WinButton({ kind, onClick, ariaLabel, children }: {
  kind: "neutral" | "danger";
  onClick: () => void;
  ariaLabel: string;
  children: React.ReactNode;
}) {
  const [hover, setHover] = useState(false);
  const isDanger = kind === "danger";
  return (
    <button
      aria-label={ariaLabel}
      onClick={onClick}
      onMouseEnter={() => setHover(true)}
      onMouseLeave={() => setHover(false)}
      style={{
        // Pas de border-radius — boutons rectangulaires Windows.
        width: 46, height: 36,
        display: "flex", alignItems: "center", justifyContent: "center",
        padding: 0, cursor: "pointer", border: "none",
        background: hover
          ? (isDanger ? "#E81123" : "rgba(255,255,255,0.08)")
          : "transparent",
        color: hover && isDanger ? "#fff" : "var(--text-1)",
        transition: "background 100ms var(--ease), color 100ms var(--ease)",
      }}>
      {children}
    </button>
  );
}

function ConnectionPill() {
  const c = useStore((s) => s.connection);
  const ok = c.status === "connected";
  return (
    <div style={{
      display: "flex", alignItems: "center", gap: 8,
      padding: "4px 11px 4px 8px",
      borderRadius: 999,
      background: "rgba(255,255,255,0.04)",
      border: "1px solid rgba(255,255,255,0.08)",
    }}>
      <div
        className={ok ? "pulse" : ""}
        style={{
          width: 7, height: 7, borderRadius: "50%",
          background: ok ? "var(--ok)" : "var(--err)",
          boxShadow: `0 0 8px ${ok ? "rgba(48,209,88,0.7)" : "rgba(255,69,58,0.7)"}`,
        }}/>
      <span style={{ fontSize: 11, color: "var(--text-1)", fontWeight: 500 }}>
        {ok ? c.port : "Déconnecté"}
      </span>
      <span className="kd-mono" style={{ fontSize: 9, color: "var(--text-4)" }}>
        {c.baud}
      </span>
    </div>
  );
}

export function TitleBar() {
  const [maximized, setMaximized] = useState(false);

  const onClose    = () => getCurrentWindow().close();
  const onMinimize = () => getCurrentWindow().minimize();
  const onZoom     = async () => {
    const win = getCurrentWindow();
    const isMax = await win.isMaximized();
    if (isMax) await win.unmaximize();
    else       await win.maximize();
    setMaximized(!isMax);
  };

  // Sync l'icône maximize/restore avec l'état réel de la fenêtre
  // (l'user peut maximizer via double-click ou Win+Up).
  useEffect(() => {
    const win = getCurrentWindow();
    let cancelled = false;
    const sync = async () => {
      const m = await win.isMaximized();
      if (!cancelled) setMaximized(m);
    };
    sync();
    const unlisten = win.onResized(() => { sync(); });
    return () => { cancelled = true; unlisten.then((fn) => fn()); };
  }, []);

  // Double-click sur drag region → maximize/restore (comportement OS standard)
  useEffect(() => {
    const onDbl = (e: MouseEvent) => {
      const t = e.target as HTMLElement | null;
      if (t?.closest("[data-tauri-drag-region]")) onZoom();
    };
    window.addEventListener("dblclick", onDbl);
    return () => window.removeEventListener("dblclick", onDbl);
  }, []);

  return (
    <div
      data-tauri-drag-region
      style={{
        position: "relative", zIndex: 30,
        height: 36, flexShrink: 0,
        display: "flex", alignItems: "stretch",
        background: "rgba(15, 15, 18, 0.6)",
        backdropFilter: "blur(20px) saturate(160%)",
        WebkitBackdropFilter: "blur(20px) saturate(160%)",
        borderBottom: "1px solid rgba(255,255,255,0.04)",
        userSelect: "none",
      }}>
      {/* Connection pill à GAUCHE (Windows met les contrôles à droite) */}
      <div
        data-tauri-drag-region
        style={{
          display: "flex", alignItems: "center", paddingLeft: 14,
          zIndex: 1,
        }}>
        <ConnectionPill />
      </div>

      {/* Logo + nom + version — centré absolu (drag region) */}
      <div
        data-tauri-drag-region
        style={{
          position: "absolute", left: "50%", top: "50%",
          transform: "translate(-50%, -50%)",
          display: "flex", alignItems: "center", gap: 8,
          pointerEvents: "none",
        }}>
        <KoreLogo size={18} />
        <span style={{ fontSize: 12, fontWeight: 500, color: "var(--text-2)", letterSpacing: "-0.01em" }}>
          Kore Deck
        </span>
        <span className="kd-mono" style={{ fontSize: 9, color: "var(--text-4)" }}>v2.0.0</span>
      </div>

      {/* Boutons fenêtre Windows — à DROITE, collés au bord (pas de padding) */}
      <div style={{ marginLeft: "auto", display: "flex", zIndex: 2 }}>
        <WinButton kind="neutral" onClick={onMinimize} ariaLabel="Réduire">
          <IconMinimize />
        </WinButton>
        <WinButton kind="neutral" onClick={onZoom}
          ariaLabel={maximized ? "Restaurer" : "Agrandir"}>
          <IconMaximize maximized={maximized} />
        </WinButton>
        <WinButton kind="danger" onClick={onClose} ariaLabel="Fermer">
          <IconClose />
        </WinButton>
      </div>
    </div>
  );
}
