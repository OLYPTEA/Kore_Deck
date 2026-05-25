// =============================================================================
// KoreLogo.tsx — Logo Kore Deck (dégradé vert→bleu + glyphe Cpu)
// Source unique réutilisée dans TitleBar (18px) et Settings hero (68px).
// =============================================================================

import { Cpu } from "lucide-react";

export function KoreLogo({ size = 18 }: { size?: number }) {
  return (
    <div
      aria-hidden="true"
      style={{
        width: size, height: size, flexShrink: 0,
        borderRadius: Math.round(size * 0.28),
        background: "linear-gradient(135deg, var(--cat-3d), var(--accent))",
        display: "flex", alignItems: "center", justifyContent: "center",
        boxShadow:
          `0 ${(size * 0.08).toFixed(1)}px ${(size * 0.24).toFixed(1)}px rgba(48,209,88,0.4),` +
          ` inset 0 1px 0 rgba(255,255,255,0.28)`,
      }}>
      <Cpu size={Math.round(size * (size >= 60 ? 0.5 : 0.62))}
        color="#fff" strokeWidth={2.2} />
    </div>
  );
}
