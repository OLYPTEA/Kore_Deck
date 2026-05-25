// =============================================================================
// palettes.ts — 6 thèmes iOS-like pour Kore Deck
// =============================================================================

export type PaletteId = "default" | "sunset" | "forest" | "ocean" | "vibrant" | "mono";

export interface Palette {
  id:     PaletteId;
  name:   string;
  accent: string;
  home:   string;
  "3d":   string;
  focus:  string;
  game:   string;
}

export const PALETTES: Record<PaletteId, Palette> = {
  default: { id: "default", name: "Aurore",   accent: "#0A84FF", home: "#5E5CE6", "3d": "#30D158", focus: "#FF9F0A", game: "#FF453A" },
  sunset:  { id: "sunset",  name: "Sunset",   accent: "#FF9500", home: "#FF2D55", "3d": "#FF375F", focus: "#FFD60A", game: "#FF6482" },
  forest:  { id: "forest",  name: "Forêt",    accent: "#30D158", home: "#00C7BE", "3d": "#30D158", focus: "#FFD60A", game: "#BF5AF2" },
  ocean:   { id: "ocean",   name: "Océan",    accent: "#0A84FF", home: "#5856D6", "3d": "#5AC8FA", focus: "#00C7BE", game: "#BF5AF2" },
  vibrant: { id: "vibrant", name: "Vibrant",  accent: "#BF5AF2", home: "#FF375F", "3d": "#30D158", focus: "#FFD60A", game: "#FF453A" },
  mono:    { id: "mono",    name: "Graphite", accent: "#A8A8AE", home: "#8E8E93", "3d": "#C7C7CC", focus: "#636366", game: "#EBEBF0" },
};

export const PALETTE_LIST = Object.values(PALETTES);

export function hexA(hex: string, a: number): string {
  const h = hex.replace("#", "");
  const r = parseInt(h.slice(0, 2), 16);
  const g = parseInt(h.slice(2, 4), 16);
  const b = parseInt(h.slice(4, 6), 16);
  return `rgba(${r}, ${g}, ${b}, ${a})`;
}

export function applyPalette(id: PaletteId): void {
  const p = PALETTES[id] || PALETTES.default;
  const root = document.documentElement;
  root.style.setProperty("--accent",       p.accent);
  root.style.setProperty("--accent-hi",    p.accent);
  root.style.setProperty("--accent-soft",  hexA(p.accent, 0.18));
  root.style.setProperty("--accent-glow",  hexA(p.accent, 0.45));
  root.style.setProperty("--accent-dim",   hexA(p.accent, 0.14));
  root.style.setProperty("--accent-bd",    hexA(p.accent, 0.40));
  root.style.setProperty("--cat-home",     p.home);
  root.style.setProperty("--cat-3d",       p["3d"]);
  root.style.setProperty("--cat-focus",    p.focus);
  root.style.setProperty("--cat-game",     p.game);
}
