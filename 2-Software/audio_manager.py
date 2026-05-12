# =============================================================================
# audio_manager.py — Contrôle audio Windows via pycaw
#
# Fonctionnalités :
#   - Volume master système
#   - Volume par application (Spotify, Discord, jeux)
#   - Mute/unmute microphone
#   - Gain microphone
# =============================================================================

import comtypes
from ctypes import POINTER, cast
from typing import Optional

from pycaw.pycaw import (
    AudioUtilities,
    IAudioEndpointVolume,
    ISimpleAudioVolume,
)
from pycaw.constants import CLSID_MMDeviceEnumerator
from comtypes import CLSCTX_ALL

from logger import log
from config import config


class AudioManager:
    """
    Gestionnaire audio Windows via pycaw.
    Gère le volume master, les volumes applicatifs et le microphone.
    """

    def __init__(self) -> None:
        self._master_volume: Optional[IAudioEndpointVolume] = None
        self._mic_volume: Optional[IAudioEndpointVolume]    = None
        self._mic_muted: bool = False
        self._init_master()
        self._init_microphone()

    # =========================================================================
    # Volume Master
    # =========================================================================

    def set_master_volume(self, percent: int) -> None:
        """
        Définit le volume master système.
        @param percent  Valeur 0-100
        """
        percent = max(0, min(100, percent))
        try:
            if self._master_volume:
                self._master_volume.SetMasterVolumeLevelScalar(
                    percent / 100.0, None
                )
                log.debug(f"Volume master → {percent}%")
        except Exception as e:
            log.error(f"set_master_volume({percent}) : {e}")

    def get_master_volume(self) -> int:
        """Retourne le volume master actuel (0-100)."""
        try:
            if self._master_volume:
                scalar = self._master_volume.GetMasterVolumeLevelScalar()
                return int(scalar * 100)
        except Exception as e:
            log.error(f"get_master_volume : {e}")
        return 0

    # =========================================================================
    # Volume applicatif
    # =========================================================================

    def set_app_volume(self, process_name: str, percent: int) -> bool:
        """
        Définit le volume d'une application par nom de processus.
        @param process_name  Ex: "Spotify.exe"
        @param percent       0-100
        @return True si l'application a été trouvée
        """
        percent = max(0, min(100, percent))
        try:
            sessions = AudioUtilities.GetAllSessions()
            for session in sessions:
                if session.Process and \
                   session.Process.name().lower() == process_name.lower():
                    volume = session._ctl.QueryInterface(ISimpleAudioVolume)
                    volume.SetMasterVolume(percent / 100.0, None)
                    log.debug(f"Volume {process_name} → {percent}%")
                    return True
        except Exception as e:
            log.error(f"set_app_volume({process_name}, {percent}) : {e}")
        return False

    def set_game_volume(self, percent: int) -> None:
        """
        Définit le volume du premier jeu détecté dans la liste de processus.
        """
        for proc in config.audio.game_processes:
            if self.set_app_volume(proc, percent):
                return
        log.debug("Aucun processus jeu actif trouvé")

    def set_spotify_volume(self, percent: int) -> None:
        self.set_app_volume(config.audio.spotify_process, percent)

    def set_discord_volume(self, percent: int) -> None:
        self.set_app_volume(config.audio.discord_process, percent)

    # =========================================================================
    # Microphone
    # =========================================================================

    def toggle_mic_mute(self) -> bool:
        """
        Bascule le mute du microphone par défaut.
        @return Nouvel état (True = muté)
        """
        try:
            if self._mic_volume:
                self._mic_muted = not self._mic_muted
                self._mic_volume.SetMute(int(self._mic_muted), None)
                log.info(f"Micro {'muté' if self._mic_muted else 'actif'}")
        except Exception as e:
            log.error(f"toggle_mic_mute : {e}")
        return self._mic_muted

    def is_mic_muted(self) -> bool:
        """Retourne l'état actuel du mute microphone."""
        try:
            if self._mic_volume:
                return bool(self._mic_volume.GetMute())
        except Exception:
            pass
        return self._mic_muted

    def set_mic_gain(self, percent: int) -> None:
        """
        Définit le gain du microphone (0-100 → 0.0-1.0 scalar).
        """
        percent = max(0, min(100, percent))
        try:
            if self._mic_volume:
                self._mic_volume.SetMasterVolumeLevelScalar(
                    percent / 100.0, None
                )
                log.debug(f"Gain micro → {percent}%")
        except Exception as e:
            log.error(f"set_mic_gain({percent}) : {e}")

    # =========================================================================
    # Initialisation privée
    # =========================================================================

    def _init_master(self) -> None:
        """Initialise le contrôle du volume master (sortie audio)."""
        try:
            devices = AudioUtilities.GetSpeakers()
            interface = devices.Activate(
                IAudioEndpointVolume._iid_, CLSCTX_ALL, None
            )
            self._master_volume = cast(interface, POINTER(IAudioEndpointVolume))
            log.info("Volume master initialisé")
        except Exception as e:
            log.error(f"Initialisation volume master : {e}")

    def _init_microphone(self) -> None:
        """Initialise le contrôle du microphone par défaut."""
        try:
            mic = AudioUtilities.GetMicrophone()
            if mic:
                interface = mic.Activate(
                    IAudioEndpointVolume._iid_, CLSCTX_ALL, None
                )
                self._mic_volume = cast(interface, POINTER(IAudioEndpointVolume))
                self._mic_muted  = bool(self._mic_volume.GetMute())
                log.info("Microphone initialisé")
        except Exception as e:
            log.error(f"Initialisation microphone : {e}")
