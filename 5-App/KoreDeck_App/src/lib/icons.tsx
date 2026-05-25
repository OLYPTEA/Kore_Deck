// =============================================================================
// icons.tsx — Registre d'icônes Lucide indexées par nom (string)
// Permet de rendre une icône via {icon: "Play"} depuis le store.
// =============================================================================

import {
  // Boutons par défaut
  Play, Pause, SkipForward, SkipBack, Volume2, VolumeX,
  Mic, MicOff, Camera, Video, Monitor, Moon, Sun,
  Home, FolderOpen, Save, Undo2, Redo2, Plus, Minus,
  Scissors, FileOutput, BookOpen, Clock, RotateCcw, Target,
  BellOff, Bell, PanelLeft, PanelRight, LayoutGrid, Layers,
  Radio, Gamepad2, List, Keyboard, Terminal, Code2,
  Zap, Star, Heart, Coffee, Music, Headphones, Box,
  // UI extras
  Cpu, Database, Activity, Thermometer, Wifi, Clock4, CloudSun, User,
  SlidersHorizontal, X, Check, Pencil, Settings as SettingsIcon,
  Users, SquareDashed, GripVertical, Download, Copy, Share, Trash2,
  Plug, AppWindow, Microchip, Info, Palette, RefreshCw, Upload, RotateCw,
  ArrowDown, ArrowUp,
} from "lucide-react";
import type { LucideIcon } from "lucide-react";

const REGISTRY: Record<string, LucideIcon> = {
  Play, Pause, SkipForward, SkipBack, Volume2, VolumeX,
  Mic, MicOff, Camera, Video, Monitor, Moon, Sun,
  Home, FolderOpen, Save, Undo2, Redo2, Plus, Minus,
  Scissors, FileOutput, BookOpen, Clock, RotateCcw, Target,
  BellOff, Bell, PanelLeft, PanelRight, LayoutGrid, Layers,
  Radio, Gamepad2, List, Keyboard, Terminal, Code2,
  Zap, Star, Heart, Coffee, Music, Headphones, Box,
  Cpu, Database, Activity, Thermometer, Wifi, Clock4, CloudSun, User,
  SlidersHorizontal, X, Check, Pencil, SettingsIcon,
  Users, SquareDashed, GripVertical, Download, Copy, Share, Trash2,
  Plug, AppWindow, Microchip, Info, Palette, RefreshCw, Upload, RotateCw,
  ArrowDown, ArrowUp,
};

export function getIcon(name: string | undefined | null): LucideIcon {
  if (!name) return Zap;
  return REGISTRY[name] || Zap;
}

interface IconProps {
  name:        string;
  size?:       number;
  color?:      string;
  strokeWidth?:number;
  className?:  string;
}

export function NamedIcon({ name, size = 16, color = "currentColor", strokeWidth = 1.8, className }: IconProps) {
  const Cmp = getIcon(name);
  return <Cmp size={size} color={color} strokeWidth={strokeWidth} className={className} aria-hidden="true" />;
}

// Liste pour l'icon picker (modal)
export const ICON_NAMES = Object.keys(REGISTRY).filter((k) => k !== "SettingsIcon");
