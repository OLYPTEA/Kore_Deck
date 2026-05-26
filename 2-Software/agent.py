import argparse
import signal
import sys
import threading
import time

from config import config
from logger import log, setup_logger
from serial_manager import SerialManager
from system_monitor import SystemMonitor
from spotify_monitor import SpotifyMonitor
from audio_manager import AudioManager
from pomodoro import PomodoroTimer
from action_executor import ActionExecutor
from ws_bridge import WebSocketBridge

try:
    import winreg
except ImportError:
    winreg = None

try:
    import psutil
except ImportError:
    psutil = None


_OBS_PROCESS_NAMES = {"obs64.exe", "obs32.exe", "obs.exe"}


class KoreDeckAgent:
    def __init__(self) -> None:
        self._system = SystemMonitor()
        self._spotify = SpotifyMonitor()
        self._audion= AudioManager()
        self._pomodoro = PomodoroTimer()
        self._executor = ActionExecutor(self._audio, self._pomodoro)
        self._serial = SerialManager(on_line_received=self._on_line_received)

        self._bridge = WebSocketBridge()
        self._bridge.on_config_update = self._on_config_update
        self._bridge.on_action        = self._on_ui_action

        self._current_category : int  = 0    # 0=HOME 1=MAKING 2=FOCUS 3=GAME
        self._dnd_active : bool = False
        self._obs_active : bool = False

        self._last_send_time = 0.0
        self._last_spotify_time = 0.0
        self._last_fps_time = 0.0
        self._last_ws_push_time = 0.0
        self._last_pomo_tick = 0.0
        self._last_dnd_check = 0.0
        self._last_obs_check = 0.0
        # Re-lecture immédiate de l'état Windows après un toggle UI.
        self._last_dnd_toggle_seen = 0.0
        self._last_obs_toggle_seen = 0.0

        self._cached_track : str = "Aucune lecture"
        self._cached_fps : int = 0

        self._running : bool = False
        self._stop_event = threading.Event()

    #Cycle de vie

    def start(self) -> None:
        log.info("Kore Deck — Agent PC v2.0")
        log.info(f"Port : {config.serial.port} | WS : ws://{config.ws.host}:{config.ws.port}")

        self._bridge.start()
        self._serial.start()
        self._running = True
        self._bridge.send_agent_status("running")

        try:
            self._main_loop()
        except KeyboardInterrupt:
            log.info("Arrêt Ctrl+C")
        finally:
            self.stop()

    def stop(self) -> None:
        if not self._running:
            return
        self._running = False
        self._stop_event.set()
        self._bridge.send_agent_status("stopped")
        self._bridge.send_connection_status("disconnected")
        self._serial.stop()
        self._bridge.stop()
        log.info("Agent arrêté")

    #Boucle principale

    def _main_loop(self) -> None:
        while self._running and not self._stop_event.is_set():
            now = time.monotonic()

            if now - self._last_pomo_tick >= config.timing.pomodoro_tick:
                self._last_pomo_tick = now
                self._pomodoro.update()

            if now - self._last_spotify_time >= config.timing.spotify_interval:
                self._last_spotify_time = now
                self._cached_track = self._spotify.get_current_track()

            if now - self._last_fps_time >= config.timing.fps_interval:
                self._last_fps_time = now
                self._cached_fps = self._system.get_fps()

            if (now - self._last_dnd_check >= config.timing.dnd_check_interval
                    or self._executor.dnd_toggled_at > self._last_dnd_toggle_seen):
                self._last_dnd_check = now
                self._last_dnd_toggle_seen = self._executor.dnd_toggled_at
                self._dnd_active = self._refresh_dnd_state()

            if (now - self._last_obs_check >= config.timing.obs_check_interval
                    or self._executor.obs_toggled_at > self._last_obs_toggle_seen):
                self._last_obs_check = now
                self._last_obs_toggle_seen = self._executor.obs_toggled_at
                self._obs_active = self._refresh_obs_state()

            if now - self._last_send_time >= config.timing.send_interval:
                self._last_send_time = now
                if self._serial.is_connected():
                    self._send_system_frame()
                    self._bridge.send_connection_status("connected")
                else:
                    self._bridge.send_connection_status("disconnected")

            if now - self._last_ws_push_time >= config.timing.ui_push_interval:
                self._last_ws_push_time = now
                if self._bridge.get_client_count() > 0:
                    self._push_stats_to_ui()

            time.sleep(config.timing.main_loop_sleep)

    #DND / OBS (Windows)

    def _refresh_dnd_state(self) -> bool:
        # HKCU\Software\Microsoft\Windows\CurrentVersion\Notifications\Settings
        # NOC_GLOBAL_SETTING_TOAST_ENABLED : 0 = DND actif, 1 = notifs actives
        if winreg is None:
            return False
        try:
            key_path = r"Software\Microsoft\Windows\CurrentVersion\Notifications\Settings"
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path) as k:
                value, _ = winreg.QueryValueEx(k, "NOC_GLOBAL_SETTING_TOAST_ENABLED")
                return value == 0
        except (OSError, FileNotFoundError):
            return False

    def _refresh_obs_state(self) -> bool:
        if psutil is None:
            return False
        try:
            for proc in psutil.process_iter(['name']):
                name = (proc.info.get('name') or "").lower()
                if name in _OBS_PROCESS_NAMES:
                    return True
        except Exception:
            pass
        return False

    #Push vers l'UI

    def _push_stats_to_ui(self) -> None:
        cpu = self._system.get_cpu_usage()
        ram = self._system.get_ram_usage()
        mins, secs = self._pomodoro.get_remaining()
        sess = self._pomodoro.get_session_count()

        track  = self._cached_track
        artist = ""
        if " - " in track:
            artist, track = track.split(" - ", 1)

        self._bridge.send_stats({
            "cpu": cpu, "ram": ram, "fps": self._cached_fps,
            "mic": self._audio.is_mic_muted(),
            "dnd": self._dnd_active, "obs": self._obs_active,
            "track": f"{artist} - {track}" if artist else track,
            "pomo": {
                "min": mins, "sec": secs, "session": sess,
                "running": self._pomodoro.is_running(),
            },
        })

    # --- Trame série ESP32

    def _send_system_frame(self) -> None:
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

    #Réception ESP32 -> PC
    # Lignes attendues : ACTION:<name>[_LONG|_DBL], POT:<action>:<v>, CAT:<n>, READY, PING

    def _on_line_received(self, line: str) -> None:
        log.debug(f"← ESP32 : {line}")

        if line.startswith("ACTION:"):
            self._executor.execute_action(line[7:])

        elif line.startswith("POT:"):
            parts = line[4:].split(":")
            if len(parts) == 2:
                try:
                    self._executor.execute_pot(parts[0], int(parts[1]))
                except ValueError:
                    pass

        elif line.startswith("CAT:"):
            try:
                self._current_category = int(line[4:])
            except ValueError:
                pass

        elif line == "READY":
            log.info("ESP32 prêt")
            self._bridge.send_connection_status("connected")

        elif line == "PING":
            pass

    #Callbacks UI

    def _on_config_update(self, data: dict) -> None:
        log.info(f"Hot-reload config depuis UI : {list(data.keys())}")

    def _on_ui_action(self, action: str) -> None:
        log.info(f"Action UI : {action}")
        self._executor.execute_action(action)


def main() -> None:
    parser = argparse.ArgumentParser(description="Kore Deck — Agent PC v2.0")
    parser.add_argument("--port",  type=str, default=None,
                        help="Port série, ex: COM3 (écrase la config)")
    parser.add_argument("--debug", action="store_true",
                        help="Active le niveau DEBUG")
    args = parser.parse_args()

    if args.port:
        config.serial.port = args.port
    if args.debug:
        setup_logger(level="DEBUG")

    agent = KoreDeckAgent()

    def _sig(sig, frame):
        agent.stop()
        sys.exit(0)
    signal.signal(signal.SIGINT,  _sig)
    signal.signal(signal.SIGTERM, _sig)

    agent.start()


if __name__ == "__main__":
    main()
