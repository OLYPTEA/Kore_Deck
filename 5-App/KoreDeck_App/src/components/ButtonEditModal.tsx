// =============================================================================
// ButtonEditModal.tsx — Modal glass d'édition d'un bouton (skin "Option A")
// =============================================================================

import {
  useState, useEffect, useCallback, useRef, type CSSProperties,
} from "react";
import * as LucideIcons from "lucide-react";
import { X, Keyboard, type LucideIcon } from "lucide-react";
import type { ButtonConfig, ActionType } from "@/types";
import { useStore } from "@/store";

interface Props {
  button:    ButtonConfig;
  catColor:  string;
  onClose:   () => void;
}

const ACTION_TYPES: { id: ActionType; label: string }[] = [
  { id: "shortcut", label: "Raccourci" },
  { id: "app",      label: "App"       },
  { id: "script",   label: "Script"    },
  { id: "macro",    label: "Macro"     },
  { id: "system",   label: "Système"   },
];

const PLACEHOLDERS: Record<ActionType, string> = {
  shortcut: "Ctrl+Shift+M  ·  Cliquer puis presser les touches",
  app:      "C:\\\\Program Files\\\\App.exe   ou   notion://",
  script:   "C:\\\\scripts\\\\backup.ps1",
  macro:    "Texte à taper automatiquement",
  system:   "MUTE_MIC, TOGGLE_DND, OBS_REC...",
};

const inputStyle: CSSProperties = {
  width: "100%",
  padding: "10px 12px",
  borderRadius: "var(--r-sm)",
  background: "var(--glass-fill-soft)",
  border: "1px solid var(--glass-border)",
  color: "var(--text-1)",
  fontSize: 13,
  fontFamily: "JetBrains Mono, ui-monospace, monospace",
  outline: "none",
  boxSizing: "border-box",
};

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
      <label className="kd-mono">{label}</label>
      {children}
    </div>
  );
}

export function ButtonEditModal({ button, catColor, onClose }: Props) {
  const updateButton     = useStore((s) => s.updateButton);
  const activeProfileId  = useStore((s) => s.activeProfileId);
  const activeCategoryId = useStore((s) => s.activeCategoryId);

  const [label,       setLabel]       = useState(button.label);
  const [type,        setType]        = useState<ActionType>(button.action.type);
  const [value,       setValue]       = useState(button.action.value);
  const [longPress,   setLongPress]   = useState(button.action.longPress   ?? "");
  const [doublePress, setDoublePress] = useState(button.action.doublePress ?? "");
  const [recording,   setRecording]   = useState<"value"|"long"|"double"|null>(null);

  // Fenêtre de capture 1s pour les raccourcis. On tracke un Set de touches
  // actuellement pressées (keydown ajoute, keyup retire) et on construit la
  // combo à chaque tick — ça permet plusieurs touches non-modifier simultanées
  // (ex: Ctrl+Shift+Alt+M = 4 touches), pas juste modifiers + 1 main key.
  const MAX_KEYS = 4;
  const [liveCombo, setLiveCombo] = useState("");
  const [captureProgress, setCaptureProgress] = useState(0); // 0 → 1 sur 1s
  const bestComboRef = useRef("");
  const heldKeysRef  = useRef<Set<string>>(new Set());
  const timerRef     = useRef<number | null>(null);
  const startRef     = useRef<number>(0);
  const rafRef       = useRef<number | null>(null);

  const HeaderIcon = (LucideIcons as unknown as Record<string, LucideIcon>)[button.icon]
                     ?? LucideIcons.Square;

  // Normalise un e.key en label affichable (et clé canonique pour le Set).
  // Renvoie "" si la touche doit être ignorée (Escape pour annuler etc.).
  const normalizeKey = (key: string): string => {
    if (key === "Control") return "Ctrl";
    if (key === "Meta")    return "Win";
    if (key === "Alt")     return "Alt";
    if (key === "Shift")   return "Shift";
    if (key === " ")       return "Space";
    if (key.length === 1)  return key.toUpperCase();
    return key; // Touches nommées : ArrowLeft, F1, Enter, Tab…
  };

  // Construit la combo ordonnée (modifiers d'abord, puis touches principales).
  // Capée à MAX_KEYS pour matcher les conventions Windows (max 4 touches).
  const buildCombo = (): string => {
    const held = heldKeysRef.current;
    const MOD_ORDER = ["Ctrl", "Alt", "Shift", "Win"];
    const modifiers = MOD_ORDER.filter((m) => held.has(m));
    const mainKeys: string[] = [];
    held.forEach((k) => { if (!MOD_ORDER.includes(k)) mainKeys.push(k); });
    return [...modifiers, ...mainKeys].slice(0, MAX_KEYS).join("+");
  };

  // Reset complet quand on (re)démarre / arrête un recording
  useEffect(() => {
    if (recording) {
      bestComboRef.current = "";
      heldKeysRef.current.clear();
      setLiveCombo("");
      setCaptureProgress(0);
      startRef.current = 0;
    } else {
      if (timerRef.current) { window.clearTimeout(timerRef.current); timerRef.current = null; }
      if (rafRef.current)   { cancelAnimationFrame(rafRef.current);  rafRef.current   = null; }
      heldKeysRef.current.clear();
      setLiveCombo("");
      setCaptureProgress(0);
    }
  }, [recording]);

  const commitCombo = useCallback((target: "value"|"long"|"double", combo: string) => {
    if (!combo) { setRecording(null); return; }
    if (target === "value")  setValue(combo);
    if (target === "long")   setLongPress(combo);
    if (target === "double") setDoublePress(combo);
    setRecording(null);
  }, []);

  const handleKeyDown = useCallback((e: KeyboardEvent) => {
    if (e.key === "Escape" && !recording) { onClose(); return; }
    if (!recording) return;
    if (e.key === "Escape") {
      setRecording(null);
      return;
    }
    e.preventDefault();

    const k = normalizeKey(e.key);
    if (!k) return;

    // Sync les modifiers depuis l'état du clavier (au cas où des keyup auraient
    // été ratés — fenêtre Tauri qui perd le focus, par ex.).
    const held = heldKeysRef.current;
    if (e.ctrlKey)  held.add("Ctrl");  else held.delete("Ctrl");
    if (e.altKey)   held.add("Alt");   else held.delete("Alt");
    if (e.shiftKey) held.add("Shift"); else held.delete("Shift");
    if (e.metaKey)  held.add("Win");   else held.delete("Win");
    held.add(k);

    const combo = buildCombo();
    if (!combo) return;

    // Garde la combo la plus complète observée pendant la fenêtre.
    const bestLen = bestComboRef.current.split("+").filter(Boolean).length;
    const newLen  = combo.split("+").length;
    if (newLen >= bestLen) {
      bestComboRef.current = combo;
      setLiveCombo(combo);
    }

    // Démarre la fenêtre 1s au premier keydown valide
    if (timerRef.current === null) {
      const target = recording;
      startRef.current = performance.now();
      timerRef.current = window.setTimeout(() => {
        timerRef.current = null;
        commitCombo(target, bestComboRef.current);
      }, 1000);
      const tick = () => {
        const p = Math.min(1, (performance.now() - startRef.current) / 1000);
        setCaptureProgress(p);
        if (p < 1 && timerRef.current !== null) {
          rafRef.current = requestAnimationFrame(tick);
        }
      };
      rafRef.current = requestAnimationFrame(tick);
    }
  }, [recording, onClose, commitCombo]);

  const handleKeyUp = useCallback((e: KeyboardEvent) => {
    if (!recording) return;
    const k = normalizeKey(e.key);
    if (k) heldKeysRef.current.delete(k);
    // Sync modifiers (un keyup peut concerner Shift alors que Ctrl est toujours tenu)
    const held = heldKeysRef.current;
    if (!e.ctrlKey)  held.delete("Ctrl");
    if (!e.altKey)   held.delete("Alt");
    if (!e.shiftKey) held.delete("Shift");
    if (!e.metaKey)  held.delete("Win");
    // Ne pas mettre à jour liveCombo ici — on garde la "best" combo capturée
    // pour que l'utilisateur voie ce qui sera enregistré.
  }, [recording]);

  useEffect(() => {
    window.addEventListener("keydown", handleKeyDown);
    window.addEventListener("keyup",   handleKeyUp);
    return () => {
      window.removeEventListener("keydown", handleKeyDown);
      window.removeEventListener("keyup",   handleKeyUp);
    };
  }, [handleKeyDown, handleKeyUp]);

  const handleSave = () => {
    updateButton(activeProfileId, activeCategoryId, button.id, {
      label,
      action: {
        type, value,
        longPress:   longPress   || undefined,
        doublePress: doublePress || undefined,
      },
    });
    onClose();
  };

  return (
    <div
      role="dialog" aria-modal="true"
      aria-label={`Édition du bouton ${button.id + 1}`}
      onClick={onClose}
      style={{
        position: "fixed", inset: 0,
        // Scrim renforcé : 0.55 → 0.72 + blur 8 → 24px pour isoler le modal
        // du grid de tuiles en arrière-plan (illisibilité signalée).
        background: "rgba(0,0,0,0.72)",
        backdropFilter: "blur(24px) saturate(140%)",
        WebkitBackdropFilter: "blur(24px) saturate(140%)",
        display: "flex", alignItems: "center", justifyContent: "center",
        zIndex: 200,
        animation: "kd-fade-in 200ms var(--ease)",
      }}
    >
      <div
        onClick={(e) => e.stopPropagation()}
        className="glass glass-strong"
        style={{
          width: 480, maxWidth: "92vw", maxHeight: "92vh", overflowY: "auto",
          borderRadius: "var(--r-xl)",
          padding: 24,
          display: "flex", flexDirection: "column", gap: 18,
          animation: "kd-scale-in 240ms var(--spring)",
        }}
      >
        {/* ─── Header : avatar glow + titre + close ─────────────────────────── */}
        <div style={{ display: "flex", gap: 14, alignItems: "center" }}>
          <div style={{
            width: 52, height: 52, borderRadius: 14, flexShrink: 0,
            background: `linear-gradient(135deg, ${button.color}, ${button.color}88)`,
            display: "flex", alignItems: "center", justifyContent: "center",
            boxShadow: `0 6px 18px ${button.color}55, inset 0 1px 0 rgba(255,255,255,0.25)`,
          }}>
            <HeaderIcon size={24} color="#fff" strokeWidth={2.2} aria-hidden="true" />
          </div>

          <div style={{ flex: 1, minWidth: 0 }}>
            <div className="kd-mono" style={{ color: catColor }}>
              BTN · {String(button.id + 1).padStart(2, "0")}
            </div>
            <div style={{
              fontSize: 20, fontWeight: 600,
              letterSpacing: "-0.025em", marginTop: 2, color: "var(--text-1)",
            }}>Configurer le bouton</div>
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

        {/* ─── Libellé ─────────────────────────────────────────────────────── */}
        <Field label="Libellé">
          <input
            value={label}
            onChange={(e) => setLabel(e.target.value)}
            maxLength={16}
            placeholder="Ex: Lecture / Pause"
            style={inputStyle}
          />
        </Field>

        {/* ─── Type d'action — segmented 5 ─────────────────────────────────── */}
        <Field label="Type d'action">
          <div style={{ display: "grid", gridTemplateColumns: "repeat(5, 1fr)", gap: 4 }}>
            {ACTION_TYPES.map((t) => {
              const active = type === t.id;
              return (
                <button
                  key={t.id}
                  onClick={() => setType(t.id)}
                  style={{
                    padding: "8px 6px",
                    borderRadius: "var(--r-sm)",
                    background: active ? "var(--accent)" : "var(--glass-fill-soft)",
                    border: active ? "1px solid transparent" : "1px solid var(--glass-border-soft)",
                    fontSize: 11, fontWeight: 500,
                    color: active ? "#fff" : "var(--text-2)",
                    transition: "all 180ms var(--ease)",
                    cursor: "pointer",
                    boxShadow: active
                      ? "0 4px 14px var(--accent-glow), inset 0 1px 0 rgba(255,255,255,0.18)"
                      : "none",
                  }}
                >
                  {t.label}
                </button>
              );
            })}
          </div>
        </Field>

        {/* ─── Valeur (avec recording si type = shortcut) ──────────────────── */}
        <Field label="Valeur">
          <RecordableValue
            value={value}
            onChange={setValue}
            isShortcut={type === "shortcut"}
            recording={recording === "value"}
            liveCombo={recording === "value" ? liveCombo : ""}
            captureProgress={recording === "value" ? captureProgress : 0}
            onStartRecord={() => setRecording("value")}
            placeholder={PLACEHOLDERS[type]}
          />
        </Field>

        {/* ─── Appui long / Double-press ──────────────────────────────────── */}
        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12 }}>
          <Field label="Appui long">
            <RecordableValue
              value={longPress}
              onChange={setLongPress}
              isShortcut={type === "shortcut"}
              recording={recording === "long"}
              liveCombo={recording === "long" ? liveCombo : ""}
              captureProgress={recording === "long" ? captureProgress : 0}
              onStartRecord={() => setRecording("long")}
              placeholder="—"
              compact
            />
          </Field>
          <Field label="Double-press">
            <RecordableValue
              value={doublePress}
              onChange={setDoublePress}
              isShortcut={type === "shortcut"}
              recording={recording === "double"}
              liveCombo={recording === "double" ? liveCombo : ""}
              captureProgress={recording === "double" ? captureProgress : 0}
              onStartRecord={() => setRecording("double")}
              placeholder="—"
              compact
            />
          </Field>
        </div>

        {/* ─── Actions ─────────────────────────────────────────────────────── */}
        <div style={{ display: "flex", gap: 10, marginTop: 6 }}>
          <button onClick={onClose} className="kd-cta kd-cta--secondary" style={{ flex: 1 }}>
            Annuler
          </button>
          <button onClick={handleSave} className="kd-cta kd-cta--primary" style={{ flex: 1 }}>
            Enregistrer
          </button>
        </div>
      </div>
    </div>
  );
}

// ─────────────────────────────────────────────────────────────────────────────
// RecordableValue — input qui devient bouton "enregistrer" pour les raccourcis.
// Pendant recording : affiche liveCombo (mise à jour à chaque keydown) + barre
// de progression 0→100% sur 1s. À expiration, le parent commit la combo finale.
// ─────────────────────────────────────────────────────────────────────────────
function RecordableValue({
  value, onChange, isShortcut, recording, liveCombo = "", captureProgress = 0,
  onStartRecord, placeholder, compact = false,
}: {
  value: string;
  onChange: (v: string) => void;
  isShortcut: boolean;
  recording: boolean;
  liveCombo?: string;
  captureProgress?: number; // 0 → 1
  onStartRecord: () => void;
  placeholder: string;
  compact?: boolean;
}) {
  const inputRef = useRef<HTMLInputElement>(null);

  if (isShortcut) {
    return (
      <button
        onClick={onStartRecord}
        style={{
          ...inputStyle,
          position: "relative", overflow: "hidden",
          padding: compact ? "9px 12px" : "10px 12px",
          textAlign: "left",
          display: "flex", alignItems: "center", gap: 8,
          background: recording ? "var(--accent-soft)" : "var(--glass-fill-soft)",
          border: `1px solid ${recording ? "var(--accent)" : "var(--glass-border)"}`,
          cursor: "pointer",
          transition: "background 160ms var(--ease), border-color 160ms var(--ease)",
          color: value ? "var(--text-1)" : "var(--text-3)",
        }}
      >
        <Keyboard
          size={13}
          color={recording ? "var(--accent)" : "var(--text-3)"}
          aria-hidden="true"
        />
        {recording ? (
          liveCombo ? (
            // Combo capturée en live — chip qui se reconstruit à chaque touche
            <span style={{
              padding: "2px 8px", borderRadius: 5,
              background: "var(--accent)",
              fontFamily: "JetBrains Mono, ui-monospace, monospace",
              fontSize: 12, color: "#fff", fontWeight: 500,
              boxShadow: "0 2px 8px var(--accent-glow)",
            }}>{liveCombo}</span>
          ) : (
            <span style={{ color: "var(--accent)", fontSize: 12 }}>
              Pressez la combinaison… (1s)
            </span>
          )
        ) : value ? (
          <span style={{
            padding: "2px 8px", borderRadius: 5,
            background: "var(--glass-fill)",
            border: "1px solid var(--glass-border-soft)",
            fontFamily: "JetBrains Mono, ui-monospace, monospace",
            fontSize: 12, color: "var(--text-1)",
          }}>{value}</span>
        ) : (
          <span style={{ fontSize: 12 }}>{placeholder}</span>
        )}

        {/* Barre de progression — défile 0 → 100% pendant la fenêtre 1s.
            Posée en bas absolu, occupe toute la largeur du chip. */}
        {recording && (
          <span
            aria-hidden="true"
            style={{
              position: "absolute", left: 0, bottom: 0, height: 2,
              width: `${Math.round(captureProgress * 100)}%`,
              background: "var(--accent)",
              boxShadow: "0 0 6px var(--accent-glow)",
              transition: "width 80ms linear",
            }}
          />
        )}
      </button>
    );
  }

  return (
    <input
      ref={inputRef}
      value={value}
      onChange={(e) => onChange(e.target.value)}
      placeholder={placeholder}
      style={{ ...inputStyle, padding: compact ? "9px 12px" : "10px 12px" }}
    />
  );
}
