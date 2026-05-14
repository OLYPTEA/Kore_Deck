# agent.py — Agent PC principal de Kore Deck
#
# Point d'entrée unique. Orchestre tous les modules :
#   - SerialManager    : communication ESP32 <=> PC
#   - SystemMonitor    : CPU, RAM, FPS
#   - SpotifyMonitor   : titre en cours de lecture
#   - AudioManager     : volumes et micro
#   - PomodoroTimer    : minuteur Pomodoro
#   - ActionExecutor   : exécution des actions boutons/potards
#
# Lancement :
#   python agent.py
#   python agent.py --port COM5
#   python agent.py --port COM3 --debug


"""
Configuration requise (config.py) :
- serial: port (str), baud (int)
- timing: spotify_interval, fps_interval, send_interval (float)
- log_level: (str) "INFO", "DEBUG"...
"""


import argparse
import signal
import sys
import time
import threading
from typing import Optional

from config     import config
from logger     import log, setup_logger
from serial_manager  import SerialManager
from system_monitor  import SystemMonitor
from spotify_monitor import SpotifyMonitor
from audio_manager   import AudioManager
from pomodoro        import PomodoroTimer
from action_executor import ActionExecutor


# ─────────────────────────────────────────────────────────────────────────────
class StreamDeckAgent:
    """
    Agent principal du StreamDeck DIY.
    Orchestre la collecte des données système et l'exécution des actions.
    """

    def __init__(self) -> None:
        #  Modules métier
        self._system    = SystemMonitor()
        self._spotify   = SpotifyMonitor()
        self._audio     = AudioManager()
        self._pomodoro  = PomodoroTimer()
        self._executor  = ActionExecutor(self._audio, self._pomodoro)

        #  Communication série
        self._serial    = SerialManager(on_line_received=self._on_line_received)

        # --- État interne
        self._current_category  : int  = 0
        self._mic_muted         : bool = False
        self._dnd_active        : bool = False
        self._obs_active        : bool = False

        #  Timings pour les tâches périodiques lentes
        self._last_send_time    : float = 0.0
        self._last_spotify_time : float = 0.0
        self._last_fps_time     : float = 0.0

        #  Cache des données lentes (mises à jour moins souvent)
        self._cached_track      : str   = "Aucune lecture"
        self._cached_fps        : int   = 0

        #  Arrêt
        self._running           : bool  = False
        self._stop_event        = threading.Event()

    
    # Cycle de vie 
   

    def start(self) -> None:
        """Démarre l'agent et entre dans la boucle principale."""
        log.info("=" * 60)
        log.info("StreamDeck DIY — Agent PC v2.0")
        log.info(f"Port : {config.serial.port} | Baud : {config.serial.baud}")
        log.info("=" * 60)

        self._serial.start()
        self._running = True

        try:
            self._main_loop()
        except KeyboardInterrupt:
            log.info("Arrêt demandé (Ctrl+C)")
        finally:
            self.stop()

    def stop(self) -> None:
        """Arrêt propre de tous les modules."""
        self._running = False
        self._serial.stop()
        log.info("Agent arrêté proprement")

    
    # Boucle principale
    

    def _main_loop(self) -> None:
        """
        Boucle principale non-bloquante.
        Cadencée à ~200 Hz pour réactivité maximale.
        """
        while self._running and not self._stop_event.is_set():
            now = time.monotonic()

            #  Tâche 1 : Mise à jour Pomodoro (toutes les itérations)
            self._pomodoro.update()

            #  Tâche 2 : Rafraîchissement titre Spotify (toutes les 2s)
            if now - self._last_spotify_time >= config.timing.spotify_interval:
                self._last_spotify_time = now
                self._cached_track = self._spotify.get_current_track()

            #  Tâche 3 : Rafraîchissement FPS (toutes les 1s)
            if now - self._last_fps_time >= config.timing.fps_interval:
                self._last_fps_time = now
                self._cached_fps = self._system.get_fps()

            #  Tâche 4 : Envoi trame système → ESP32 (toutes les 100ms)
            if now - self._last_send_time >= config.timing.send_interval:
                self._last_send_time = now
                if self._serial.is_connected():
                    self._send_system_frame()

            time.sleep(0.005)  # empêche la boucle de tourner à 100% CPU, mais ça reste très réactif (200 Hz)

    
    # Construction et envoi de la trame système (note à moi même : à voir si on peut faire mieux que 100ms, genre 50ms ?) -> à tester, mais je pense que 100ms c'est déjà très fluide et ça laisse plus de temps pour les autres tâches
    # Attention risque de saturer si on envoie trop vite et que l'ESP32 n'arrive pas à suivre, d'où l'idée de faire du 50ms seulement si l'écran (DWIN/Nextion) suit, sinon rester à 100ms pour éviter les pertes de trames

    def _send_system_frame(self) -> None:
        """
        Construit et envoie la trame ASCII vers l'ESP32.
        Format : CPU:34|RAM:11.2|TRACK:Artist - Title|FPS:144|MIC:0|DND:1|OBS:1|POMO:24:13:3     
        """
        cpu  = self._system.get_cpu_usage()  
        ram  = self._system.get_ram_usage()
        mins, secs = self._pomodoro.get_remaining()
        sess = self._pomodoro.get_session_count()

        frame = (
            f"CPU:{cpu}"
            f"|RAM:{ram:.1f}"
            f"|TRACK:{self._cached_track}"
            f"|FPS:{self._cached_fps}"
            f"|MIC:{1 if self._audio.is_mic_muted() else 0}"
            f"|DND:{1 if self._dnd_active else 0}"
            f"|OBS:{1 if self._obs_active else 0}"
            f"|POMO:{mins}:{secs}:{sess}"
        )

        self._serial.send(frame)
        log.debug(f"→ ESP32 : {frame}")

   
    # Réception des trames ESP32 → PC
   

    def _on_line_received(self, line: str) -> None:
        """
        Callback appelé par SerialManager pour chaque ligne reçue.
        Parse et dispatche les commandes ESP32.
        """
        log.debug(f"← ESP32 : {line}")

        if line.startswith("ACTION:"):
            action = line[7:]
            self._executor.execute_action(action)

        elif line.startswith("POT:"):
            # Format : POT:VOL_MASTER:72
            parts = line[4:].split(':')
            if len(parts) == 2:
                try:
                    self._executor.execute_pot(parts[0], int(parts[1]))
                except ValueError:
                    log.warning(f"Valeur pot invalide : {line}")

        elif line.startswith("CAT:"):
            try:
                cat = int(line[4:])
                self._current_category = cat
                log.info(f"Catégorie active → {cat}")
            except ValueError:
                log.warning(f"Catégorie invalide : {line}")

        elif line.startswith("NAV:HOME"):
            log.info("Navigation vers accueil DWIN")

        elif line == "READY":
            log.info("ESP32 prêt — démarrage de l'envoi des données")

        else:
            log.debug(f"Trame non reconnue : {line}")



# Point d'entrée


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="StreamDeck DIY — Agent PC"
    )
    parser.add_argument(
        "--port", type=str, default=None,
        help="Port COM de l'ESP32 (ex: COM3 ou /dev/ttyUSB0)"
    )
    parser.add_argument(
        "--debug", action="store_true",
        help="Active les logs DEBUG"
    )
    return parser.parse_args()


def main() -> None:
    args = _parse_args()

    # Surcharge config depuis les arguments CLI
    if args.port:
        config.serial.port = args.port
    if args.debug:
        config.log_level = "DEBUG"
        setup_logger(level="DEBUG")

    agent = StreamDeckAgent()

    # Gestion du signal SIGINT (Ctrl+C) pour arrêt propre
    def _signal_handler(sig, frame):
        log.info("Signal reçu — arrêt en cours...")
        agent.stop()
        sys.exit(0)

    signal.signal(signal.SIGINT,  _signal_handler)
    signal.signal(signal.SIGTERM, _signal_handler)

    agent.start()


if __name__ == "__main__":
    main()


# --- TODO pour le prochain dev <3 ---
# 1  Passer l'envoi de la trame à 50ms si l'écran (DWIN/Nextion) suit.
# 2  Ajouter une vérification (checksum) sur les trames reçues de l'ESP32.
# 3  Permettre le changement de catégorie (CAT) via le clavier du PC.