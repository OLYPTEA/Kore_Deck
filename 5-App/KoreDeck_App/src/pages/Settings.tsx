// =============================================================================
// Settings.tsx — Paramètres : Hero ESP32 + Palette + connexion + app + firmware
// =============================================================================

import { useEffect, useState } from "react";
import {
  RotateCw, Plug, AppWindow, Microchip, Info, Moon,
} from "lucide-react";
import type { BgTheme } from "@/store";
import { listSerialPorts, setAutostart, type SerialPort } from "@/lib/tauri-commands";
import { useStore } from "@/store";
import { PageHeader } from "@/components/PageHeader";
import { PaletteSection } from "@/components/PaletteSection";
import { KoreLogo } from "@/components/KoreLogo";

// ─── Toggle (style refonte) ───────────────────────────────────────────────
function Toggle({ value, onChange }: { value: boolean; onChange: (v: boolean) => void }) {
  return (
    <button onClick={() => onChange(!value)}
      role="switch" aria-checked={value}
      style={{
        width: 44, height: 26, borderRadius: 999,
        background: value ? "var(--ok)" : "rgba(255,255,255,0.12)",
        position: "relative",
        transition: "background 220ms var(--ease)",
        boxShadow: value
          ? "inset 0 1px 0 rgba(255,255,255,0.2)"
          : "inset 0 1px 2px rgba(0,0,0,0.4)",
        cursor: "pointer", border: "none", padding: 0,
      }}>
      <div style={{
        position: "absolute", top: 2, left: value ? 20 : 2,
        width: 22, height: 22, borderRadius: "50%",
        background: "#fff",
        boxShadow: "0 2px 6px rgba(0,0,0,0.35)",
        transition: "left 220ms var(--ease)",
      }}/>
    </button>
  );
}

// ─── BgThemeSegmented (Sombre / Lunaire) ─────────────────────────────────
function BgThemeSegmented({ value, onChange }: {
  value: BgTheme;
  onChange: (v: BgTheme) => void;
}) {
  const options: { value: BgTheme; label: string }[] = [
    { value: "dark",  label: "Sombre"  },
    { value: "lunar", label: "Lunaire" },
  ];
  return (
    <div style={{
      display: "flex", gap: 2, padding: 3,
      background: "var(--glass-fill-soft)",
      border: "1px solid var(--glass-border-soft)",
      borderRadius: 999,
    }}>
      {options.map((o) => {
        const active = o.value === value;
        return (
          <button key={o.value}
            onClick={() => onChange(o.value)}
            style={{
              padding: "6px 14px", borderRadius: 999,
              background: active ? "var(--accent)" : "transparent",
              color: active ? "#fff" : "var(--text-2)",
              fontSize: 12, fontWeight: 500, letterSpacing: "-0.01em",
              cursor: "pointer", border: "none",
              transition: "background 180ms var(--ease), color 180ms var(--ease), box-shadow 180ms var(--ease)",
              boxShadow: active ? "0 4px 12px var(--accent-glow)" : "none",
            }}>
            {o.label}
          </button>
        );
      })}
    </div>
  );
}

// ─── SelectField ─────────────────────────────────────────────────────────
function SelectField<T extends string | number>({ value, options, onChange }: {
  value: T;
  options: { label: string; value: T }[];
  onChange: (v: T) => void;
}) {
  return (
    <select value={String(value)}
      onChange={(e) => {
        const v = options.find((o) => String(o.value) === e.target.value)?.value;
        if (v !== undefined) onChange(v);
      }}
      style={{
        padding: "7px 30px 7px 12px",
        borderRadius: 8,
        background: "var(--glass-fill-soft)",
        border: "1px solid var(--glass-border)",
        color: "var(--text-1)", fontSize: 12, minWidth: 130, width: "auto",
        appearance: "none",
        backgroundImage: "url(\"data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='10' height='6' viewBox='0 0 10 6'%3E%3Cpath d='M1 1l4 4 4-4' stroke='%23aaa' stroke-width='1.5' fill='none' stroke-linecap='round'/%3E%3C/svg%3E\")",
        backgroundRepeat: "no-repeat",
        backgroundPosition: "right 10px center",
      }}>
      {options.map((o) => (
        <option key={String(o.value)} value={String(o.value)} style={{ background: "#1a1a1f" }}>
          {o.label}
        </option>
      ))}
    </select>
  );
}

// ─── SliderField ─────────────────────────────────────────────────────────
function SliderField({ value, min, max, onChange, unit = "ms" }: {
  value: number; min: number; max: number; onChange: (v: number) => void; unit?: string;
}) {
  return (
    <div style={{ display: "flex", alignItems: "center", gap: 10, width: 220 }}>
      <input type="range" value={value} min={min} max={max}
        onChange={(e) => onChange(+e.target.value)}
        style={{ flex: 1, accentColor: "var(--accent)" }}/>
      <span className="tnum kd-mono" style={{
        fontSize: 10, color: "var(--text-1)", minWidth: 48, textAlign: "right",
      }}>{value} {unit.toUpperCase()}</span>
    </div>
  );
}

// ─── SettingsRow ─────────────────────────────────────────────────────────
function SettingsRow({ label, hint, children }: {
  label: string; hint?: string; children: React.ReactNode;
}) {
  return (
    <div style={{
      display: "flex", alignItems: "center", gap: 16,
      padding: "12px 18px",
      borderTop: "1px solid var(--glass-border-soft)",
    }}>
      <div style={{ flex: 1, minWidth: 0 }}>
        <div style={{ fontSize: 13, color: "var(--text-1)", fontWeight: 500 }}>{label}</div>
        {hint && <div style={{ fontSize: 11, color: "var(--text-3)", marginTop: 2 }}>{hint}</div>}
      </div>
      <div>{children}</div>
    </div>
  );
}

// ─── SettingsGroup ───────────────────────────────────────────────────────
function SettingsGroup({ title, Icon, children }: {
  title: string; Icon: typeof Plug; children: React.ReactNode;
}) {
  return (
    <div className="glass" style={{
      borderRadius: "var(--r-lg)", padding: "8px 4px",
      overflow: "hidden", marginBottom: 12,
    }}>
      <div style={{
        padding: "12px 18px 8px", display: "flex", alignItems: "center", gap: 8,
        position: "relative", zIndex: 1,
      }}>
        <Icon size={13} color="var(--accent)" aria-hidden="true" />
        <span className="kd-mono" style={{
          color: "var(--text-2)", letterSpacing: "0.14em",
        }}>{title.toUpperCase()}</span>
      </div>
      <div style={{ position: "relative", zIndex: 1 }}>{children}</div>
    </div>
  );
}

// ─── Page ────────────────────────────────────────────────────────────────
export function Settings() {
  const conn      = useStore((s) => s.connection);
  const settings  = useStore((s) => s.settings);
  const updateSettings = useStore((s) => s.updateSettings);
  const bgTheme   = useStore((s) => s.bgTheme);
  const setBgTheme = useStore((s) => s.setBgTheme);

  const [ports, setPorts] = useState<SerialPort[]>([]);
  useEffect(() => { listSerialPorts().then(setPorts); }, []);

  const handleAutostart = async (v: boolean) => {
    updateSettings({ startWithWindows: v });
    await setAutostart(v);
  };

  const portOptions = (ports.length > 0
    ? ports.map((p) => ({ label: p.name + (p.description ? ` — ${p.description}` : ""), value: p.name }))
    : [{ label: settings.serialPort, value: settings.serialPort }]);

  return (
    <div style={{ display: "flex", flexDirection: "column", height: "100%" }}>
      <PageHeader
        title="Paramètres"
        subtitle="Connexion série, application, firmware."
      />

      <div style={{
        flex: 1, minHeight: 0,
        overflowY: "auto", overflowX: "hidden",
        padding: "0 28px 110px",
      }}>
        <div style={{
          maxWidth: 720, margin: "0 auto",
          display: "flex", flexDirection: "column", gap: 16,
        }}>
          {/* Hero ESP32 */}
          <div className="glass" style={{
            padding: 22, borderRadius: "var(--r-lg)",
            display: "flex", alignItems: "center", gap: 18,
          }}>
            <KoreLogo size={68} />
            <div style={{ flex: 1, position: "relative", zIndex: 1 }}>
              <div className="kd-mono">DECK PHYSIQUE</div>
              <div style={{
                fontSize: 22, fontWeight: 600, letterSpacing: "-0.025em", marginTop: 2,
              }}>Kore Deck · ESP32</div>
              <div style={{
                display: "flex", gap: 14, marginTop: 8,
                fontSize: 12, color: "var(--text-3)",
                flexWrap: "wrap",
              }}>
                <span style={{ display: "flex", alignItems: "center", gap: 5 }}>
                  <div className={conn.status === "connected" ? "pulse" : ""} style={{
                    width: 7, height: 7, borderRadius: "50%",
                    background: conn.status === "connected" ? "var(--ok)" : "var(--err)",
                  }}/>
                  {conn.status === "connected" ? `Connecté · ${conn.port}` : "Déconnecté"}
                </span>
                <span>Firmware {settings.firmwareVersion}</span>
                <span>{conn.baud} baud</span>
              </div>
            </div>
            <button className="kd-cta kd-cta--secondary kd-cta--sm" style={{ position: "relative", zIndex: 1 }}>
              <RotateCw size={12} aria-hidden="true" /> Reconnecter
            </button>
          </div>

          {/* Palette */}
          <PaletteSection />

          {/* Apparence — Background */}
          <SettingsGroup title="Apparence" Icon={Moon}>
            <SettingsRow label="Background"
              hint="Gradient nuit sombre ou lumineux façon lumière rasante">
              <BgThemeSegmented value={bgTheme ?? "dark"} onChange={setBgTheme} />
            </SettingsRow>
          </SettingsGroup>

          {/* Connexion série */}
          <SettingsGroup title="Connexion série" Icon={Plug}>
            <SettingsRow label="Port" hint="Détection automatique recommandée">
              <SelectField value={settings.serialPort} options={portOptions}
                onChange={(v) => updateSettings({ serialPort: v })} />
            </SettingsRow>
            <SettingsRow label="Baud rate">
              <SelectField value={settings.baudRate}
                options={[9600, 57600, 115200, 230400, 460800, 921600].map((b) => ({
                  label: b.toLocaleString(), value: b,
                }))}
                onChange={(v) => updateSettings({ baudRate: v })} />
            </SettingsRow>
            <SettingsRow label="Intervalle d'envoi" hint="Délai entre 2 trames système (ms)">
              <SliderField value={settings.sendInterval} min={50} max={500}
                onChange={(v) => updateSettings({ sendInterval: v })} />
            </SettingsRow>
            <SettingsRow label="Reconnexion auto" hint="Reconnecte si le câble est débranché">
              <Toggle value={settings.autoReconnect}
                onChange={(v) => updateSettings({ autoReconnect: v })} />
            </SettingsRow>
          </SettingsGroup>

          {/* Application */}
          <SettingsGroup title="Application" Icon={AppWindow}>
            <SettingsRow label="Lancer au démarrage de Windows"
              hint="Lance l'agent automatiquement au boot">
              <Toggle value={settings.startWithWindows} onChange={handleAutostart} />
            </SettingsRow>
            <SettingsRow label="Minimiser dans la tray"
              hint="Fermer la fenêtre la cache, n'arrête pas l'app">
              <Toggle value={settings.minimizeToTray}
                onChange={(v) => updateSettings({ minimizeToTray: v })} />
            </SettingsRow>
          </SettingsGroup>

          {/* Firmware */}
          <SettingsGroup title="Firmware" Icon={Microchip}>
            <SettingsRow label="Version installée">
              <span className="kd-mono" style={{ color: "var(--text-1)", fontSize: 11 }}>
                {settings.firmwareVersion}
              </span>
            </SettingsRow>
            <SettingsRow label="Vérifier les mises à jour">
              <button className="kd-cta kd-cta--ghost kd-cta--sm">Vérifier</button>
            </SettingsRow>
          </SettingsGroup>

          {/* À propos */}
          <SettingsGroup title="À propos" Icon={Info}>
            <SettingsRow label="Kore Deck">
              <span style={{ fontSize: 12, color: "var(--text-3)" }}>
                v2.0.0 · build {new Date().getFullYear()}.{String(new Date().getMonth() + 1).padStart(2, "0")}
              </span>
            </SettingsRow>
            <SettingsRow label="OLYPTEA · Open Source">
              <span className="kd-mono" style={{ fontSize: 10 }}>MIT LICENSE</span>
            </SettingsRow>
          </SettingsGroup>
        </div>
      </div>
    </div>
  );
}
