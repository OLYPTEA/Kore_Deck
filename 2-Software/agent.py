# =============================================================================
# agent.py — le cerveau du truc
#
# C'est ici que tout se connecte. Chaque fichier fait un truc précis,
# ce fichier les fait tous tourner ensemble :
#   - SerialManager  : parle à l'ESP32 via USB
#   - WebSocketBridge: parle à l'interface Tauri
#   - SystemMonitor  : CPU / RAM / FPS
#   - SpotifyMonitor : récupère le titre en cours (sans API Spotify, on est malins)
#   - AudioManager   : contrôle les volumes Windows
#   - PomodoroTimer  : le minuteur, appelé dans la boucle principale
#   - ActionExecutor : traduit les actions bouton en vrais raccourcis clavier
# =============================================================================

import argparse, json, signal, sys, time, threading
from config          import config
from logger          import log, setup_logger
from serial_manager  import SerialManager
from system_monitor  import SystemMonitor
from spotify_monitor import SpotifyMonitor
from audio_manager   import AudioManager
from pomodoro        import PomodoroTimer
from action_executor import ActionExecutor
from ws_bridge       import WebSocketBridge


class KoreDeckAgent:
    """
    Classe centrale de l'agent. Chaque sous-système est instancié une fois
    et partagé via injection de dépendance (pas de singletons globaux).
    """

    def __init__(self) -> None:
        # --- Sous-systèmes indépendants
        self._system    = SystemMonitor()
        self._spotify   = SpotifyMonitor()
        self._audio     = AudioManager()
        self._pomodoro  = PomodoroTimer()

        # ActionExecutor a besoin d'AudioManager et PomodoroTimer pour les contrôler
        self._executor  = ActionExecutor(self._audio, self._pomodoro)

        # SerialManager appelle _on_line_received à chaque ligne reçue de l'ESP32
        self._serial    = SerialManager(on_line_received=self._on_line_received)

        # WebSocketBridge écoute sur ws://localhost:8765, notifie via callbacks
        self._bridge    = WebSocketBridge()
        self._bridge.on_config_update = self._on_config_update
        self._bridge.on_action        = self._on_ui_action

        # État applicatif
        self._current_category : int  = 0      # 0=HOME 1=MAKING 2=FOCUS 3=GAME
        self._dnd_active       : bool = False   # Do Not Disturb Windows
        self._obs_active       : bool = False   # OBS en cours d'enregistrement

        # timestamps pour pas spammer à chaque tick
        self._last_send_time    = self._last_spotify_time = 0.0
        self._last_fps_time     = self._last_ws_push_time = 0.0

        # on cache ces valeurs car les relire à chaque tick c'est trop lent
        self._cached_track : str = "Aucune lecture"
        self._cached_fps   : int = 0

        self._running    : bool = False
        self._stop_event = threading.Event()

    # =========================================================================
    # Cycle de vie
    # =========================================================================

    def start(self) -> None:
        """Lance le bridge WS, les threads série, puis entre dans la boucle principale."""
        log.info("=" * 60)
        log.info("Kore Deck — Agent PC v2.0")
        log.info(f"Port : {config.serial.port} | WS : ws://localhost:8765")
        log.info("=" * 60)

        self._bridge.start()   # Lance le serveur WebSocket dans son thread
        self._serial.start()   # Lance les threads reader/writer série
        self._running = True
        self._bridge.send_agent_status("running")

        try:
            self._main_loop()
        except KeyboardInterrupt:
            log.info("Arrêt Ctrl+C")
        finally:
            self.stop()

    def stop(self) -> None:
        """Arrêt propre : notifie l'UI, puis ferme les connexions dans l'ordre."""
        self._running = False
        self._bridge.send_agent_status("stopped")
        self._bridge.send_connection_status("disconnected")
        self._serial.stop()    # Ferme le port série (join des threads)
        self._bridge.stop()    # Ferme le serveur WebSocket
        log.info("Agent arrêté")

    # =========================================================================
    # Boucle principale
    # =========================================================================

    def _main_loop(self) -> None:
        """
        La boucle principale. Tourne à ~200 Hz (sleep 5 ms entre chaque tour).
        Chaque tâche a son propre timer pour pas tout faire en même temps.

        qui fait quoi et à quelle fréquence :
          - pomodoro.update()   → chaque tick  (faut pas rater la fin d'une session)
          - Spotify             → toutes les 2 s  (l'API WinRT est pas rapide)
          - FPS via HWiNFO      → toutes les 1 s
          - trame vers ESP32    → toutes les 100 ms
          - stats vers l'UI     → toutes les 200 ms  (inutile d'aller plus vite)
        """
        while self._running and not self._stop_event.is_set():
            now = time.monotonic()   # Monotonic : immunisé aux changements d'heure système

            # --- Tick Pomodoro (détecte les fins de session)
            self._pomodoro.update()

            # --- Rafraîchissement titre Spotify (opération lente → cache)
            if now - self._last_spotify_time >= config.timing.spotify_interval:
                self._last_spotify_time = now
                self._cached_track = self._spotify.get_current_track()

            # --- Rafraîchissement FPS HWiNFO (shared memory → cache)
            if now - self._last_fps_time >= config.timing.fps_interval:
                self._last_fps_time = now
                self._cached_fps = self._system.get_fps()

            # --- Envoi trame système vers l'ESP32 (toutes les 100 ms)
            if now - self._last_send_time >= config.timing.send_interval:
                self._last_send_time = now
                if self._serial.is_connected():
                    self._send_system_frame()
                    self._bridge.send_connection_status("connected")
                else:
                    self._bridge.send_connection_status("disconnected")

            # --- Push stats vers l'interface Tauri (toutes les 200 ms)
            if now - self._last_ws_push_time >= 0.2:
                self._last_ws_push_time = now
                if self._bridge.get_client_count() > 0:   # Inutile de sérialiser si personne n'écoute
                    self._push_stats_to_ui()

            # sans ce sleep Python bouffe 100% CPU pour rien
            time.sleep(0.005)

    # =========================================================================
    # Push données vers l'UI
    # =========================================================================

    def _push_stats_to_ui(self) -> None:
        """
        Construit le payload JSON de stats et le diffuse via WebSocket.
        Sépare "Artiste - Titre" en deux champs si le format est respecté.
        """
        cpu  = self._system.get_cpu_usage()
        ram  = self._system.get_ram_usage()
        mins, secs = self._pomodoro.get_remaining()
        sess = self._pomodoro.get_session_count()

        # Sépare "Artiste - Titre" si le séparateur " - " est présent
        track = self._cached_track
        artist = ""
        if " - " in track:
            parts = track.split(" - ", 1)   # maxsplit=1 pour éviter les splits multiples
            artist, track = parts[0], parts[1]

        self._bridge.send_stats({
            "cpu": cpu, "ram": ram, "fps": self._cached_fps,
            "mic": self._audio.is_mic_muted(),
            "dnd": self._dnd_active, "obs": self._obs_active,
            "track": f"{artist} - {track}" if artist else track,
            "pomo": {
                "min": mins, "sec": secs, "session": sess,
                "running": self._pomodoro.is_running()
            },
        })

    # =========================================================================
    # Envoi trame série vers l'ESP32
    # =========================================================================

    def _send_system_frame(self) -> None:
        """
        Construit et envoie la trame texte vers l'ESP32.

        Format : CPU:<n>|RAM:<n.n>|TRACK:<str>|FPS:<n>|MIC:<0|1>|DND:<0|1>|OBS:<0|1>|POMO:<mm>:<ss>:<session>
        Exemple : CPU:45|RAM:61.2|TRACK:Daft Punk - Harder|FPS:120|MIC:0|DND:0|OBS:1|POMO:22:30:2

        Le firmware parse cette trame dans protocol.cpp (FrameParser::parse).
        """
        cpu  = self._system.get_cpu_usage()
        ram  = self._system.get_ram_usage()
        mins, secs = self._pomodoro.get_remaining()
        sess = self._pomodoro.get_session_count()

        frame = (f"CPU:{cpu}|RAM:{ram:.1f}|TRACK:{self._cached_track}"
                 f"|FPS:{self._cached_fps}"
                 f"|MIC:{1 if self._audio.is_mic_muted() else 0}"
                 f"|DND:{1 if self._dnd_active else 0}"
                 f"|OBS:{1 if self._obs_active else 0}"
                 f"|POMO:{mins}:{secs}:{sess}")
        self._serial.send(frame)

    # =========================================================================
    # Réception des trames ESP32 → PC
    # =========================================================================

    def _on_line_received(self, line: str) -> None:
        """
        Callback appelé par SerialManager pour chaque ligne reçue de l'ESP32.
        Appelé depuis le thread 'serial-reader' — ne pas bloquer ici.

        Ce que l'ESP32 peut envoyer :
          ACTION:<name>          → bouton appuyé,  ex: ACTION:MEDIA_PLAY
          ACTION:<name>_LONG     → appui long,      ex: ACTION:MUTE_LONG
          ACTION:<name>_DBL      → double appui
          POT:<action>:<0-100>   → pot bougé,       ex: POT:VOL_MASTER:73
          CAT:<0-3>              → changement de catégorie
          READY                  → l'ESP32 a fini de booter
          PING                   → il est encore vivant (on ignore, c'est juste un keepalive)
        """
        log.debug(f"← ESP32 : {line}")

        if line.startswith("ACTION:"):
            # Extrait le nom de l'action (tout ce qui suit "ACTION:")
            self._executor.execute_action(line[7:])

        elif line.startswith("POT:"):
            # Format attendu : POT:<action>:<valeur_entière_0-100>
            parts = line[4:].split(":")
            if len(parts) == 2:
                try:
                    self._executor.execute_pot(parts[0], int(parts[1]))
                except ValueError:
                    pass   # Valeur non entière → on ignore silencieusement

        elif line.startswith("CAT:"):
            # L'ESP32 confirme le changement de catégorie (suite à enterCategory())
            try:
                self._current_category = int(line[4:])
            except ValueError:
                pass

        elif line == "READY":
            # L'ESP32 vient de booter — signaler la connexion à l'UI immédiatement
            log.info("ESP32 prêt")
            self._bridge.send_connection_status("connected")

        elif line == "PING":
            pass   # Heartbeat reçu — rien à faire, la présence du message suffit

    # =========================================================================
    # Callbacks depuis l'UI (WebSocket → agent)
    # =========================================================================

    def _on_config_update(self, data: dict) -> None:
        """
        L'UI a changé un paramètre (port, baud, etc.).
        TODO: appliquer vraiment les changements sans redémarrer l'agent
        """
        log.info(f"Hot-reload config depuis UI")

    def _on_ui_action(self, action: str) -> None:
        """
        Appelé quand l'UI envoie { "type": "action", "action": "<name>" }.
        Permet à l'interface de déclencher des actions sans passer par l'ESP32.
        """
        log.info(f"Action UI : {action}")
        self._executor.execute_action(action)   # Même pipeline que les actions bouton


# =============================================================================
# Point d'entrée CLI
# =============================================================================

def main() -> None:
    parser = argparse.ArgumentParser(description="Kore Deck — Agent PC v2.0")
    parser.add_argument("--port",  type=str, default=None,
                        help="Port série à utiliser, ex: COM3 (écrase la config)")
    parser.add_argument("--debug", action="store_true",
                        help="Active le niveau DEBUG pour les logs détaillés")
    args = parser.parse_args()

    # Surcharge de la config au runtime si argument fourni
    if args.port:  config.serial.port = args.port
    if args.debug: setup_logger(level="DEBUG")

    agent = KoreDeckAgent()

    # Gestionnaire de signal pour arrêt propre via Ctrl+C ou SIGTERM (ex: systemd)
    def _sig(sig, frame):
        agent.stop()
        sys.exit(0)
    signal.signal(signal.SIGINT,  _sig)
    signal.signal(signal.SIGTERM, _sig)

    agent.start()   # Bloque ici jusqu'à l'arrêt


if __name__ == "__main__":
    main()
