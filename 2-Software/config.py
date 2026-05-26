from dataclasses import dataclass, field
from typing import List


def _clamp(value, lo, hi, name: str):
    if value < lo or value > hi:
        raise ValueError(f"{name}={value} hors plage [{lo}, {hi}]")
    return value


@dataclass
class SerialConfig:
    port : str = "COM3"
    baud : int = 115200
    timeout : float = 1.0
    reconnect_delay : float = 3.0

    def __post_init__(self) -> None:
        if not self.port:
            raise ValueError("serial.port ne peut pas être vide")
        _clamp(self.baud, 9600, 921600, "serial.baud")
        _clamp(self.timeout,0.05, 60.0,   "serial.timeout")
        _clamp(self.reconnect_delay, 0.5,  60.0,   "serial.reconnect_delay")


@dataclass
class TimingConfig:
    send_interval : float = 0.1
    spotify_interval : float = 2.0
    fps_interval : float = 1.0
    ui_push_interval : float = 0.2
    pomodoro_tick : float = 0.25
    main_loop_sleep : float = 0.005
    dnd_check_interval : float = 10.0
    obs_check_interval : float = 15.0

    def __post_init__(self) -> None:
        _clamp(self.send_interval, 0.01, 5.0,"timing.send_interval")
        _clamp(self.spotify_interval, 0.5,60.0,"timing.spotify_interval")
        _clamp(self.fps_interval, 0.1,60.0,"timing.fps_interval")
        _clamp(self.ui_push_interval, 0.05,5.0,"timing.ui_push_interval")
        _clamp(self.pomodoro_tick, 0.05, 1.0,"timing.pomodoro_tick")
        _clamp(self.main_loop_sleep, 0.001, 0.1,"timing.main_loop_sleep")
        _clamp(self.dnd_check_interval, 1.0, 120.0,"timing.dnd_check_interval")
        _clamp(self.obs_check_interval, 1.0, 120.0,"timing.obs_check_interval")


@dataclass
class AudioConfig:
    # game_processes : priorité descendante — premier process trouvé = volume jeu actif
    spotify_process : strn= "Spotify.exe"
    discord_process : str = "Discord.exe"
    game_processes : List[str] = field(default_factory=lambda: [
        "EscapeFromTarkov.exe",
        "RainbowSix.exe",
        "valorant.exe",
        "cs2.exe",
        "VALORANT-Win64-Shipping.exe",
    ])
    # Évite d'énumérer toutes les sessions Windows à chaque mouvement de pot.
    session_cache_ttl : float = 2.0

    def __post_init__(self) -> None:
        _clamp(self.session_cache_ttl, 0.1, 30.0, "audio.session_cache_ttl")


@dataclass
class PomodorConfig:
    default_duration_min : int = 25
    short_break_minn: int = 5
    long_break_minn: int = 15
    sessions_before_long : int = 4

    def __post_init__(self) -> None:
        _clamp(self.default_duration_min, 1, 240, "pomodoro.default_duration_min")
        _clamp(self.short_break_minn,1, 60,  "pomodoro.short_break_minn")
        _clamp(self.long_break_minn,1, 120, "pomodoro.long_break_minn")
        _clamp(self.sessions_before_long, 1, 20, "pomodoro.sessions_before_long")


@dataclass
class WebSocketConfig:
    host: str   = "localhost"   # pas d'auth — ne pas binder sur 0.0.0.0
    port : int   = 8765
    ping_intervaln: float = 20.0
    ping_timeoutn: float = 10.0
    max_message_size : int   = 16 * 1024

    def __post_init__(self) -> None:
        if not self.host:
            raise ValueError("ws.host ne peut pas être vide")
        _clamp(self.port,1024, 65535,"ws.port")
        _clamp(self.ping_intervaln, 1.0,  300.0,"ws.ping_interval")
        _clamp(self.ping_timeoutn,1.0,  300.0,"ws.ping_timeout")
        _clamp(self.max_message_size, 256, 1048576, "ws.max_message_size")


@dataclass
class AppConfig:
    serial : SerialConfig = field(default_factory=SerialConfig)
    timing : TimingConfig = field(default_factory=TimingConfig)
    audio : AudioConfig = field(default_factory=AudioConfig)
    pomodoro : PomodorConfig   = field(default_factory=PomodorConfig)
    ws : WebSocketConfig = field(default_factory=WebSocketConfig)
    log_level : str = "INFO"

    def __post_init__(self) -> None:
        valid = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}
        if self.log_level.upper() not in valid:
            raise ValueError(f"log_level={self.log_level!r} doit être l'un de {valid}")


config = AppConfig()
