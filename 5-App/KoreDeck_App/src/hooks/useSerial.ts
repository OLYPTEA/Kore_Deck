// =============================================================================
// hooks/useSerial.ts — Connexion WebSocket vers l'agent Python (bridge ws_bridge.py)
// =============================================================================

import { useEffect, useRef, useCallback } from "react";
import { useStore } from "@/store";

const WS_URL             = "ws://localhost:8765";
const RECONNECT_DELAY_MS = 3000;

// ─── Singleton WS partagé ────────────────────────────────────────────────────
// useSerial() est appelé une seule fois (dans App.tsx), mais d'autres composants
// — boutons média, toggles, etc. — doivent pouvoir envoyer des actions à l'agent
// sans recevoir le hook par prop drilling. On expose donc l'instance WS active
// au niveau module et un helper `sendAction()` qui s'occupe du framing JSON.
let wsInstance: WebSocket | null = null;

/**
 * Envoie une action au format attendu par ws_bridge.py :
 *   { "type": "action", "action": "MEDIA_PLAY" }
 * Silencieux (warn) si la connexion n'est pas ouverte — évite de planter l'UI.
 */
export function sendAction(action: string): void {
  if (wsInstance?.readyState === WebSocket.OPEN) {
    wsInstance.send(JSON.stringify({ type: "action", action }));
  } else {
    console.warn("[Kore Deck] WS non connecté — action ignorée :", action);
  }
}

export function useSerial() {
  const wsRef      = useRef<WebSocket | null>(null);
  const retryRef   = useRef<ReturnType<typeof setTimeout> | null>(null);
  const mountedRef = useRef(true);

  const updateStats   = useStore(s => s.updateStats);
  const setConnection = useStore(s => s.setConnectionStatus);
  const settings      = useStore(s => s.settings);

  // Ref pour accéder aux settings les plus récents depuis les callbacks WS
  // sans recréer handleMessage/connect à chaque changement de settings.
  const settingsRef = useRef(settings);
  useEffect(() => { settingsRef.current = settings; }, [settings]);

  // ─── Parsing des messages JSON du bridge ──────────────────────────────────
  const handleMessage = useCallback((raw: string) => {
    try {
      const msg = JSON.parse(raw);
      const s   = settingsRef.current;   // toujours les settings à jour

      switch (msg.type) {

        case "stats": {
          const p      = msg.payload;
          const parts  = (p.track ?? "").split(" - ");
          const artist = parts.length > 1 ? parts[0] : "";
          const title  = parts.length > 1 ? parts[1] : parts[0];
          updateStats({
            cpu:         p.cpu   ?? 0,
            ram:         p.ram   ?? 0,
            fps:         p.fps   ?? 0,
            micMuted:    p.mic   ?? false,
            dndActive:   p.dnd   ?? false,
            obsActive:   p.obs   ?? false,
            trackTitle:  title   || "Aucune lecture",
            trackArtist: artist  || "",
            pomoMinutes: p.pomo?.min     ?? 0,
            pomoSeconds: p.pomo?.sec     ?? 0,
            pomoSession: p.pomo?.session ?? 0,
            pomoRunning: p.pomo?.running ?? false,
          });
          break;
        }

        case "connection":
          setConnection({
            status:   msg.payload === "connected" ? "connected" : "disconnected",
            port:     s.serialPort,
            baud:     s.baudRate,
            lastSeen: msg.payload === "connected" ? new Date() : null,
          });
          break;

        case "agent":
          if (msg.payload === "stopped") {
            setConnection({ status: "disconnected" });
          }
          break;
      }
    } catch {
      // Message non-JSON ignoré silencieusement
    }
  }, [updateStats, setConnection]);   // deps stables — settingsRef via ref

  // ─── Connexion WebSocket ───────────────────────────────────────────────────
  const connect = useCallback(() => {
    if (!mountedRef.current) return;

    const ws = new WebSocket(WS_URL);
    wsRef.current = ws;
    wsInstance    = ws;   // Partage la connexion avec sendAction()

    ws.onopen = () => {
      if (!mountedRef.current) return;
      setConnection({ status: "connected" });
      ws.send(JSON.stringify({ type: "hello", version: "2.0" }));
    };

    ws.onmessage = e => handleMessage(e.data);

    ws.onclose = () => {
      if (wsInstance === ws) wsInstance = null;   // évite d'utiliser un WS fermé
      if (!mountedRef.current) return;
      setConnection({ status: "disconnected" });
      if (settingsRef.current.autoReconnect) {
        setConnection({ status: "reconnecting" });
        retryRef.current = setTimeout(connect, RECONNECT_DELAY_MS);
      }
    };

    ws.onerror = () => ws.close();
  }, [handleMessage, setConnection]);

  // ─── Envoi vers l'agent ────────────────────────────────────────────────────
  const send = useCallback((message: object) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify(message));
    }
  }, []);

  const sendConfigUpdate = useCallback((data: object) => {
    send({ type: "config_update", data });
  }, [send]);

  // ─── Cycle de vie ─────────────────────────────────────────────────────────
  useEffect(() => {
    mountedRef.current = true;
    connect();
    return () => {
      mountedRef.current = false;
      if (retryRef.current) clearTimeout(retryRef.current);
      wsRef.current?.close();
    };
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  return { send, sendConfigUpdate };
}
