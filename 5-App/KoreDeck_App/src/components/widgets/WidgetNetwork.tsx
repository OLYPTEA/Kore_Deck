// =============================================================================
// WidgetNetwork.tsx — Bande passante up/down (mock à brancher plus tard)
// =============================================================================

import { useEffect, useState } from "react";
import { Wifi, ArrowDown, ArrowUp } from "lucide-react";
import { useRingBuffer } from "@/hooks/useRingBuffer";
import { WidgetShell } from "./WidgetShell";
import { Sparkline } from "./Sparkline";

interface NetSample { down: number; up: number; }

// TODO: brancher sur l'agent Python (psutil net_io_counters).
function useMockNetwork(): NetSample {
  const [s, setS] = useState<NetSample>({ down: 4.2, up: 1.1 });
  useEffect(() => {
    const id = setInterval(() => {
      setS((v) => ({
        down: Math.max(0, Math.min(60, v.down + (Math.random() - 0.5) * 4)),
        up:   Math.max(0, Math.min(20, v.up   + (Math.random() - 0.5) * 1.4)),
      }));
    }, 1000);
    return () => clearInterval(id);
  }, []);
  return s;
}

function fmt(mbps: number): string {
  return mbps >= 10 ? mbps.toFixed(0) : mbps.toFixed(1);
}

export function WidgetNetwork() {
  const { down, up } = useMockNetwork();
  const downHist = useRingBuffer(down, 60, 1000);
  const upHist   = useRingBuffer(up,   60, 1000);

  return (
    <WidgetShell label="RÉSEAU" Icon={Wifi} accent="var(--accent)">
      <div style={{
        display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12,
        alignItems: "baseline",
      }}>
        <div>
          <div style={{ display: "flex", alignItems: "center", gap: 4, color: "var(--accent)" }}>
            <ArrowDown size={12} aria-hidden="true" />
            <span className="tnum" style={{
              fontSize: "clamp(18px, 1.8vw, 26px)", fontWeight: 600,
              letterSpacing: "-0.03em", color: "var(--text-1)",
            }}>{fmt(down)}</span>
            <span className="kd-mono" style={{ fontSize: 9, marginLeft: 2 }}>MB/S</span>
          </div>
        </div>
        <div>
          <div style={{ display: "flex", alignItems: "center", gap: 4, color: "var(--warn)" }}>
            <ArrowUp size={12} aria-hidden="true" />
            <span className="tnum" style={{
              fontSize: "clamp(18px, 1.8vw, 26px)", fontWeight: 600,
              letterSpacing: "-0.03em", color: "var(--text-1)",
            }}>{fmt(up)}</span>
            <span className="kd-mono" style={{ fontSize: 9, marginLeft: 2 }}>MB/S</span>
          </div>
        </div>
      </div>
      <div style={{ flex: 1, minHeight: 24, marginTop: 8, maxHeight: 64, position: "relative" }}>
        <div style={{ position: "absolute", inset: 0 }}>
          <Sparkline data={downHist} color="var(--accent)" min={0} max={60} />
        </div>
        <div style={{ position: "absolute", inset: 0, opacity: 0.7 }}>
          <Sparkline data={upHist}   color="var(--warn)"   min={0} max={20} filled={false} />
        </div>
      </div>
      <div className="kd-mono" style={{ fontSize: 9, marginTop: 4 }}>
        60S · ↓ {fmt(Math.max(...downHist))} · ↑ {fmt(Math.max(...upHist))} MAX
      </div>
    </WidgetShell>
  );
}
