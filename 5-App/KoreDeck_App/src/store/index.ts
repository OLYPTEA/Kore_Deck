// =============================================================================
// store/index.ts — Store global Zustand
// Gère l'état complet de l'application (profils, monitoring, connexion, settings)
// =============================================================================

import { create } from "zustand";
import { persist, createJSONStorage } from "zustand/middleware";
import {
  Profile, SystemStats, ConnectionState, AppSettings,
  CategoryId, ButtonConfig, PotConfig,
  DEFAULT_BUTTONS, DEFAULT_POTS, CATEGORIES,
} from "@/types";
import type { PaletteId } from "@/lib/palettes";

// Thème de background — n'affecte QUE le gradient global, pas la skin glass/texte.
export type BgTheme = "dark" | "lunar";

// ─────────────────────────────────────────────────────────────────────────────
// État initial
// ─────────────────────────────────────────────────────────────────────────────
const DEFAULT_PROFILE: Profile = {
  id: 1,
  name: "Profil par défaut",
  description: "Configuration de base",
  createdAt: new Date().toISOString(),
  updatedAt: new Date().toISOString(),
  isActive: true,
  categories: CATEGORIES.map((cat) => ({
    categoryId: cat.id as CategoryId,
    buttons:    DEFAULT_BUTTONS[cat.id],
    pots:       DEFAULT_POTS[cat.id],
  })),
};

const DEFAULT_STATS: SystemStats = {
  cpu: 0, ram: 0, fps: 0,
  micMuted: false, dndActive: false, obsActive: false,
  trackTitle: "Aucune lecture", trackArtist: "",
  pomoMinutes: 25, pomoSeconds: 0, pomoSession: 0, pomoRunning: false,
};

const DEFAULT_SETTINGS: AppSettings = {
  serialPort:       "COM3",
  baudRate:         115200,
  sendInterval:     100,
  autoReconnect:    true,
  startWithWindows: false,
  minimizeToTray:   true,
  firmwareVersion:  "v2.0.0",
};

// ─────────────────────────────────────────────────────────────────────────────
// Interface du store
// ─────────────────────────────────────────────────────────────────────────────
interface StreamDeckStore {
  // --- Profils
  profiles:       Profile[];
  activeProfileId:number;
  activeCategoryId: CategoryId;

  // --- Monitoring live
  stats:          SystemStats;

  // --- Connexion ESP32
  connection:     ConnectionState;

  // --- Paramètres
  settings:       AppSettings;

  // --- UI
  selectedPage:   "dashboard" | "config" | "profiles" | "settings";
  palette:        PaletteId;
  bgTheme:        BgTheme;

  // ─── Actions ───────────────────────────────────────────────────────────────

  // Profils
  setActiveProfile:   (id: number) => void;
  createProfile:      (name: string, description?: string) => void;
  duplicateProfile:   (id: number) => void;
  deleteProfile:      (id: number) => void;
  updateProfileName:  (id: number, name: string) => void;

  // Catégorie active
  setActiveCategory:  (id: CategoryId) => void;

  // Boutons
  updateButton: (
    profileId:  number,
    categoryId: CategoryId,
    buttonId:   number,
    config:     Partial<ButtonConfig>
  ) => void;

  // Potentiomètres
  updatePot: (
    profileId:  number,
    categoryId: CategoryId,
    potId:      number,
    config:     Partial<PotConfig>
  ) => void;

  // Monitoring
  updateStats:        (stats: Partial<SystemStats>) => void;

  // Connexion
  setConnectionStatus:(state: Partial<ConnectionState>) => void;

  // Paramètres
  updateSettings:     (settings: Partial<AppSettings>) => void;

  // Navigation
  setPage:            (page: StreamDeckStore["selectedPage"]) => void;

  // Palette de couleurs (cosmétique pure)
  setPalette:         (id: PaletteId) => void;

  // Thème de background (cosmétique pure)
  setBgTheme:         (id: BgTheme) => void;

  // Getters dérivés
  getActiveProfile:   () => Profile | undefined;
  getActiveCategory:  () => import("@/types").CategoryConfig | undefined;
}

// ─────────────────────────────────────────────────────────────────────────────
// Store Zustand avec persistance localStorage
// ─────────────────────────────────────────────────────────────────────────────
export const useStore = create<StreamDeckStore>()(
  persist(
    (set, get) => ({
      profiles:        [DEFAULT_PROFILE],
      activeProfileId: 1,
      activeCategoryId: 0,
      stats:           DEFAULT_STATS,
      connection: {
        status:   "disconnected",
        port:     "COM3",
        baud:     115200,
        lastSeen: null,
      },
      settings:      DEFAULT_SETTINGS,
      selectedPage:  "dashboard",
      palette:       "default",
      bgTheme:       "dark",

      // ─── Profils ───────────────────────────────────────────────────────
      setActiveProfile: (id) => {
        set((state) => ({
          activeProfileId: id,
          profiles: state.profiles.map((p) => ({
            ...p,
            isActive: p.id === id,
          })),
        }));
      },

      createProfile: (name, description = "") => {
        const newId = Date.now();
        const newProfile: Profile = {
          ...DEFAULT_PROFILE,
          id:          newId,
          name,
          description,
          isActive:    false,
          createdAt:   new Date().toISOString(),
          updatedAt:   new Date().toISOString(),
        };
        set((state) => ({ profiles: [...state.profiles, newProfile] }));
      },

      duplicateProfile: (id) => {
        const source = get().profiles.find((p) => p.id === id);
        if (!source) return;
        const newProfile: Profile = {
          ...source,
          id:        Date.now(),
          name:      `${source.name} (copie)`,
          isActive:  false,
          createdAt: new Date().toISOString(),
          updatedAt: new Date().toISOString(),
        };
        set((state) => ({ profiles: [...state.profiles, newProfile] }));
      },

      deleteProfile: (id) => {
        set((state) => ({
          profiles: state.profiles.filter(
            (p) => p.id !== id || state.profiles.length === 1
          ),
        }));
      },

      updateProfileName: (id, name) => {
        set((state) => ({
          profiles: state.profiles.map((p) =>
            p.id === id
              ? { ...p, name, updatedAt: new Date().toISOString() }
              : p
          ),
        }));
      },

      // ─── Catégorie ─────────────────────────────────────────────────────
      setActiveCategory: (id) => set({ activeCategoryId: id }),

      // ─── Boutons ───────────────────────────────────────────────────────
      updateButton: (profileId, categoryId, buttonId, config) => {
        set((state) => ({
          profiles: state.profiles.map((p) => {
            if (p.id !== profileId) return p;
            return {
              ...p,
              updatedAt: new Date().toISOString(),
              categories: p.categories.map((cat) => {
                if (cat.categoryId !== categoryId) return cat;
                return {
                  ...cat,
                  buttons: cat.buttons.map((btn) =>
                    btn.id === buttonId ? { ...btn, ...config } : btn
                  ),
                };
              }),
            };
          }),
        }));
      },

      // ─── Potards ───────────────────────────────────────────────────────
      updatePot: (profileId, categoryId, potId, config) => {
        set((state) => ({
          profiles: state.profiles.map((p) => {
            if (p.id !== profileId) return p;
            return {
              ...p,
              updatedAt: new Date().toISOString(),
              categories: p.categories.map((cat) => {
                if (cat.categoryId !== categoryId) return cat;
                return {
                  ...cat,
                  pots: cat.pots.map((pot) =>
                    pot.id === potId ? { ...pot, ...config } : pot
                  ),
                };
              }),
            };
          }),
        }));
      },

      // ─── Monitoring ────────────────────────────────────────────────────
      updateStats: (stats) =>
        set((state) => ({ stats: { ...state.stats, ...stats } })),

      // ─── Connexion ─────────────────────────────────────────────────────
      setConnectionStatus: (conn) =>
        set((state) => ({ connection: { ...state.connection, ...conn } })),

      // ─── Paramètres ────────────────────────────────────────────────────
      updateSettings: (settings) =>
        set((state) => ({ settings: { ...state.settings, ...settings } })),

      // ─── Navigation ────────────────────────────────────────────────────
      setPage: (page) => set({ selectedPage: page }),

      // ─── Palette ───────────────────────────────────────────────────────
      setPalette: (id) => set({ palette: id }),

      // ─── Background ────────────────────────────────────────────────────
      setBgTheme: (id) => set({ bgTheme: id }),

      // ─── Getters dérivés ───────────────────────────────────────────────
      getActiveProfile: () =>
        get().profiles.find((p) => p.id === get().activeProfileId),

      getActiveCategory: () => {
        const profile = get().getActiveProfile();
        if (!profile) return undefined;
        return profile.categories.find(
          (c) => c.categoryId === get().activeCategoryId
        );
      },
    }),
    {
      name:    "kore-deck-store",
      storage: createJSONStorage(() => localStorage),
      // Ne pas persister les stats live ni la connexion
      partialize: (state) => ({
        profiles:        state.profiles,
        activeProfileId: state.activeProfileId,
        settings:        state.settings,
        palette:         state.palette,
        bgTheme:         state.bgTheme,
      }),
    }
  )
);
