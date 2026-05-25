// =============================================================================
// extras.tsx — Widgets glass restants : Spotify / RAM / FPS / Mic / Pomodoro
//              / DWIN / Pots (+ Dial réutilisable)
// =============================================================================

import { useEffect, useState } from "react";
import {
  Music, Database, Gamepad2, Mic, MicOff, Clock,
  Monitor, SlidersHorizontal, SkipBack, SkipForward, Play, Pause,
  Home, Box, Target,
} from "lucide-react";
import { useStore } from "@/store";
import { CATEGORIES, type CategoryId, type PotConfig } from "@/types";

// Référence stable pour le fallback du sélecteur Zustand de WidgetPots.
// Sans ça, `?? []` retourne un nouvel array à chaque appel → useSyncExternalStore
// détecte un "changement" permanent → boucle infinie → crash React.
const EMPTY_POTS: readonly PotConfig[] = Object.freeze([]);
import { sendAction } from "@/hooks/useSerial";
import { WidgetShell, BigNumber } from "./WidgetShell";
import { getIcon } from "@/lib/icons";

const CAT_ICONS = { Home, Box, Target, Gamepad2 };

// ─── Bar simple ────────────────────────────────────────────────────────────
function Bar({ pct, color = "var(--accent)" }: { pct: number; color?: string }) {
  return (
    <div style={{
      height: 4, borderRadius: 4, background: "rgba(255,255,255,0.08)",
      overflow: "hidden", marginTop: "auto",
    }}>
      <div style={{
        height: "100%", width: `${Math.min(100, Math.max(0, pct))}%`,
        background: color, borderRadius: 4,
        transition: "width 600ms var(--ease)",
        boxShadow: color === "var(--accent)" ? "0 0 8px var(--accent-glow)" : "none",
      }}/>
    </div>
  );
}

// ─── Dial SVG (réutilisé par Pots) ────────────────────────────────────────
export function Dial({ value, max = 100, color = "var(--accent)", size = 42 }: {
  value: number; max?: number; color?: string; size?: number;
}) {
  const pct  = Math.max(0, Math.min(1, value / max));
  const r    = size / 2 - 4;
  const c    = 2 * Math.PI * r;
  const dash = c * 0.78 * pct;
  return (
    <svg width={size} height={size} viewBox={`0 0 ${size} ${size}`} style={{ flexShrink: 0 }}>
      <circle cx={size / 2} cy={size / 2} r={r} fill="none" stroke="rgba(255,255,255,0.08)" strokeWidth="2.5"
        strokeDasharray={`${c * 0.78} ${c}`} transform={`rotate(126 ${size / 2} ${size / 2})`} strokeLinecap="round"/>
      <circle cx={size / 2} cy={size / 2} r={r} fill="none" stroke={color} strokeWidth="2.5"
        strokeDasharray={`${dash} ${c}`} transform={`rotate(126 ${size / 2} ${size / 2})`} strokeLinecap="round"
        style={{ transition: "stroke-dasharray 600ms var(--ease)", filter: `drop-shadow(0 0 4px ${color})` }}/>
    </svg>
  );
}

// =============================================================================
// RAM 2×1
// =============================================================================
export function WidgetRAM() {
  const ram = useStore((s) => s.stats.ram);
  const color = ram > 80 ? "var(--err)" : "var(--accent)";
  return (
    <WidgetShell label="RAM" Icon={Database} dense>
      <div style={{ display: "flex", alignItems: "baseline", justifyContent: "space-between" }}>
        <BigNumber value={ram.toFixed(1)} unit="%" />
        <div className="kd-mono" style={{ fontSize: 9 }}>
          {(ram * 0.32).toFixed(1)} / 32 GB
        </div>
      </div>
      <Bar pct={ram} color={color} />
    </WidgetShell>
  );
}

// =============================================================================
// FPS 1×1
// =============================================================================
export function WidgetFPS() {
  const fps = useStore((s) => s.stats.fps);
  return (
    <WidgetShell label="FPS" Icon={Gamepad2} dense>
      <BigNumber value={fps} />
      <div className="kd-mono" style={{ fontSize: 8, marginTop: "auto", color: "var(--cat-3d)" }}>
        EN JEU
      </div>
    </WidgetShell>
  );
}

// =============================================================================
// Micro 1×1
// =============================================================================
export function WidgetMic() {
  const muted = useStore((s) => s.stats.micMuted);
  return (
    <WidgetShell label="MICRO"
      Icon={muted ? MicOff : Mic}
      accent={muted ? "var(--err)" : "var(--cat-3d)"} dense>
      <div style={{
        fontSize: 16, fontWeight: 600, letterSpacing: "-0.02em",
        color: muted ? "var(--err)" : "var(--text-1)",
        transition: "color 200ms var(--ease)",
      }}>{muted ? "Muté" : "Actif"}</div>
      <div className="kd-mono" style={{ fontSize: 8, marginTop: "auto" }}>SHURE MV7</div>
      <div style={{
        display: "flex", gap: 2, marginTop: 4, alignItems: "flex-end", height: 14,
      }}>
        {[...Array(10)].map((_, i) => (
          <div key={i} style={{
            flex: 1,
            height: muted ? 2 : 5 + (i % 4) * 2,
            background: muted ? "var(--text-4)" : "var(--cat-3d)",
            opacity: muted ? 0.4 : 0.35 + (i / 10) * 0.5,
            borderRadius: 1,
            animation: muted ? "none" : `kd-mic-${i} ${0.4 + (i % 3) * 0.2}s ease-in-out infinite alternate`,
            transition: "height 200ms var(--ease), background 200ms var(--ease)",
          }}/>
        ))}
      </div>
    </WidgetShell>
  );
}

// =============================================================================
// Pomodoro 2×1
// =============================================================================
export function WidgetPomodoro() {
  const s = useStore((s) => s.stats);
  const total = s.pomoMinutes * 60 + s.pomoSeconds;
  const pct = (1 - total / (25 * 60)) * 100;
  return (
    <WidgetShell
      label={`POMODORO · SESSION ${String(s.pomoSession).padStart(2, "0")}`}
      Icon={Clock}
      accent="var(--cat-focus)"
      footer={
        <div style={{
          display: "flex", alignItems: "center", gap: 5,
          padding: "3px 9px", borderRadius: 999,
          background: s.pomoRunning ? "rgba(48, 209, 88, 0.12)" : "rgba(255,255,255,0.06)",
          border: `1px solid ${s.pomoRunning ? "rgba(48, 209, 88, 0.30)" : "var(--glass-border-soft)"}`,
        }}>
          <div className="pulse" style={{
            width: 6, height: 6, borderRadius: "50%",
            background: s.pomoRunning ? "var(--ok)" : "var(--text-4)",
          }}/>
          <span className="kd-mono" style={{
            fontSize: 9,
            color: s.pomoRunning ? "var(--ok)" : "var(--text-3)",
            letterSpacing: "0.1em",
          }}>{s.pomoRunning ? "RUN" : "PAUSE"}</span>
        </div>
      }
    >
      <div style={{ display: "flex", alignItems: "center", gap: 16, marginTop: 2 }}>
        <div className="tnum" style={{
          fontSize: 36, fontWeight: 600, letterSpacing: "-0.04em",
          color: "var(--text-1)", lineHeight: 1,
        }}>
          {String(s.pomoMinutes).padStart(2, "0")}:{String(s.pomoSeconds).padStart(2, "0")}
        </div>
        <div style={{ flex: 1 }}>
          <div className="kd-mono" style={{ fontSize: 9, marginBottom: 4 }}>FOCUS · 25 MIN</div>
          <Bar pct={pct} color="var(--cat-focus)" />
        </div>
      </div>
    </WidgetShell>
  );
}

// =============================================================================
// Spotify 4×2 — branche sendAction sur les contrôles
// =============================================================================
function CtrlButton({ Icon, big = false, onClick, label }: {
  Icon: typeof Play; big?: boolean; onClick: () => void; label: string;
}) {
  const sz = big ? 44 : 34;
  return (
    <button
      aria-label={label}
      onClick={onClick}
      style={{
        width: sz, height: sz, borderRadius: "50%",
        background: big ? "var(--text-1)" : "rgba(255,255,255,0.06)",
        border: big ? "none" : "1px solid var(--glass-border)",
        display: "flex", alignItems: "center", justifyContent: "center",
        transition: "transform var(--d-fast) var(--ease), background var(--d-fast) var(--ease)",
        cursor: "pointer",
      }}
      onMouseDown={(e) => (e.currentTarget.style.transform = "scale(0.92)")}
      onMouseUp={(e) => (e.currentTarget.style.transform = "scale(1)")}
      onMouseLeave={(e) => (e.currentTarget.style.transform = "scale(1)")}>
      <Icon size={big ? 18 : 14} color={big ? "var(--bg-0)" : "var(--text-1)"} strokeWidth={2.2} aria-hidden="true" />
    </button>
  );
}

export function WidgetSpotify() {
  const stats = useStore((s) => s.stats);
  const title = stats.trackTitle || "Aucune lecture";
  const isPlaying = Boolean(stats.trackTitle) && stats.trackTitle !== "Aucune lecture";

  // Progress / duration ne sont pas dans le store — fake ratio pour l'esthétique.
  const pct = 45;

  return (
    <WidgetShell label="EN ÉCOUTE" Icon={Music} accent="var(--cat-3d)">
      <div style={{ display: "flex", gap: 14, alignItems: "stretch", flex: 1, minHeight: 0, minWidth: 0 }}>
        {/* Cover */}
        <div style={{
          height: "100%", aspectRatio: "1/1", flexShrink: 0,
          maxWidth: 130, minWidth: 56,
          borderRadius: 14,
          background: "linear-gradient(135deg, oklch(0.55 0.21 320), oklch(0.45 0.18 250), oklch(0.40 0.16 200))",
          position: "relative", overflow: "hidden",
          boxShadow: "0 10px 30px rgba(0,0,0,0.4), inset 0 1px 0 rgba(255,255,255,0.18)",
        }}>
          <div style={{
            position: "absolute", inset: 0,
            background: "radial-gradient(ellipse 60% 50% at 30% 30%, rgba(255,255,255,0.25), transparent 60%)",
          }}/>
          <div style={{
            position: "absolute", inset: 0,
            display: "flex", alignItems: "center", justifyContent: "center",
            fontFamily: "JetBrains Mono, monospace", fontSize: 9,
            letterSpacing: "0.15em", color: "rgba(255,255,255,0.6)",
          }}>COVER</div>
        </div>

        {/* Colonne droite */}
        <div style={{
          flex: 1, minWidth: 0,
          display: "flex", flexDirection: "column", justifyContent: "space-between",
          gap: 8, paddingTop: 4, paddingBottom: 2,
        }}>
          <div style={{ minWidth: 0 }}>
            <div className="trunc" style={{
              fontSize: "clamp(15px, 1.6vw, 22px)", fontWeight: 600, letterSpacing: "-0.02em",
              color: "var(--text-1)", marginBottom: 3,
            }}>{title}</div>
            <div className="trunc" style={{ fontSize: 12, color: "var(--text-3)" }}>
              {stats.trackArtist || "—"}
            </div>
          </div>

          {/* Scrubber */}
          <div style={{ minWidth: 0 }}>
            <div style={{ position: "relative", height: 4, borderRadius: 4, background: "rgba(255,255,255,0.08)" }}>
              <div style={{
                position: "absolute", left: 0, top: 0, height: "100%",
                width: `${pct}%`, borderRadius: 4,
                background: "linear-gradient(90deg, var(--text-1), var(--text-2))",
              }}/>
              <div style={{
                position: "absolute", left: `calc(${pct}% - 5px)`, top: "50%",
                width: 10, height: 10, borderRadius: "50%", background: "var(--text-1)",
                transform: "translateY(-50%)",
                boxShadow: "0 2px 6px rgba(0,0,0,0.5)",
              }}/>
            </div>
            <div style={{
              display: "flex", justifyContent: "space-between", marginTop: 5,
              fontFamily: "JetBrains Mono, monospace", fontSize: 10, color: "var(--text-3)",
            }}>
              <span className="tnum">—:—</span>
              <span className="tnum">—:—</span>
            </div>
          </div>

          <div style={{ display: "flex", justifyContent: "center", gap: 12 }}>
            <CtrlButton Icon={SkipBack}    label="Précédent"     onClick={() => sendAction("MEDIA_PREV")} />
            <CtrlButton Icon={isPlaying ? Pause : Play} big label="Lecture/Pause" onClick={() => sendAction("MEDIA_PLAY")} />
            <CtrlButton Icon={SkipForward} label="Suivant"       onClick={() => sendAction("MEDIA_NEXT")} />
          </div>
        </div>
      </div>
    </WidgetShell>
  );
}

// =============================================================================
// DWIN Preview 4×2 — segmented control catégorie + 7 boutons
// =============================================================================
export function WidgetDWIN() {
  const activeCat = useStore((s) => s.activeCategoryId);
  const setCat    = useStore((s) => s.setActiveCategory);
  const profile   = useStore((s) => s.profiles.find((p) => p.id === s.activeProfileId));
  const catData   = useStore((s) => {
    const p = s.profiles.find((pp) => pp.id === s.activeProfileId);
    return p?.categories.find((c) => c.categoryId === s.activeCategoryId);
  });
  const cat = CATEGORIES[activeCat];

  return (
    <WidgetShell
      label="ÉCRAN DWIN · 960×240"
      Icon={Monitor}
      footer={
        <div style={{
          display: "flex", gap: 2, padding: 2,
          borderRadius: 999, background: "rgba(255,255,255,0.05)",
          border: "1px solid var(--glass-border-soft)",
          flexShrink: 0,
        }}>
          {CATEGORIES.map((c) => {
            const isActive = c.id === activeCat;
            const Ico = CAT_ICONS[c.icon as keyof typeof CAT_ICONS] || Home;
            const shortLabel = c.name === "3D Making" ? "3D" : c.name;
            return (
              <button key={c.id}
                title={c.name}
                onClick={() => setCat(c.id as CategoryId)}
                style={{
                  padding: isActive ? "4px 9px" : "4px 7px",
                  borderRadius: 999,
                  background: isActive ? c.color : "transparent",
                  color: isActive ? "#fff" : "var(--text-3)",
                  fontSize: 10, fontWeight: 500, letterSpacing: "-0.01em",
                  transition: "all var(--d-fast) var(--ease)",
                  display: "flex", alignItems: "center", gap: 4,
                  whiteSpace: "nowrap", cursor: "pointer",
                }}>
                <Ico size={10} color={isActive ? "#fff" : c.color} aria-hidden="true" />
                {isActive && shortLabel}
              </button>
            );
          })}
        </div>
      }
    >
      {/* Bezel hardware premium — gradient brossé + reflet bord haut + LED rouge ON */}
      <div style={{
        flex: 1,
        background: "linear-gradient(180deg, #25252B 0%, #18181C 38%, #0E0E11 100%)",
        borderRadius: 14,
        padding: 9,
        border: "1px solid rgba(255,255,255,0.06)",
        boxShadow:
          "inset 0 1px 0 rgba(255,255,255,0.10), " +     // reflet bord haut (lumière OS)
          "inset 0 -1px 0 rgba(0,0,0,0.4), " +            // ombre bord bas
          "0 2px 10px rgba(0,0,0,0.45), " +               // ombre portée externe
          "0 0 0 1px rgba(0,0,0,0.3)",                    // séparation nette
        display: "flex", flexDirection: "column",
        marginTop: 6, position: "relative",
      }}>
        {/* LED ON rouge en haut-droite du bezel */}
        <div style={{
          position: "absolute", top: 4, right: 6,
          width: 4, height: 4, borderRadius: "50%",
          background: "#FF453A",
          boxShadow: "0 0 6px rgba(255,69,58,0.85), inset 0 -0.5px 0 rgba(0,0,0,0.3)",
        }}/>

        <div style={{
          flex: 1, borderRadius: 7,
          background:
            "radial-gradient(ellipse 130% 80% at 50% 0%, #0E0E18 0%, #06060A 60%, #030305 100%)",
          padding: 7,
          display: "flex", flexDirection: "column", gap: 5,
          overflow: "hidden", position: "relative",
          boxShadow:
            "inset 0 0 24px rgba(0,0,0,0.65), " +         // vignette intérieure
            "inset 0 1px 2px rgba(0,0,0,0.8)",            // recess top
        }}>
          {/* Scanlines très subtiles (1.5% opacity) pour effet LCD authentique */}
          <div aria-hidden="true" style={{
            position: "absolute", inset: 0,
            background: "repeating-linear-gradient(0deg, " +
              "rgba(255,255,255,0.012) 0 1px, transparent 1px 3px)",
            pointerEvents: "none",
          }}/>

          {/* Header DWIN */}
          <div style={{
            display: "flex", justifyContent: "space-between", alignItems: "center",
            padding: "1px 4px", position: "relative", zIndex: 1,
            fontFamily: "JetBrains Mono, monospace", fontSize: 8,
            color: cat.color, letterSpacing: "0.18em",
            textShadow: `0 0 8px ${cat.color}66`,         // glow néon header
          }}>
            <span>{cat.name.toUpperCase()}</span>
            <span style={{ color: "rgba(255,255,255,0.35)", textShadow: "none" }}>
              KORE · {profile?.name?.toUpperCase() || "—"}
            </span>
          </div>
          <div style={{
            flex: 1, display: "grid", gridTemplateColumns: "repeat(7, 1fr)",
            gap: 4, position: "relative", zIndex: 1,
          }}>
            {catData?.buttons.map((btn) => (
              <DwinButton key={btn.id} btn={btn} />
            ))}
          </div>
        </div>
      </div>
    </WidgetShell>
  );
}

// Bouton DWIN premium — fond avec glow couleur, reflet top, icône avec drop-shadow
function DwinButton({ btn }: { btn: { id: number; icon: string; color: string; label: string } }) {
  const Ico = getIcon(btn.icon);
  return (
    <div style={{
      background: `linear-gradient(180deg, ${btn.color}14 0%, ${btn.color}06 60%, transparent 100%)`,
      border: `1px solid ${btn.color}38`,
      borderRadius: 5,
      display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center",
      gap: 3, padding: "4px 2px", minWidth: 0,
      boxShadow:
        `inset 0 1px 0 ${btn.color}28, ` +                // reflet top color
        `inset 0 -1px 0 rgba(0,0,0,0.3), ` +              // base ombre
        `0 0 8px ${btn.color}18`,                         // halo extérieur soft
      position: "relative", overflow: "hidden",
    }}>
      <Ico size={12} color={btn.color} strokeWidth={2.2} aria-hidden="true"
        style={{ filter: `drop-shadow(0 0 3px ${btn.color}88)` }} />
      <div style={{
        fontFamily: "JetBrains Mono, monospace",
        fontSize: 6.5, color: "rgba(255,255,255,0.7)",
        letterSpacing: "0.08em", textAlign: "center", lineHeight: 1.1,
        overflow: "hidden", textOverflow: "ellipsis",
        whiteSpace: "nowrap", width: "100%",
        textShadow: "0 1px 2px rgba(0,0,0,0.6)",
      }}>{btn.label.toUpperCase()}</div>
    </div>
  );
}

// =============================================================================
// Pots 4×1 — 4 dials physiques de la catégorie active
// =============================================================================
export function WidgetPots() {
  const cat = useStore((s) => CATEGORIES[s.activeCategoryId]);
  const pots = useStore((s) => {
    const p = s.profiles.find((pp) => pp.id === s.activeProfileId);
    return p?.categories.find((c) => c.categoryId === s.activeCategoryId)?.pots ?? EMPTY_POTS;
  });

  // Valeurs live simulées (le store n'a pas de "current value") — purement esthétique
  const [vals, setVals] = useState<number[]>(() => pots.map(() => 50));
  useEffect(() => {
    setVals(pots.map((p) => Math.round((p.min + p.max) / 2)));
  }, [pots.length]);

  return (
    <WidgetShell label={`POTENTIOMÈTRES · ${cat.name.toUpperCase()}`}
      Icon={SlidersHorizontal} accent={cat.color} dense>
      <div style={{
        display: "grid", gridTemplateColumns: "repeat(4, 1fr)",
        gap: 10, flex: 1, alignItems: "center",
      }}>
        {pots.map((pot, i) => (
          <div key={pot.id} style={{ display: "flex", alignItems: "center", gap: 10 }}>
            <Dial value={vals[i] ?? 0} max={pot.max} color={cat.color} size={42} />
            <div style={{ minWidth: 0 }}>
              <div className="trunc" style={{ fontSize: 11, color: "var(--text-2)" }}>{pot.label}</div>
              <div className="tnum kd-mono" style={{ fontSize: 9, color: cat.color }}>
                {vals[i] ?? 0}%
              </div>
            </div>
          </div>
        ))}
      </div>
    </WidgetShell>
  );
}
