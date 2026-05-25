// =============================================================================
// Dashboard.tsx — Grille 6×5 statique de widgets glass
// =============================================================================

import { PageHeader }   from "@/components/PageHeader";
import { WidgetCPU } from "@/components/widgets/WidgetCPU";
import {
  WidgetRAM, WidgetFPS, WidgetMic, WidgetPomodoro,
  WidgetSpotify, WidgetDWIN, WidgetPots,
} from "@/components/widgets/extras";

// ─── Layout fixe (sans drag&drop) ─────────────────────────────────────────
// Chaque entrée correspond à une zone du grid : x, y (1-indexés), w, h.
const LAYOUT = [
  { Cmp: WidgetCPU,      x: 1, y: 1, w: 2, h: 2 },
  { Cmp: WidgetSpotify,  x: 3, y: 1, w: 4, h: 2 },
  { Cmp: WidgetRAM,      x: 1, y: 3, w: 2, h: 1 },
  { Cmp: WidgetDWIN,     x: 3, y: 3, w: 4, h: 2 },
  { Cmp: WidgetFPS,      x: 1, y: 4, w: 1, h: 1 },
  { Cmp: WidgetMic,      x: 2, y: 4, w: 1, h: 1 },
  { Cmp: WidgetPomodoro, x: 1, y: 5, w: 2, h: 1 },
  { Cmp: WidgetPots,     x: 3, y: 5, w: 4, h: 1 },
];

export function Dashboard() {
  return (
    <div style={{ display: "flex", flexDirection: "column", height: "100%" }}>
      <PageHeader
        title="Dashboard"
        subtitle="Monitoring temps réel · widgets repositionnables"
      />

      <div style={{
        flex: 1, minHeight: 0,
        padding: "0 28px 88px",   // 88px = Dock ~60px + clearance 28px (vs 110px avant : trop généreux)
        display: "flex", flexDirection: "column",
      }}>
        <div style={{
          flex: 1, minHeight: 0,
          display: "grid",
          gridTemplateColumns: "repeat(6, 1fr)",
          gridTemplateRows:    "repeat(5, 1fr)",
          gap: "var(--gap-grid)",
        }}>
          {LAYOUT.map(({ Cmp, x, y, w, h }, i) => (
            <div key={i} style={{
              gridColumn: `${x} / span ${w}`,
              gridRow:    `${y} / span ${h}`,
              minWidth: 0, minHeight: 0,
              width: "100%", height: "100%",
              display: "flex",
            }}>
              <Cmp />
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
