// =============================================================================
// PaletteSection.tsx — Sélecteur visuel des 6 palettes (page Paramètres)
// =============================================================================

import { useState } from "react";
import { Check, Palette as PaletteIcon } from "lucide-react";
import { useStore } from "@/store";
import { PALETTE_LIST, PALETTES, type Palette } from "@/lib/palettes";

function Dot({ color }: { color: string }) {
  return (
    <div style={{
      width: 14, height: 14, borderRadius: "50%",
      background: color,
      boxShadow: `0 1px 3px ${color}66, inset 0 1px 0 rgba(255,255,255,0.2)`,
    }}/>
  );
}

function PaletteCard({ palette, active, onPick }: {
  palette: Palette; active: boolean; onPick: () => void;
}) {
  const [hover, setHover] = useState(false);
  return (
    <button
      onClick={onPick}
      onMouseEnter={() => setHover(true)}
      onMouseLeave={() => setHover(false)}
      style={{
        padding: 12,
        borderRadius: "var(--r-md)",
        background: active ? "var(--accent-soft)"
                  : hover  ? "var(--glass-fill)" : "var(--glass-fill-soft)",
        border: active ? "1.5px solid var(--accent)" : "1px solid var(--glass-border-soft)",
        display: "flex", flexDirection: "column", gap: 10,
        textAlign: "left",
        transition: "all 220ms var(--ease)",
        transform: hover && !active ? "translateY(-1px)" : "translateY(0)",
        position: "relative",
        cursor: "pointer",
      }}>
      <div style={{ display: "flex", gap: 6, alignItems: "center", height: 32 }}>
        <div style={{
          width: 32, height: 32, borderRadius: "50%",
          background: `linear-gradient(135deg, ${palette.accent}, ${palette.accent}cc)`,
          boxShadow: `0 4px 12px ${palette.accent}66, inset 0 1px 0 rgba(255,255,255,0.25)`,
          flexShrink: 0,
        }}/>
        <div style={{ display: "flex", flexDirection: "column", gap: 4, flex: 1 }}>
          <div style={{ display: "flex", gap: 4 }}>
            <Dot color={palette.home}/>
            <Dot color={palette["3d"]}/>
          </div>
          <div style={{ display: "flex", gap: 4 }}>
            <Dot color={palette.focus}/>
            <Dot color={palette.game}/>
          </div>
        </div>
      </div>

      <div>
        <div style={{
          fontSize: 13, fontWeight: 600, letterSpacing: "-0.01em",
          color: "var(--text-1)",
        }}>{palette.name}</div>
        <div className="kd-mono" style={{
          fontSize: 8, marginTop: 2,
          color: active ? "var(--accent)" : "var(--text-4)",
        }}>
          {active ? "ACTIVE" : palette.id.toUpperCase()}
        </div>
      </div>

      {active && (
        <div style={{
          position: "absolute", top: 8, right: 8,
          width: 18, height: 18, borderRadius: "50%",
          background: "var(--accent)",
          display: "flex", alignItems: "center", justifyContent: "center",
          boxShadow: "0 2px 6px var(--accent-glow)",
        }}>
          <Check size={10} color="#fff" strokeWidth={3} aria-hidden="true"/>
        </div>
      )}
    </button>
  );
}

export function PaletteSection() {
  const current    = useStore((s) => s.palette);
  const setPalette = useStore((s) => s.setPalette);

  return (
    <div className="glass" style={{
      borderRadius: "var(--r-lg)", padding: 18,
      marginBottom: 12,
    }}>
      <div style={{
        display: "flex", alignItems: "center", justifyContent: "space-between",
        marginBottom: 14, position: "relative", zIndex: 1,
      }}>
        <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
          <PaletteIcon size={13} color="var(--accent)" aria-hidden="true"/>
          <span className="kd-mono" style={{ color: "var(--text-2)", letterSpacing: "0.14em" }}>
            APPARENCE · PALETTE
          </span>
        </div>
        <span style={{ fontSize: 12, color: "var(--text-3)" }}>
          {(PALETTES[current] || PALETTES.default).name}
        </span>
      </div>
      <div style={{
        display: "grid", gridTemplateColumns: "repeat(3, 1fr)",
        gap: 10, position: "relative", zIndex: 1,
      }}>
        {PALETTE_LIST.map((p) => (
          <PaletteCard key={p.id} palette={p}
            active={p.id === current}
            onPick={() => setPalette(p.id)} />
        ))}
      </div>
    </div>
  );
}
