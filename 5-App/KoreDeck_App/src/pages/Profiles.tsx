// =============================================================================
// Profiles.tsx — Liste glass des profils + side-sheet (sans drag&drop)
// =============================================================================

import { useState, type CSSProperties } from "react";
import * as LucideIcons from "lucide-react";
import {
  Plus, Download, Copy, Share, Trash2, X,
  type LucideIcon,
} from "lucide-react";
import { useStore } from "@/store";
import { CATEGORIES, type Profile } from "@/types";
import { PageHeader } from "@/components/PageHeader";

// Couleurs de swatch cyclées par id de profil (le store n'a pas de swatchKey)
const SWATCHES_HEX = ["#5E5CE6", "#30D158", "#FF9F0A", "#FF453A"];
function swatchHex(id: number): string {
  return SWATCHES_HEX[Math.abs(id) % SWATCHES_HEX.length];
}

function getLucideIcon(name: string): LucideIcon {
  return (LucideIcons as unknown as Record<string, LucideIcon>)[name] ?? LucideIcons.Square;
}

// ─────────────────────────────────────────────────────────────────────────────
// CircleAction
// ─────────────────────────────────────────────────────────────────────────────
function CircleAction({
  Icon, label, danger = false, onClick,
}: {
  Icon: LucideIcon;
  label: string;
  danger?: boolean;
  onClick?: () => void;
}) {
  const [hover, setHover] = useState(false);
  return (
    <button
      title={label} aria-label={label}
      onClick={(e) => { e.stopPropagation(); onClick?.(); }}
      onMouseEnter={() => setHover(true)}
      onMouseLeave={() => setHover(false)}
      style={{
        width: 36, height: 36, borderRadius: "50%",
        background: hover
          ? (danger ? "rgba(255,69,58,0.16)" : "var(--glass-fill-strong)")
          : "var(--glass-fill-soft)",
        border: `1px solid ${hover
          ? (danger ? "rgba(255,69,58,0.4)" : "var(--glass-border)")
          : "var(--glass-border-soft)"}`,
        display: "flex", alignItems: "center", justifyContent: "center",
        transition: "background 160ms var(--ease), border-color 160ms var(--ease)",
        cursor: "pointer",
      }}
    >
      <Icon size={14}
        color={hover && danger ? "var(--err)" : "var(--text-2)"}
        aria-hidden="true" />
    </button>
  );
}

// ─────────────────────────────────────────────────────────────────────────────
// NewProfileCard
// ─────────────────────────────────────────────────────────────────────────────
function NewProfileCard({ onClick }: { onClick: () => void }) {
  const [hover, setHover] = useState(false);
  return (
    <button
      onClick={onClick}
      onMouseEnter={() => setHover(true)}
      onMouseLeave={() => setHover(false)}
      style={{
        padding: "26px 22px",
        borderRadius: "var(--r-lg)",
        border: `1.5px dashed ${hover ? "var(--accent)" : "rgba(255,255,255,0.16)"}`,
        background: hover ? "var(--accent-soft)" : "transparent",
        display: "flex", alignItems: "center", gap: 16,
        color: "var(--text-2)",
        transition: "background 200ms var(--ease), border-color 200ms var(--ease)",
        cursor: "pointer",
      }}
    >
      <div style={{
        width: 44, height: 44, borderRadius: 12,
        background: "var(--glass-fill)",
        border: "1px solid var(--glass-border)",
        display: "flex", alignItems: "center", justifyContent: "center",
        flexShrink: 0,
      }}>
        <Plus size={20} color="var(--accent)" strokeWidth={2.5} aria-hidden="true" />
      </div>
      <div style={{ textAlign: "left", flex: 1, minWidth: 0 }}>
        <div style={{
          fontSize: 15, fontWeight: 600,
          color: "var(--text-1)", letterSpacing: "-0.01em",
        }}>Nouveau profil</div>
        <div style={{ fontSize: 12, color: "var(--text-3)", marginTop: 2 }}>
          Démarre depuis zéro ou duplique un profil existant.
        </div>
      </div>
    </button>
  );
}

// ─────────────────────────────────────────────────────────────────────────────
// ProfileCard
// ─────────────────────────────────────────────────────────────────────────────
function ProfileCard({
  profile, onOpen, onActivate, onDuplicate, onExport, onDelete, canDelete,
}: {
  profile: Profile;
  onOpen:      () => void;
  onActivate:  () => void;
  onDuplicate: () => void;
  onExport:    () => void;
  onDelete:    () => void;
  canDelete:   boolean;
}) {
  const [hover, setHover] = useState(false);
  useStore((s) => s.palette); // re-render quand la palette change
  const sw = swatchHex(profile.id);

  // Note : pas de onMouseMove ici — la délégation globale dans App.tsx
  // (useGlassMouseTracking) pose --rx/--ry sur tout `.glass` automatiquement.
  return (
    <div
      onMouseEnter={() => setHover(true)}
      onMouseLeave={() => setHover(false)}
      onClick={onOpen}
      className="glass"
      style={{
        position: "relative",
        padding: 18,
        borderRadius: "var(--r-lg)",
        display: "flex", alignItems: "center", gap: 18,
        cursor: "pointer",
        transition: "transform 200ms var(--ease), box-shadow 200ms var(--ease)",
        transform: hover ? "translateY(-2px)" : "translateY(0)",
        boxShadow: hover ? "0 14px 36px rgba(0,0,0,0.45)" : "var(--glass-shadow)",
        overflow: "hidden",
      }}
    >
      {/* Highlight radial qui suit la souris */}
      <div style={{
        position: "absolute", inset: 0,
        background: "radial-gradient(ellipse 60% 80% at var(--rx, 50%) var(--ry, 50%), rgba(255,255,255,0.08), transparent 60%)",
        opacity: hover ? 1 : 0,
        transition: "opacity 200ms var(--ease)",
        pointerEvents: "none",
      }}/>

      {/* Avatar */}
      <div style={{
        width: 52, height: 52, borderRadius: 14, flexShrink: 0,
        background: `linear-gradient(135deg, ${sw}, ${sw}88)`,
        display: "flex", alignItems: "center", justifyContent: "center",
        color: "#fff", fontWeight: 700, fontSize: 20, letterSpacing: "-0.02em",
        boxShadow: `0 6px 18px ${sw}55, inset 0 1px 0 rgba(255,255,255,0.25)`,
        position: "relative", zIndex: 1,
      }}>
        {profile.name[0]?.toUpperCase() || "?"}
      </div>

      <div style={{ flex: 1, minWidth: 0, position: "relative", zIndex: 1 }}>
        <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 4 }}>
          <span className="trunc" style={{
            fontSize: 16, fontWeight: 600, letterSpacing: "-0.02em",
          }}>{profile.name}</span>
          {profile.isActive && (
            <span style={{
              fontFamily: "JetBrains Mono, ui-monospace, monospace", fontSize: 9,
              padding: "2px 8px", borderRadius: 999,
              background: "rgba(48, 209, 88, 0.16)",
              color: "var(--ok)",
              border: "1px solid rgba(48, 209, 88, 0.30)",
              letterSpacing: "0.1em", flexShrink: 0,
            }}>ACTIF</span>
          )}
        </div>
        <div className="trunc" style={{ fontSize: 13, color: "var(--text-3)" }}>
          {profile.description || "Profil personnalisé"}
        </div>
        <div className="kd-mono" style={{
          fontSize: 9, marginTop: 6, color: "var(--text-3)",
        }}>
          MAJ · {new Date(profile.updatedAt).toLocaleString("fr-FR", {
            day: "2-digit", month: "short", hour: "2-digit", minute: "2-digit",
          }).toUpperCase()}
        </div>
      </div>

      <div style={{
        display: "flex", gap: 6,
        position: "relative", zIndex: 1, flexShrink: 0,
      }}>
        <CircleAction Icon={Download} label="Charger"   onClick={onActivate} />
        <CircleAction Icon={Copy}     label="Dupliquer" onClick={onDuplicate} />
        <CircleAction Icon={Share}    label="Exporter"  onClick={onExport} />
        <CircleAction Icon={Trash2}   label="Supprimer" danger
          onClick={() => canDelete && onDelete()} />
      </div>
    </div>
  );
}

// ─────────────────────────────────────────────────────────────────────────────
// ProfileSideSheet — Slide-in à droite
// ─────────────────────────────────────────────────────────────────────────────
function ProfileSideSheet({
  profile, onClose, onActivate, onDuplicate,
}: {
  profile: Profile | undefined;
  onClose:     () => void;
  onActivate:  () => void;
  onDuplicate: () => void;
}) {
  useStore((s) => s.palette);
  const open = !!profile;
  const sw = profile ? swatchHex(profile.id) : "#5E5CE6";

  const overlayStyle: CSSProperties = {
    position: "absolute", inset: 0,
    // Scrim renforcé pour isoler le side-sheet des cards profils en arrière-plan
    // (lisibilité signalée). 0.55 → 0.72 + blur 8 → 22px.
    background: open ? "rgba(0,0,0,0.72)" : "transparent",
    backdropFilter: open ? "blur(22px) saturate(140%)" : "none",
    WebkitBackdropFilter: open ? "blur(22px) saturate(140%)" : "none",
    opacity: open ? 1 : 0,
    transition: "opacity 240ms var(--ease)",
  };

  return (
    <div
      role="dialog" aria-modal="true" aria-hidden={!open}
      style={{
        position: "fixed", inset: 0,
        pointerEvents: open ? "auto" : "none",
        zIndex: 100,
      }}
    >
      <div onClick={onClose} style={overlayStyle} />

      <div className="glass glass-strong" style={{
        position: "absolute", top: 0, right: 0, bottom: 0,
        width: 440, maxWidth: "92vw",
        borderRadius: "var(--r-xl) 0 0 var(--r-xl)",
        padding: 24,
        transform: open ? "translateX(0)" : "translateX(110%)",
        transition: "transform 360ms var(--ease)",
        display: "flex", flexDirection: "column", gap: 16,
        overflowY: "auto",
        boxShadow: "-30px 0 60px rgba(0,0,0,0.4)",
      }}>
        {profile && (
          <>
            <div style={{ display: "flex", alignItems: "center", gap: 14 }}>
              <div style={{
                width: 56, height: 56, borderRadius: 16, flexShrink: 0,
                background: `linear-gradient(135deg, ${sw}, ${sw}88)`,
                display: "flex", alignItems: "center", justifyContent: "center",
                color: "#fff", fontWeight: 700, fontSize: 22,
                boxShadow: `0 6px 18px ${sw}55, inset 0 1px 0 rgba(255,255,255,0.25)`,
              }}>{profile.name[0]?.toUpperCase() || "?"}</div>

              <div style={{ flex: 1, minWidth: 0 }}>
                <div className="trunc" style={{
                  fontSize: 22, fontWeight: 600, letterSpacing: "-0.025em",
                }}>{profile.name}</div>
                <div className="trunc" style={{
                  fontSize: 12, color: "var(--text-3)", marginTop: 2,
                }}>{profile.description || "Profil personnalisé"}</div>
              </div>

              <button
                onClick={onClose} aria-label="Fermer"
                style={{
                  width: 32, height: 32, borderRadius: "50%",
                  background: "var(--glass-fill)",
                  border: "1px solid var(--glass-border)",
                  display: "flex", alignItems: "center", justifyContent: "center",
                  cursor: "pointer", flexShrink: 0,
                }}
              >
                <X size={14} color="var(--text-2)" aria-hidden="true" />
              </button>
            </div>

            {/* ── Aperçu par catégorie ── */}
            {CATEGORIES.map((c) => {
              const catConfig = profile.categories.find((pc) => pc.categoryId === c.id);
              const buttons = catConfig?.buttons ?? [];
              const pots    = catConfig?.pots    ?? [];
              const CatIcon = getLucideIcon(c.icon);
              return (
                <div key={c.id} style={{
                  padding: 14, borderRadius: "var(--r-md)",
                  background: "var(--glass-fill-soft)",
                  border: "1px solid var(--glass-border-soft)",
                }}>
                  <div style={{
                    display: "flex", alignItems: "center", gap: 8, marginBottom: 10,
                  }}>
                    <CatIcon size={14} color={c.color} aria-hidden="true" />
                    <span style={{ fontSize: 14, fontWeight: 600 }}>{c.name}</span>
                    <span className="kd-mono" style={{
                      fontSize: 9, marginLeft: "auto", color: c.color,
                    }}>{buttons.length} · {pots.length}</span>
                  </div>

                  <div style={{
                    display: "grid", gridTemplateColumns: "repeat(7, 1fr)", gap: 4,
                  }}>
                    {buttons.map((b) => {
                      const Btn = getLucideIcon(b.icon);
                      return (
                        <div key={b.id} style={{
                          aspectRatio: "1/1", borderRadius: 6,
                          background: `${b.color}1a`,
                          border: `1px solid ${b.color}44`,
                          display: "flex", alignItems: "center", justifyContent: "center",
                        }}>
                          <Btn size={14} color={b.color} aria-hidden="true" />
                        </div>
                      );
                    })}
                  </div>

                  <div style={{
                    display: "grid", gridTemplateColumns: "repeat(4, 1fr)",
                    gap: 4, marginTop: 6,
                  }}>
                    {pots.map((p) => (
                      <div key={p.id} className="trunc" style={{
                        padding: "4px 6px", borderRadius: 5,
                        background: "var(--glass-fill-soft)",
                        border: "1px solid var(--glass-border-soft)",
                        fontFamily: "JetBrains Mono, ui-monospace, monospace", fontSize: 9,
                        color: "var(--text-3)", textAlign: "center",
                      }}>{p.label}</div>
                    ))}
                  </div>
                </div>
              );
            })}

            {/* ── Actions ── */}
            <div style={{ display: "flex", gap: 8, marginTop: "auto" }}>
              <button onClick={onActivate} className="kd-cta kd-cta--primary" style={{ flex: 1 }}>
                {profile.isActive ? "Profil actif" : "Charger ce profil"}
              </button>
              <button onClick={onDuplicate} className="kd-cta kd-cta--secondary">
                Dupliquer
              </button>
            </div>
          </>
        )}
      </div>
    </div>
  );
}

// ─────────────────────────────────────────────────────────────────────────────
// Page
// ─────────────────────────────────────────────────────────────────────────────
export function Profiles() {
  const profiles         = useStore((s) => s.profiles);
  const setActive        = useStore((s) => s.setActiveProfile);
  const createProfile    = useStore((s) => s.createProfile);
  const duplicateProfile = useStore((s) => s.duplicateProfile);
  const deleteProfile    = useStore((s) => s.deleteProfile);

  const [openId, setOpenId] = useState<number | null>(null);
  const openProfile = profiles.find((p) => p.id === openId);

  const handleExport = (p: Profile) => {
    const blob = new Blob([JSON.stringify(p, null, 2)], { type: "application/json" });
    const url  = URL.createObjectURL(blob);
    const a    = document.createElement("a");
    a.href = url; a.download = `${p.name.replace(/\s+/g, "_")}_koredeck.json`;
    a.click(); URL.revokeObjectURL(url);
  };

  return (
    <div style={{ display: "flex", flexDirection: "column", height: "100%" }}>
      <PageHeader
        title="Profils"
        subtitle={`${profiles.length} profil${profiles.length > 1 ? "s" : ""} sauvegardé${profiles.length > 1 ? "s" : ""}`}
      />

      <div style={{
        flex: 1, minHeight: 0,
        overflowY: "auto", overflowX: "hidden",
        padding: "0 28px 110px",
      }}>
        <div style={{
          display: "flex", flexDirection: "column", gap: 12,
          maxWidth: 880, margin: "0 auto",
        }}>
          <NewProfileCard onClick={() => createProfile(`Profil ${profiles.length + 1}`)} />

          {profiles.map((p) => (
            <ProfileCard
              key={p.id}
              profile={p}
              onOpen={() => setOpenId(p.id)}
              onActivate={() => setActive(p.id)}
              onDuplicate={() => duplicateProfile(p.id)}
              onExport={() => handleExport(p)}
              onDelete={() => deleteProfile(p.id)}
              canDelete={profiles.length > 1}
            />
          ))}
        </div>
      </div>

      <ProfileSideSheet
        profile={openProfile}
        onClose={() => setOpenId(null)}
        onActivate={() => {
          if (openProfile) setActive(openProfile.id);
          setOpenId(null);
        }}
        onDuplicate={() => {
          if (openProfile) duplicateProfile(openProfile.id);
          setOpenId(null);
        }}
      />
    </div>
  );
}
