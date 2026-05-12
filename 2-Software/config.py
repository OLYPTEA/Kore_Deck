# =============================================================================
# config.py — Configuration centralisée de l'agent PC StreamDeck
# =============================================================================

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class SerialConfig:
    """Configuration du port série vers l'ESP32."""
    port: str           = "COM3"       # À adapter selon le Gestionnaire de périphériques
    baud: int           = 115200
    timeout: float      = 1.0          # Timeout de lecture (secondes)
    reconnect_delay: float = 3.0       # Délai avant tentative de reconnexion


@dataclass
class TimingConfig:
    """Intervalles des tâches périodiques (secondes)."""
    send_interval: float    = 0.1      # Envoi trame système → ESP32 (100ms)
    spotify_interval: float = 2.0      # Rafraîchissement titre Spotify
    fps_interval: float     = 1.0      # Rafraîchissement FPS via HWiNFO


@dataclass
class AudioConfig:
    """Noms des processus audio Windows (pycaw)."""
    spotify_process: str  = "Spotify.exe"
    discord_process: str  = "Discord.exe"
    game_processes: list  = field(default_factory=lambda: [
        "EscapeFromTarkov.exe",
        "RainbowSix.exe",
        "valorant.exe",
        "cs2.exe",
        "VALORANT-Win64-Shipping.exe",
    ])


@dataclass
class PomodorConfig:
    """Paramètres par défaut du minuteur Pomodoro."""
    default_duration_min: int  = 25    # Durée par défaut (minutes)
    short_break_min: int       = 5
    long_break_min: int        = 15
    sessions_before_long: int  = 4


@dataclass
class AppConfig:
    """Configuration globale de l'application."""
    serial:   SerialConfig   = field(default_factory=SerialConfig)
    timing:   TimingConfig   = field(default_factory=TimingConfig)
    audio:    AudioConfig    = field(default_factory=AudioConfig)
    pomodoro: PomodorConfig  = field(default_factory=PomodorConfig)
    log_level: str           = "INFO"  # DEBUG / INFO / WARNING / ERROR


# Instance globale importable partout
config = AppConfig()
