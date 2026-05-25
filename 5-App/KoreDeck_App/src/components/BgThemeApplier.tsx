// =============================================================================
// BgThemeApplier.tsx — Pose data-bg-theme sur <html> à chaque changement
// Couple le store Zustand au sélecteur CSS [data-bg-theme="..."] dans index.css.
// =============================================================================

import { useEffect } from "react";
import { useStore } from "@/store";

export function BgThemeApplier() {
  const bgTheme = useStore((s) => s.bgTheme);

  useEffect(() => {
    // `?? "dark"` couvre le cas où un user déjà installé n'a pas le champ
    // dans son localStorage (migration zero-cost depuis la version précédente).
    document.documentElement.setAttribute("data-bg-theme", bgTheme ?? "dark");
  }, [bgTheme]);

  return null;
}
