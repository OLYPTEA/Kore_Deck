# --- Contrôle audio Windows via pycaw (Core Audio COM) ---
# Si appelé depuis un thread secondaire : penser à CoInitialize/CoUninitialize.

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
    def __init__(self) -> None:
        self._master_volume : Optional[IAudioEndpointVolume] = None
        self._mic_volume    : Optional[IAudioEndpointVolume] = None
        self._mic_muted     : bool = False

        self._init_master()
        self._init_microphone()

    # --- Volume master

    def set_master_volume(self, percent: int) -> None:
        percent = max(0, min(100, percent))
        try:
            if self._master_volume:
                self._master_volume.SetMasterVolumeLevelScalar(percent / 100.0, None)
                log.debug(f"Volume master → {percent}%")
        except Exception as e:
            log.error(f"set_master_volume({percent}) : {e}")

    def get_master_volume(self) -> int:
        try:
            if self._master_volume:
                return int(self._master_volume.GetMasterVolumeLevelScalar() * 100)
        except Exception as e:
            log.error(f"get_master_volume : {e}")
        return 0

    # --- Volume applicatif

    def set_app_volume(self, process_name: str, percent: int) -> bool:
        percent = max(0, min(100, percent))
        try:
            for session in AudioUtilities.GetAllSessions():
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
        for proc in config.audio.game_processes:
            if self.set_app_volume(proc, percent):
                return
        log.debug("Aucun processus jeu actif trouvé")

    def set_spotify_volume(self, percent: int) -> None:
        self.set_app_volume(config.audio.spotify_process, percent)

    def set_discord_volume(self, percent: int) -> None:
        self.set_app_volume(config.audio.discord_process, percent)

    # --- Microphone

    def toggle_mic_mute(self) -> bool:
        try:
            if self._mic_volume:
                self._mic_muted = not self._mic_muted
                self._mic_volume.SetMute(int(self._mic_muted), None)
                log.info(f"Micro {'muté' if self._mic_muted else 'actif'}")
        except Exception as e:
            log.error(f"toggle_mic_mute : {e}")
        return self._mic_muted

    def is_mic_muted(self) -> bool:
        try:
            if self._mic_volume:
                return bool(self._mic_volume.GetMute())
        except Exception:
            pass
        return self._mic_muted

    def set_mic_gain(self, percent: int) -> None:
        percent = max(0, min(100, percent))
        try:
            if self._mic_volume:
                self._mic_volume.SetMasterVolumeLevelScalar(percent / 100.0, None)
                log.debug(f"Gain micro → {percent}%")
        except Exception as e:
            log.error(f"set_mic_gain({percent}) : {e}")

    # --- Init COM

    @staticmethod
    def _unwrap_device(dev):
        # GetSpeakers/GetMicrophone renvoient soit un IMMDevice COM natif,
        # soit un wrapper AudioDevice (suivant la version de pycaw).
        if dev is None or hasattr(dev, 'Activate'):
            return dev
        inner = getattr(dev, '_dev', None)
        if inner is not None and hasattr(inner, 'Activate'):
            return inner
        return dev

    def _init_master(self) -> None:
        try:
            device    = self._unwrap_device(AudioUtilities.GetSpeakers())
            interface = device.Activate(IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
            self._master_volume = cast(interface, POINTER(IAudioEndpointVolume))
            log.info("Volume master initialisé")
        except Exception as e:
            log.error(f"Initialisation volume master : {e}")

    def _init_microphone(self) -> None:
        try:
            mic = self._unwrap_device(AudioUtilities.GetMicrophone())
            if mic:
                interface = mic.Activate(IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
                self._mic_volume = cast(interface, POINTER(IAudioEndpointVolume))
                self._mic_muted  = bool(self._mic_volume.GetMute())
                log.info("Microphone initialisé")
        except Exception as e:
            log.error(f"Initialisation microphone : {e}")
