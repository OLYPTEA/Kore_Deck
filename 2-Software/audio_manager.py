# =============================================================================
# audio_manager.py — Contrôle audio Windows via pycaw
#
# pycaw tape directement dans les API COM Windows (Core Audio) :
#   - IAudioEndpointVolume  : volume / mute d'un périphérique physique
#   - ISimpleAudioVolume    : volume d'une appli dans le mixeur Windows
#   - AudioUtilities        : helpers pour trouver les périphériques et sessions
#
# attention si tu appelles AudioManager depuis un thread secondaire :
# comtypes ne s'initialise pas tout seul dans les threads, il faut ajouter :
#   comtypes.CoInitialize()    au début du thread
#   comtypes.CoUninitialize()  à la fin
# =============================================================================

import time
from ctypes import POINTER, cast
from typing import Optional, Dict

from pycaw.pycaw import (
    AudioUtilities,
    IAudioEndpointVolume,
    ISimpleAudioVolume,
)
from comtypes import CLSCTX_ALL

from logger import log
from config import config


class AudioManager:
    """
    Gestionnaire audio Windows via pycaw (Python Core Audio Windows).

    Dégradation gracieuse : si un périphérique est absent, les méthodes
    correspondantes retournent silencieusement sans lever d'exception.

    Cache de sessions audio : éviter de ré-énumérer toutes les sessions Windows
    à chaque mouvement de potentiomètre (peut être 30+ sessions, COM lent).
    TTL configurable via config.audio.session_cache_ttl.
    """

    def __init__(self) -> None:
        self._master_volume : Optional[IAudioEndpointVolume] = None
        self._mic_volume    : Optional[IAudioEndpointVolume] = None

        # Cache process_name (lowercase) → ISimpleAudioVolume + horodatage du lookup
        self._session_cache : Dict[str, "ISimpleAudioVolume"] = {}
        self._session_cache_time : float = 0.0

        self._init_master()
        self._init_microphone()

    # =========================================================================
    # Volume Master (sortie audio par défaut)
    # =========================================================================

    def set_master_volume(self, percent: int) -> None:
        """Définit le volume master (0-100)."""
        percent = max(0, min(100, percent))
        try:
            if self._master_volume:
                self._master_volume.SetMasterVolumeLevelScalar(percent / 100.0, None)
                log.debug(f"Volume master → {percent}%")
        except Exception as e:
            log.error(f"set_master_volume({percent}) : {e}")

    def get_master_volume(self) -> int:
        """Lit le volume master actuel (0-100), 0 en cas d'erreur."""
        try:
            if self._master_volume:
                return int(self._master_volume.GetMasterVolumeLevelScalar() * 100)
        except Exception as e:
            log.error(f"get_master_volume : {e}")
        return 0

    # =========================================================================
    # Volume applicatif (par session audio Windows)
    # =========================================================================

    def set_app_volume(self, process_name: str, percent: int) -> bool:
        """
        Contrôle le volume d'une application dans le mixeur Windows.

        @param process_name  Nom exact du .exe, ex: "Spotify.exe"
        @param percent       0-100
        @return True si l'application a été trouvée et modifiée
        """
        percent = max(0, min(100, percent))
        try:
            volume_iface = self._get_app_volume_iface(process_name)
            if volume_iface is None:
                return False
            volume_iface.SetMasterVolume(percent / 100.0, None)
            log.debug(f"Volume {process_name} → {percent}%")
            return True
        except Exception as e:
            # Session invalidée (process fermé) → vide le cache pour ce process
            self._session_cache.pop(process_name.lower(), None)
            log.error(f"set_app_volume({process_name}, {percent}) : {e}")
            return False

    def set_game_volume(self, percent: int) -> None:
        """Tâte la liste de jeux connus, contrôle le premier qui tourne."""
        for proc in config.audio.game_processes:
            if self.set_app_volume(proc, percent):
                return
        log.debug("Aucun processus jeu actif trouvé")

    def set_spotify_volume(self, percent: int) -> None:
        self.set_app_volume(config.audio.spotify_process, percent)

    def set_discord_volume(self, percent: int) -> None:
        self.set_app_volume(config.audio.discord_process, percent)

    def _get_app_volume_iface(self, process_name: str):
        """
        Retourne l'ISimpleAudioVolume pour ce process, depuis le cache si possible.
        Re-scanne toutes les sessions si le cache est trop vieux ou si le process
        n'est pas connu (premier appel, ou app vient d'être lancée).
        """
        key = process_name.lower()
        now = time.monotonic()
        cache_expired = (now - self._session_cache_time) > config.audio.session_cache_ttl

        if not cache_expired and key in self._session_cache:
            return self._session_cache[key]

        # Rebuild complet du cache : un seul GetAllSessions pour tous les process
        self._rebuild_session_cache()
        return self._session_cache.get(key)

    def _rebuild_session_cache(self) -> None:
        """Énumère toutes les sessions audio et reconstruit le cache."""
        try:
            self._session_cache.clear()
            for session in AudioUtilities.GetAllSessions():
                if not session.Process:
                    continue
                try:
                    proc_name = session.Process.name().lower()
                except Exception:
                    continue   # Process mort entre l'énumération et le query
                iface = session._ctl.QueryInterface(ISimpleAudioVolume)
                self._session_cache[proc_name] = iface
            self._session_cache_time = time.monotonic()
        except Exception as e:
            log.error(f"Rebuild session cache : {e}")

    # =========================================================================
    # Microphone (entrée audio par défaut)
    # =========================================================================

    def toggle_mic_mute(self) -> bool:
        """
        Bascule le mute du microphone par défaut.
        Lit l'état RÉEL Windows avant de toggle → reste synchronisé même si
        une autre app (Teams, Discord) a changé le mute via raccourci global.

        @return  Nouvel état mute (True = muté)
        """
        try:
            if self._mic_volume:
                current = bool(self._mic_volume.GetMute())
                new_state = not current
                self._mic_volume.SetMute(int(new_state), None)
                log.info(f"Micro {'muté' if new_state else 'actif'}")
                return new_state
        except Exception as e:
            log.error(f"toggle_mic_mute : {e}")
        return False

    def is_mic_muted(self) -> bool:
        """Lit l'état mute réel depuis Windows. False en cas d'erreur ou pas de micro."""
        try:
            if self._mic_volume:
                return bool(self._mic_volume.GetMute())
        except Exception:
            pass
        return False

    def set_mic_gain(self, percent: int) -> None:
        """Ajuste le niveau d'enregistrement du micro (0-100)."""
        percent = max(0, min(100, percent))
        try:
            if self._mic_volume:
                self._mic_volume.SetMasterVolumeLevelScalar(percent / 100.0, None)
                log.debug(f"Gain micro → {percent}%")
        except Exception as e:
            log.error(f"set_mic_gain({percent}) : {e}")

    # =========================================================================
    # Initialisation COM (privé)
    # =========================================================================

    def _init_master(self) -> None:
        """Récupère IAudioEndpointVolume du périphérique de sortie par défaut."""
        try:
            devices   = AudioUtilities.GetSpeakers()
            interface = devices.Activate(IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
            self._master_volume = cast(interface, POINTER(IAudioEndpointVolume))
            log.info("Volume master initialisé")
        except Exception as e:
            log.error(f"Initialisation volume master : {e}")

    def _init_microphone(self) -> None:
        """Récupère IAudioEndpointVolume du microphone par défaut."""
        try:
            mic = AudioUtilities.GetMicrophone()
            if mic:
                interface = mic.Activate(IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
                self._mic_volume = cast(interface, POINTER(IAudioEndpointVolume))
                log.info("Microphone initialisé")
        except Exception as e:
            log.error(f"Initialisation microphone : {e}")
