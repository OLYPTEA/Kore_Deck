import { LayoutDashboard, Keyboard, Layers, Settings, Wifi, WifiOff, Loader2 } from "lucide-react";
import { useStore } from "@/store";

const NAV = [
  { id: "dashboard" as const, label: "Dashboard",  Icon: LayoutDashboard },
  { id: "config"    as const, label: "Boutons",     Icon: Keyboard },
  { id: "profiles"  as const, label: "Profils",     Icon: Layers },
  { id: "settings"  as const, label: "Paramètres",  Icon: Settings },
];

const Logo = () => (
  <svg viewBox="0 0 28 28" width="28" height="28" style={{ flexShrink: 0 }}>
    <rect width="28" height="28" rx="7" fill="#6366F1"/>
    <line x1="9"  y1="7"  x2="9"  y2="21" stroke="white" strokeWidth="2.2" strokeLinecap="round"/>
    <line x1="9"  y1="14" x2="19" y2="7"  stroke="white" strokeWidth="2.2" strokeLinecap="round"/>
    <line x1="9"  y1="14" x2="19" y2="21" stroke="white" strokeWidth="2.2" strokeLinecap="round"/>
  </svg>
);

export function Sidebar() {
  const page   = useStore(s => s.selectedPage);
  const setPage= useStore(s => s.setPage);
  const conn   = useStore(s => s.connection);

  const statusColor = { connected: "#22C55E", disconnected: "#EF4444", reconnecting: "#F59E0B" }[conn.status];
  const statusLabel = { connected: "Connecté",  disconnected: "Déconnecté",  reconnecting: "Reconnexion..." }[conn.status];
  const StatusIcon  = { connected: Wifi,        disconnected: WifiOff,       reconnecting: Loader2 }[conn.status];

  return (
    <aside style={{
      width: 200, minWidth: 200,
      display: "flex", flexDirection: "column",
      height: "100%",
      background: "rgba(10, 10, 12, 0.65)",
      backdropFilter: "var(--glass-blur-light)",
      WebkitBackdropFilter: "var(--glass-blur-light)",
      borderRight: "1px solid rgba(255,255,255,0.07)",
    }}>

      {/* Logo */}
      <div style={{
        padding: "16px 14px",
        borderBottom: "1px solid rgba(255,255,255,0.06)",
        display: "flex", alignItems: "center", gap: 10,
      }}>
        <Logo />
        <div>
          <div style={{ fontSize: 13, fontWeight: 600, color: "#ECECEF", letterSpacing: "-0.01em" }}>
            Kore Deck
          </div>
          <div style={{ fontSize: 10, color: "#4E4E60", marginTop: 1 }}>v2.0</div>
        </div>
      </div>

      {/* Nav */}
      <nav style={{ padding: "10px 8px", flex: 1 }}>
        <div style={{
          fontSize: 9.5, color: "#4E4E60", fontWeight: 600,
          padding: "8px 10px 6px",
          textTransform: "uppercase", letterSpacing: "0.12em",
        }}>
          Navigation
        </div>

        {NAV.map(({ id, label, Icon }) => {
          const active = page === id;
          return (
            <button key={id} onClick={() => setPage(id)}
              aria-current={active ? "page" : undefined}
              style={{
                display: "flex", alignItems: "center", gap: 8,
                width: "100%", padding: "7px 10px", paddingLeft: 9,
                fontSize: 13, textAlign: "left",
                borderRadius: 8, marginBottom: 1,
                background: active ? "rgba(99,102,241,0.12)" : "transparent",
                border: "none",
                borderLeft: `2.5px solid ${active ? "#6366F1" : "transparent"}`,
                color: active ? "#ECECEF" : "#8E8EA0",
                cursor: "pointer", transition: "all 0.12s",
              }}
              onMouseEnter={e => {
                if (!active) {
                  (e.currentTarget as HTMLElement).style.background = "rgba(255,255,255,0.04)";
                  (e.currentTarget as HTMLElement).style.color = "#ECECEF";
                }
              }}
              onMouseLeave={e => {
                if (!active) {
                  (e.currentTarget as HTMLElement).style.background = "transparent";
                  (e.currentTarget as HTMLElement).style.color = "#8E8EA0";
                }
              }}
            >
              <Icon size={14} aria-hidden="true"/>
              {label}
            </button>
          );
        })}
      </nav>

      {/* Status */}
      <div style={{
        padding: "12px 14px",
        borderTop: "1px solid rgba(255,255,255,0.06)",
      }}>
        <div style={{ display: "flex", alignItems: "center", gap: 7, marginBottom: 3 }}>
          <div style={{
            width: 6, height: 6, borderRadius: "50%",
            background: statusColor,
            boxShadow: `0 0 6px ${statusColor}88`,
            animation: conn.status === "reconnecting" ? "blink 1.2s ease-in-out infinite" : "none",
          }}/>
          <StatusIcon
            size={10} color={statusColor}
            style={conn.status === "reconnecting" ? { animation: "spin 1s linear infinite" } : undefined}
          />
          <span style={{ fontSize: 11, color: "#8E8EA0" }}>{statusLabel}</span>
        </div>
        <div style={{ fontSize: 10, color: "#4E4E60", paddingLeft: 13 }}>
          {conn.port} · {conn.baud?.toLocaleString()} baud
        </div>
      </div>
    </aside>
  );
}
