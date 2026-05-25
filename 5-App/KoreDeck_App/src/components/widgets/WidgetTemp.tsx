// =============================================================================
// WidgetTemp.tsx — Température CPU (mock HWiNFO, à brancher plus tard)
// =============================================================================

import { useEffect, useState } from "react";
import { Thermometer } from "lucide-react";
import { useRingBuffer } from "@/hooks/useRingBuffer";
import { WidgetShell, BigNumber } from "./WidgetShell";
import { Sparkline } from "./Sparkline";

// TODO: remplacer par la lecture HWiNFO via l'agent Python (WebSocket).
function useMockTemp(): number {
  const [t, setT] = useState(58);
  useEffect(() => {
    const id = setInterval(() => {
      setT((v) => Math.max(48, Math.min(82, v + (Math.random() - 0.5) * 2.5)));
    }, 1000);
    return () => clearInterval(id);
  }, []);
  return Math.round(t);
}

export function WidgetTemp() {
  const t    = useMockTemp();
  const hist = useRingBuffer(t, 60, 1000);
  const color =
    t > 75 ? "var(--err)" :
    t > 65 ? "var(--warn)" : "var(--accent)";

  return (
    <WidgetShell label="TEMP CPU" Icon={Thermometer} accent={color}>
      <BigNumber value={t} unit="°C" />
      <div style={{ flex: 1, minHeight: 24, marginTop: 8, maxHeight: 64 }}>
        <Sparkline data={hist} color={color} min={40} max={90} />
      </div>
      <div className="kd-mono" style={{ fontSize: 9, marginTop: 4 }}>
        HWiNFO · PACKAGE
      </div>
    </WidgetShell>
  );
}
