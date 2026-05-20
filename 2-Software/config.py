# =============================================================================
# config.py — tous les paramètres de l'agent au même endroit
#
# dataclasses typées avec valeurs par défaut. une instance globale "config"
# est importée partout :
#   from config import config
#   config.serial.port          → "COM3"
#   config.timing.send_interval → 0.1
#
# pour changer un paramètre depuis argparse ou l'UI :
#   config.serial.port = "COM7"   # ça s'applique immédiatement
#
# si un jour on veut charger ça depuis un fichier JSON externe,
# il suffit de remplacer AppConfig() par un loader en bas du fichier.
# =============================================================================

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class SerialConfig:
    """Paramètres de la liaison UART vers l'ESP32."""

    port            : str   = "COM3"    # Port COM à adapter selon le Gestionnaire de périphériques
                                        # Vérifier : Device Manager → Ports (COM & LPT)
    baud            : int   = 115200    # Doit correspondre exactement au Serial.begin() firmware
    timeout         : float = 1.0       # Timeout readline() en secondes (évite le blocage infini)
    reconnect_delay : float = 3.0       # Délai entre deux tentatives de reconnexion (secondes)


@dataclass
class TimingConfig:
    """
    Intervalles des tâches périodiques de la boucle principale (en secondes).
    Augmenter ces valeurs réduit la charge CPU de l'agent.
    """

    send_interval    : float = 0.1   # Fréquence d'envoi trame système → ESP32 (100 ms = 10 Hz)
    spotify_interval : float = 2.0   # Rafraîchissement titre Spotify (API WinRT assez lente)
    fps_interval     : float = 1.0   # Rafraîchissement FPS HWiNFO (shared memory)


@dataclass
class AudioConfig:
    """
    Noms des processus Windows pour le contrôle de volume applicatif.
    Ces noms sont comparés insensiblement à la casse par AudioManager.

    game_processes : liste prioritaire — le premier trouvé en cours d'exécution
                     est contrôlé par le potentiomètre VOL_GAME.
                     Ajouter ici tout nouveau jeu à supporter.
    """

    spotify_process : str  = "Spotify.exe"
    discord_process : str  = "Discord.exe"
    game_processes  : list = field(default_factory=lambda: [
        "EscapeFromTarkov.exe",
        "RainbowSix.exe",
        "valorant.exe",
        "cs2.exe",
        "VALORANT-Win64-Shipping.exe",
    ])


@dataclass
class PomodorConfig:
    """
    Paramètres du cycle Pomodoro.
    Modifiables via l'UI Settings ou via le potentiomètre POMO_DURATION (durée seulement).
    """

    default_duration_min  : int = 25   # Durée d'une session de travail (minutes)
    short_break_min       : int = 5    # Pause courte après chaque session
    long_break_min        : int = 15   # Pause longue après sessions_before_long sessions
    sessions_before_long  : int = 4    # Nombre de sessions avant pause longue


@dataclass
class AppConfig:
    """
    Regroupe toutes les sous-configs.
    On utilise field(default_factory=...) pour les objets imbriqués —
    c'est le piège classique des dataclasses Python avec des valeurs mutables par défaut.
    """

    serial   : SerialConfig  = field(default_factory=SerialConfig)
    timing   : TimingConfig  = field(default_factory=TimingConfig)
    audio    : AudioConfig   = field(default_factory=AudioConfig)
    pomodoro : PomodorConfig = field(default_factory=PomodorConfig)

    # Niveau de log : "DEBUG" pour le développement, "INFO" pour la production
    log_level : str = "INFO"


# l'instance globale — tout le monde fait "from config import config"
config = AppConfig()
