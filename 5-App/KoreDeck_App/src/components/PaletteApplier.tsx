import { useEffect } from "react";
import { useStore } from "@/store";
import { applyPalette } from "@/lib/palettes";

export function PaletteApplier() {
  const palette = useStore((s) => s.palette);
  useEffect(() => { applyPalette(palette); }, [palette]);
  return null;
}
