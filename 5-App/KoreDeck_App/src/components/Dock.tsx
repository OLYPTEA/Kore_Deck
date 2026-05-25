// =============================================================================
// Dock.tsx — Segmented control iOS-style avec thumb glissant
// =============================================================================

import { useState } from "react";
import { LayoutGrid, SquareDashed, Users, Settings as SettingsIcon } from "lucide-react";
import type { LucideIcon } from "lucide-react";
import { useStore } from "@/store";

type PageId = "dashboard" | "config" | "profiles" | "settings";

interface DockItem { id: PageId; Icon: LucideIcon; label: string; }

const ITEMS: DockItem[] = [
  { id: "dashboard", Icon: LayoutGrid,   label: "Dashboard"  },
  { id: "config",    Icon: SquareDashed, label: "Boutons"    },
  { id: "profiles",  Icon: Users,        label: "Profils"    },
  { id: "settings",  Icon: SettingsIcon, label: "Paramètres" },
];

// Géométrie du segmented — référencée par le thumb ET les boutons.
// On change ici, tout reste cohérent.
const PADDING  = 8;
const GAP      = 6;
const BTN_SIZE = 44;

function DockButton({ Icon, label, active, onPick }: {
  Icon: LucideIcon; label: string; active: boolean; onPick: () => void;
}) {
  const [hover, setHover] = useState(false);
  return (
    <button
      onClick={onPick}
      onMouseEnter={() => setHover(true)}
      onMouseLeave={() => setHover(false)}
      title={label}
      aria-label={label}
      aria-current={active ? "page" : undefined}
      style={{
        width: BTN_SIZE, height: BTN_SIZE,
        borderRadius: 999,
        // Pas de background propre — c'est le thumb glissant qui s'occupe du surlignage actif.
        // Hover discret uniquement quand le bouton n'est pas actif.
        background: !active && hover ? "rgba(255,255,255,0.06)" : "transparent",
        display: "flex", alignItems: "center", justifyContent: "center",
        position: "relative",   // sits above the absolute thumb
        zIndex: 1,
        transition: "background 180ms var(--ease)",
        cursor: "pointer",
        border: "none",
      }}>
      <Icon
        size={18}
        color={active ? "#1A1A1F" : hover ? "var(--text-1)" : "var(--text-2)"}
        strokeWidth={active ? 2.4 : 2}
        aria-hidden="true"
      />
    </button>
  );
}

export function Dock() {
  const page    = useStore((s) => s.selectedPage);
  const setPage = useStore((s) => s.setPage);

  const activeIndex = ITEMS.findIndex((it) => it.id === page);
  const showThumb   = activeIndex >= 0;

  // Position absolue du thumb dans la pill : padding + (index × (taille + gap))
  // Comme tous les boutons ont la même taille, le thumb glisse d'un cran fixe.
  const thumbLeft = PADDING + activeIndex * (BTN_SIZE + GAP);

  return (
    <div style={{
      position: "fixed", bottom: 22, left: "50%",
      transform: "translateX(-50%)",
      zIndex: 50, pointerEvents: "auto",
    }}>
      <div className="glass" style={{
        position: "relative",
        display: "flex", alignItems: "center", gap: GAP,
        padding: PADDING, borderRadius: 999,
        background: "rgba(20, 20, 25, 0.7)",
        boxShadow: "0 18px 50px rgba(0,0,0,0.55), 0 0 0 0.5px rgba(255,255,255,0.05)",
      }}>
        {/* Thumb glissant — élément absolu qui anime sa position selon activeIndex.
            Posé DERRIÈRE les boutons (zIndex: 0) avec pointer-events: none pour ne
            jamais bloquer les clics. La transition sur `left` fait le glide iOS. */}
        {showThumb && (
          <div
            aria-hidden="true"
            style={{
              position: "absolute",
              top: PADDING, left: thumbLeft,
              width: BTN_SIZE, height: BTN_SIZE,
              borderRadius: 999,
              background:
                "linear-gradient(180deg, rgba(255,255,255,0.96) 0%, rgba(218,218,224,0.88) 100%)",
              boxShadow:
                "0 4px 12px rgba(0,0,0,0.22), " +     // ombre portée
                "0 0 22px rgba(255,255,255,0.12), " + // halo lumineux extérieur
                "inset 0 1px 0 rgba(255,255,255,0.70), " + // reflet du haut
                "inset 0 -1px 0 rgba(0,0,0,0.05)",     // base subtile
              transition: "left 320ms cubic-bezier(0.32, 0.72, 0, 1)",
              pointerEvents: "none",
              zIndex: 0,
            }}
          />
        )}

        {ITEMS.map((it) => (
          <DockButton
            key={it.id}
            Icon={it.Icon}
            label={it.label}
            active={page === it.id}
            onPick={() => setPage(it.id)}
          />
        ))}
      </div>
    </div>
  );
}
