// =============================================================================
// Sparkline.tsx — Mini-graph SVG (60 derniers points)
// =============================================================================

import { useId } from "react";

interface SparklineProps {
  data:   number[];
  color?: string;
  min?:   number;
  max?:   number;
  filled?: boolean;
}

export function Sparkline({ data, color = "var(--accent)", min = 0, max = 100, filled = true }: SparklineProps) {
  const gradId = useId().replace(/:/g, "");
  const w = 280, h = 80;
  if (!data.length) return null;

  const pts = data.map((v, i) => {
    const x = (i / Math.max(1, data.length - 1)) * w;
    const y = h - ((v - min) / Math.max(0.0001, max - min)) * h;
    return [x, y] as const;
  });
  const d    = pts.map((p, i) => (i === 0 ? "M" : "L") + p[0].toFixed(1) + "," + p[1].toFixed(1)).join(" ");
  const area = d + ` L${w},${h} L0,${h} Z`;

  return (
    <svg viewBox={`0 0 ${w} ${h}`} preserveAspectRatio="none"
         style={{ width: "100%", height: "100%", display: "block" }}>
      <defs>
        <linearGradient id={`spk-${gradId}`} x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%"  stopColor={color} stopOpacity="0.35" />
          <stop offset="100%" stopColor={color} stopOpacity="0" />
        </linearGradient>
      </defs>
      {filled && <path d={area} fill={`url(#spk-${gradId})`} />}
      <path d={d} fill="none" stroke={color} strokeWidth="1.6"
            strokeLinejoin="round" strokeLinecap="round" />
    </svg>
  );
}
