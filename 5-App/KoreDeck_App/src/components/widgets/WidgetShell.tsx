// =============================================================================
// WidgetShell.tsx — Coque commune (label mono + corps) pour les widgets glass
// =============================================================================

import { useEffect, useRef, useState } from "react";
import type { LucideIcon } from "lucide-react";

interface ShellProps {
  label:    string;
  Icon?:    LucideIcon;
  accent?:  string;
  dense?:   boolean;
  footer?:  React.ReactNode;
  children: React.ReactNode;
}

// Pattern repris de ProfileCard : mouse tracking + hover lift + glow overlay.
// Optimisations perf :
//   - onMouseMove throttle via rAF (1 update/frame max au lieu d'une par event)
//   - getBoundingClientRect caché tant que la souris n'est pas relâchée
//   - cleanup du rAF au unmount pour éviter callbacks orphelins
export function WidgetShell({ label, Icon, accent, dense = false, footer, children }: ShellProps) {
  const ref = useRef<HTMLDivElement>(null);
  const [hover, setHover] = useState(false);
  const rafRef     = useRef<number | null>(null);
  const lastEvtRef = useRef<{ x: number; y: number } | null>(null);
  const rectRef    = useRef<DOMRect | null>(null);

  function onMouseEnter() {
    setHover(true);
    // Cache le rect au moment du hover — pas de getBoundingClientRect
    // dans la hot path du mousemove (force un reflow).
    if (ref.current) rectRef.current = ref.current.getBoundingClientRect();
  }
  function onMouseLeave() {
    setHover(false);
    rectRef.current = null;
    if (rafRef.current !== null) {
      cancelAnimationFrame(rafRef.current);
      rafRef.current = null;
    }
  }

  function onMouseMove(e: React.MouseEvent<HTMLDivElement>) {
    lastEvtRef.current = { x: e.clientX, y: e.clientY };
    if (rafRef.current !== null) return; // déjà une frame en attente
    rafRef.current = requestAnimationFrame(() => {
      rafRef.current = null;
      const el = ref.current;
      const r  = rectRef.current;
      const ev = lastEvtRef.current;
      if (!el || !r || !ev) return;
      const x = ((ev.x - r.left) / r.width)  * 100;
      const y = ((ev.y - r.top)  / r.height) * 100;
      el.style.setProperty("--rx", x.toFixed(1) + "%");
      el.style.setProperty("--ry", y.toFixed(1) + "%");
    });
  }

  // Cleanup au unmount
  useEffect(() => {
    return () => {
      if (rafRef.current !== null) cancelAnimationFrame(rafRef.current);
    };
  }, []);

  return (
    <div
      ref={ref}
      onMouseMove={onMouseMove}
      onMouseEnter={onMouseEnter}
      onMouseLeave={onMouseLeave}
      className="glass"
      style={{
        position: "relative", overflow: "hidden",
        width: "100%", height: "100%",
        borderRadius: "var(--r-lg)",
        padding: dense ? 10 : 13,    // -3px par côté (vs 12/16) → +6px utiles par cellule
        display: "flex", flexDirection: "column", gap: dense ? 5 : 8,
        minHeight: 0,
        // Lift au hover (comme ProfileCard) — transition transform/shadow ciblée.
        transform: hover ? "translateY(-2px)" : "translateY(0)",
        boxShadow: hover
          ? "0 14px 36px rgba(0,0,0,0.45), inset 0 1px 0 rgba(255,255,255,0.08)"
          : "var(--glass-shadow)",
        transition: "transform 200ms var(--ease), box-shadow 200ms var(--ease)",
      }}>
      {/* Glow radial qui suit la souris — opacity pilotée par state React,
          --rx/--ry posés par onMouseMove. Aucun `:hover` CSS impliqué donc
          aucune race condition possible avec le premier mousemove. */}
      <div
        aria-hidden="true"
        style={{
          position: "absolute", inset: 0,
          background:
            "radial-gradient(ellipse 60% 80% at var(--rx, 50%) var(--ry, 50%)," +
            " rgba(255,255,255,0.08), transparent 60%)",
          opacity: hover ? 1 : 0,
          transition: "opacity 200ms var(--ease)",
          pointerEvents: "none",
        }}
      />

      <div style={{
        position: "relative", zIndex: 1,
        display: "flex", alignItems: "center", justifyContent: "space-between", gap: 8,
      }}>
        <div className="kd-mono" style={{ display: "flex", alignItems: "center", gap: 6 }}>
          {Icon && <Icon size={11} color={accent || "currentColor"} aria-hidden="true" />}
          <span>{label}</span>
        </div>
        {footer}
      </div>
      <div style={{
        position: "relative", zIndex: 1,
        flex: 1, minHeight: 0, display: "flex", flexDirection: "column",
      }}>
        {children}
      </div>
    </div>
  );
}

export function BigNumber({ value, unit, color = "var(--text-1)", size = "lg" }: {
  value: string | number; unit?: string; color?: string; size?: "sm" | "md" | "lg";
}) {
  const fs = size === "sm" ? "clamp(18px, 1.6vw, 24px)"
           : size === "md" ? "clamp(20px, 1.9vw, 28px)"
           :                  "clamp(22px, 2.1vw, 32px)";
  return (
    <div className="tnum" style={{
      fontSize: fs, fontWeight: 600,
      letterSpacing: "-0.035em", lineHeight: 1, color,
      display: "flex", alignItems: "baseline", gap: 2,
    }}>
      <span>{value}</span>
      {unit && <span style={{ fontSize: "0.42em", fontWeight: 500, color: "var(--text-3)", marginLeft: 2 }}>{unit}</span>}
    </div>
  );
}
