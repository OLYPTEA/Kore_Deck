// =============================================================================
// WidgetCPU.tsx — CPU live + sparkline 60s
// =============================================================================

import { Cpu } from "lucide-react";
import { useStore } from "@/store";
import { useRingBuffer } from "@/hooks/useRingBuffer";
import { WidgetShell, BigNumber } from "./WidgetShell";
import { Sparkline } from "./Sparkline";

export function WidgetCPU() {
  const cpu  = useStore((s) => s.stats.cpu);
  const hist = useRingBuffer(cpu, 60, 1000);
  const color =
    cpu > 75 ? "var(--err)" :
    cpu > 55 ? "var(--warn)" : "var(--accent)";
  const peak = Math.max(...hist);

  return (
    <WidgetShell label="CPU" Icon={Cpu} accent={color}>
      <BigNumber value={cpu.toFixed(0)} unit="%" size="md" />
      <div style={{ flex: 1, minHeight: 0, marginTop: 6, overflow: "hidden" }}>
        <Sparkline data={hist} color={color} />
      </div>
      <div className="kd-mono" style={{ fontSize: 9, marginTop: 4, flexShrink: 0 }}>
        60S · {peak.toFixed(0)}% MAX
      </div>
    </WidgetShell>
  );
}
