// =============================================================================
// Config.tsx — Page "Boutons" : tuiles glass + potards + DWIN preview
// =============================================================================

import { useEffect, useState } from "react";
import { useStore } from "@/store";
import { type ButtonConfig, type CategoryId, CATEGORIES, type PotConfig } from "@/types";
import { ButtonEditModal } from "@/components/ButtonEditModal";
import { PageHeader } from "@/components/PageHeader";
import { NamedIcon, getIcon } from "@/lib/icons";
import { Monitor } from "lucide-react";
import { Dial } from "@/components/widgets/extras";

const ACTION_LABELS: Record<string, string> = {
  shortcut: "Raccourci clavier",
  app:      "Lancer une app",
  script:   "Exécuter un script",
  macro:    "Macro multi-étapes",
  system:   "Action système",
};

// ─── Segmented control catégories ────────────────────────────────────────
function CategorySegmented({ active, onChange }: {
  active: CategoryId; onChange: (id: CategoryId) => void;
}) {
  return (
    <div style={{
      display: "flex", gap: 4, padding: 4,
      background: "var(--glass-fill)",
      backdropFilter: "var(--glass-blur-light)",
      WebkitBackdropFilter: "var(--glass-blur-light)",
      border: "1px solid var(--glass-border)",
      borderRadius: 999,
    }}>
      {CATEGORIES.map((c) => {
        const isActive = c.id === active;
        return (
          <button key={c.id}
            onClick={() => onChange(c.id as CategoryId)}
            style={{
              display: "flex", alignItems: "center", gap: 6,
              padding: "8px 14px", borderRadius: 999,
              background: isActive ? c.color : "transparent",
              color: isActive ? "#fff" : "var(--text-2)",
              fontSize: 13, fontWeight: 500, letterSpacing: "-0.01em",
              transition: "background 220ms var(--ease), color 220ms var(--ease), box-shadow 220ms var(--ease)",
              boxShadow: isActive
                ? `0 4px 14px ${c.color}55, inset 0 1px 0 rgba(255,255,255,0.22)`
                : "none",
              cursor: "pointer",
            }}>
            <NamedIcon name={c.icon} size={13}
              color={isActive ? "#fff" : c.color} strokeWidth={2.2} />
            {c.name}
          </button>
        );
      })}
    </div>
  );
}

// ─── ButtonTile — grosse tuile cliquable ─────────────────────────────────
function ButtonTile({ btn, catColor, onClick }: {
  btn: ButtonConfig; catColor: string; onClick: () => void;
}) {
  const [hover, setHover] = useState(false);
  return (
    <button onClick={onClick}
      onMouseEnter={() => setHover(true)}
      onMouseLeave={() => setHover(false)}
      style={{
        aspectRatio: "1 / 1.08",
        borderRadius: "var(--r-lg)",
        background: "var(--glass-fill)",
        backdropFilter: "var(--glass-blur)",
        WebkitBackdropFilter: "var(--glass-blur)",
        border: "1px solid var(--glass-border)",
        padding: 16,
        display: "flex", flexDirection: "column",
        alignItems: "flex-start", justifyContent: "space-between",
        position: "relative", overflow: "hidden",
        textAlign: "left", color: "var(--text-1)",
        transition: "transform 200ms var(--ease), box-shadow 200ms var(--ease)",
        transform: hover ? "translateY(-3px)" : "translateY(0)",
        boxShadow: hover
          ? `0 14px 36px rgba(0,0,0,0.55), 0 0 0 1px ${btn.color}55, inset 0 1px 0 rgba(255,255,255,0.12)`
          : "0 4px 14px rgba(0,0,0,0.3), inset 0 1px 0 rgba(255,255,255,0.06)",
        cursor: "pointer",
      }}>
      {/* Radial glow couleur de la catégorie en BAS de la tuile.
          opacity 0 au repos (sinon bande lumineuse permanente visible),
          0.8 au hover pour l'effet "qui s'allume" quand on survole. */}
      <div style={{
        position: "absolute", inset: 0,
        background: `radial-gradient(ellipse 70% 50% at 50% 100%, ${btn.color}33, transparent 60%)`,
        opacity: hover ? 0.8 : 0,
        transition: "opacity var(--d-base) var(--ease)",
        pointerEvents: "none",
      }}/>

      <div style={{ position: "relative", zIndex: 1, width: "100%" }}>
        <div className="kd-mono" style={{ fontSize: 9, color: catColor }}>
          BTN · {String(btn.id + 1).padStart(2, "0")}
        </div>
      </div>

      <div style={{
        width: 52, height: 52, borderRadius: 14,
        background: `linear-gradient(135deg, ${btn.color}, ${btn.color}88)`,
        display: "flex", alignItems: "center", justifyContent: "center",
        boxShadow: `0 6px 18px ${btn.color}55, inset 0 1px 0 rgba(255,255,255,0.25)`,
        position: "relative", zIndex: 1, alignSelf: "center",
      }}>
        <NamedIcon name={btn.icon} size={26} color="#fff" strokeWidth={2.2} />
      </div>

      <div style={{ position: "relative", zIndex: 1, width: "100%", minWidth: 0 }}>
        <div className="trunc" style={{
          fontSize: 13, fontWeight: 600, letterSpacing: "-0.01em", marginBottom: 3,
        }}>{btn.label}</div>
        <div className="kd-mono" style={{ fontSize: 9, color: "var(--text-3)" }}>
          {ACTION_LABELS[btn.action.type] || btn.action.type}
        </div>
        <div style={{
          marginTop: 6, padding: "3px 6px", borderRadius: 5,
          background: "var(--glass-fill-soft)",
          border: "1px solid var(--glass-border-soft)",
          fontFamily: "JetBrains Mono, monospace", fontSize: 10,
          color: "var(--text-2)", display: "inline-block",
          maxWidth: "100%", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap",
        }}>{btn.action.value}</div>
      </div>
    </button>
  );
}

// ─── PotCard ─────────────────────────────────────────────────────────────
function PotCard({ pot, catColor, value }: {
  pot: PotConfig; catColor: string; value: number;
}) {
  return (
    <div style={{
      padding: 16, borderRadius: "var(--r-md)",
      background: "var(--glass-fill-soft)",
      border: "1px solid var(--glass-border-soft)",
      display: "flex", gap: 14, alignItems: "center",
    }}>
      <Dial value={value} max={pot.max} color={catColor} size={64} />
      <div style={{ flex: 1, minWidth: 0 }}>
        <div className="kd-mono" style={{ color: catColor, fontSize: 9 }}>
          POT · {String(pot.id + 1).padStart(2, "0")}
        </div>
        <div style={{
          fontSize: 15, fontWeight: 600, marginTop: 2, letterSpacing: "-0.01em",
        }}>{pot.label}</div>
        <div style={{
          marginTop: 6, display: "flex", gap: 6, alignItems: "center",
          fontFamily: "JetBrains Mono, monospace", fontSize: 10, color: "var(--text-3)",
        }}>
          <span>{pot.min}</span>
          <div style={{
            flex: 1, height: 2, background: "rgba(255,255,255,0.08)",
            borderRadius: 2, position: "relative",
          }}>
            <div style={{
              position: "absolute", left: 0, height: "100%",
              background: catColor, borderRadius: 2,
              width: `${((value - pot.min) / Math.max(1, pot.max - pot.min)) * 100}%`,
            }}/>
          </div>
          <span>{pot.max}</span>
        </div>
        <div className="tnum" style={{
          fontSize: 11, color: "var(--text-2)", marginTop: 4,
        }}>{pot.action.replace(/_/g, " ")}</div>
      </div>
    </div>
  );
}

// ─── DWIN sticky preview ─────────────────────────────────────────────────
function DwinSticky({ buttons }: { buttons: ButtonConfig[] }) {
  return (
    <div className="glass" style={{
      borderRadius: "var(--r-lg)", padding: 16,
      display: "flex", flexDirection: "column", gap: 10,
    }}>
      <div className="kd-mono" style={{
        display: "flex", alignItems: "center", gap: 6, position: "relative", zIndex: 1,
      }}>
        <Monitor size={11} color="var(--accent)" aria-hidden="true" />
        APERÇU LIVE · ÉCRAN DWIN
      </div>
      {/* Bezel premium harmonisé avec WidgetDWIN du Dashboard */}
      <div style={{
        background: "linear-gradient(180deg, #25252B 0%, #18181C 38%, #0E0E11 100%)",
        borderRadius: 14, padding: 10,
        border: "1px solid rgba(255,255,255,0.06)",
        boxShadow:
          "inset 0 1px 0 rgba(255,255,255,0.10), " +
          "inset 0 -1px 0 rgba(0,0,0,0.4), " +
          "0 2px 10px rgba(0,0,0,0.45)",
        aspectRatio: "960 / 240",
        position: "relative", zIndex: 1,
      }}>
        {/* LED ON rouge */}
        <div style={{
          position: "absolute", top: 5, right: 8,
          width: 5, height: 5, borderRadius: "50%",
          background: "#FF453A",
          boxShadow: "0 0 7px rgba(255,69,58,0.85), inset 0 -0.5px 0 rgba(0,0,0,0.3)",
        }}/>
        <div style={{
          width: "100%", height: "100%", borderRadius: 7,
          background:
            "radial-gradient(ellipse 130% 80% at 50% 0%, #0E0E18 0%, #06060A 60%, #030305 100%)",
          padding: 7, display: "grid", gridTemplateColumns: "repeat(7, 1fr)", gap: 5,
          position: "relative", overflow: "hidden",
          boxShadow:
            "inset 0 0 24px rgba(0,0,0,0.65), " +
            "inset 0 1px 2px rgba(0,0,0,0.8)",
        }}>
          {/* Scanlines */}
          <div aria-hidden="true" style={{
            position: "absolute", inset: 0,
            background: "repeating-linear-gradient(0deg, " +
              "rgba(255,255,255,0.012) 0 1px, transparent 1px 3px)",
            pointerEvents: "none",
          }}/>
          {buttons.map((b) => {
            const Ico = getIcon(b.icon);
            return (
              <div key={b.id} style={{
                background: `linear-gradient(180deg, ${b.color}14 0%, ${b.color}06 60%, transparent 100%)`,
                border: `1px solid ${b.color}38`,
                borderRadius: 6,
                display: "flex", flexDirection: "column",
                alignItems: "center", justifyContent: "center", gap: 4,
                boxShadow:
                  `inset 0 1px 0 ${b.color}28, ` +
                  `inset 0 -1px 0 rgba(0,0,0,0.3), ` +
                  `0 0 8px ${b.color}18`,
                position: "relative", zIndex: 1, overflow: "hidden",
              }}>
                <Ico size={16} color={b.color} strokeWidth={2.2} aria-hidden="true"
                  style={{ filter: `drop-shadow(0 0 4px ${b.color}88)` }} />
                <div style={{
                  fontFamily: "JetBrains Mono, monospace",
                  fontSize: 8, color: "rgba(255,255,255,0.7)",
                  letterSpacing: "0.06em", textAlign: "center",
                  padding: "0 2px", lineHeight: 1.1,
                  textShadow: "0 1px 2px rgba(0,0,0,0.6)",
                }}>{b.label.toUpperCase()}</div>
              </div>
            );
          })}
        </div>
      </div>

      <div className="kd-mono" style={{
        display: "flex", alignItems: "center", gap: 6,
        color: "var(--ok)", marginTop: 4, position: "relative", zIndex: 1,
      }}>
        <div className="pulse" style={{
          width: 6, height: 6, borderRadius: "50%", background: "var(--ok)",
        }}/>
        SYNCHRONISÉ · COM3
      </div>
    </div>
  );
}

// ─── Page ────────────────────────────────────────────────────────────────
export function Config() {
  const activeCategoryId = useStore((s) => s.activeCategoryId);
  const setCategory      = useStore((s) => s.setActiveCategory);
  const profiles         = useStore((s) => s.profiles);
  const activeProfileId  = useStore((s) => s.activeProfileId);
  const setActiveProfile = useStore((s) => s.setActiveProfile);

  const categoryData = useStore((s) => {
    const p = s.profiles.find((pp) => pp.id === s.activeProfileId);
    return p?.categories.find((c) => c.categoryId === s.activeCategoryId);
  });

  const [editing, setEditing] = useState<ButtonConfig | null>(null);
  const cat = CATEGORIES[activeCategoryId];

  // Auto-recovery : si le state persisté pointe vers un profil/catégorie qui
  // n'existe plus (corruption après crash), on rebascule sur un état valide.
  // Sans ça, la page retournait `null` → écran vide silencieux.
  useEffect(() => {
    if (categoryData) return;
    const profileExists = profiles.some((p) => p.id === activeProfileId);
    if (!profileExists && profiles.length > 0) {
      setActiveProfile(profiles[0].id);
    }
    if (activeCategoryId !== 0) setCategory(0);
  }, [categoryData, profiles, activeProfileId, activeCategoryId, setActiveProfile, setCategory]);

  if (!categoryData) {
    return (
      <div style={{ display: "flex", flexDirection: "column", height: "100%" }}>
        <PageHeader title="Boutons" subtitle="Restauration de la configuration…" />
        <div style={{
          flex: 1, display: "flex", alignItems: "center", justifyContent: "center",
          color: "var(--text-3)", fontSize: 12,
        }}>
          <span className="kd-mono">REINITIALISATION DE L'ETAT</span>
        </div>
      </div>
    );
  }

  return (
    <div style={{ display: "flex", flexDirection: "column", height: "100%", overflow: "hidden" }}>
      <PageHeader
        title="Boutons"
        subtitle={`Configure les 7 boutons et 4 potentiomètres de la catégorie ${cat.name}.`}
        right={<CategorySegmented active={activeCategoryId} onChange={setCategory} />}
      />

      <div style={{
        flex: 1, minHeight: 0,
        overflowY: "auto", overflowX: "hidden",
        padding: "0 28px 110px",
      }}>
        {/* 7 tuiles */}
        <div style={{
          display: "grid", gridTemplateColumns: "repeat(7, 1fr)",
          gap: 14, marginBottom: 24,
        }}>
          {categoryData.buttons.map((btn) => (
            <ButtonTile key={btn.id} btn={btn} catColor={cat.color}
              onClick={() => setEditing(btn)} />
          ))}
        </div>

        {/* Pots + DWIN */}
        <div style={{ display: "grid", gridTemplateColumns: "1.4fr 1fr", gap: 14 }}>
          <div className="glass" style={{ borderRadius: "var(--r-lg)", padding: 20 }}>
            <div style={{
              display: "flex", alignItems: "center", justifyContent: "space-between",
              marginBottom: 16, position: "relative", zIndex: 1,
            }}>
              <div>
                <div className="kd-mono">POTENTIOMÈTRES</div>
                <div style={{
                  fontSize: 18, fontWeight: 600, letterSpacing: "-0.02em", marginTop: 2,
                }}>4 dials physiques</div>
              </div>
              <span className="kd-mono" style={{ color: cat.color }}>
                {cat.name.toUpperCase()}
              </span>
            </div>

            <div style={{
              display: "grid", gridTemplateColumns: "repeat(2, 1fr)",
              gap: 14, position: "relative", zIndex: 1,
            }}>
              {categoryData.pots.map((pot) => (
                <PotCard key={pot.id} pot={pot} catColor={cat.color}
                  value={Math.round((pot.min + pot.max) / 2)} />
              ))}
            </div>
          </div>

          <DwinSticky buttons={categoryData.buttons} />
        </div>
      </div>

      {editing && <ButtonEditModal button={editing} catColor={cat.color} onClose={() => setEditing(null)} />}
    </div>
  );
}
