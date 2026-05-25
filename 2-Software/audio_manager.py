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
    Gestionnaire audio Windows via pycaw (Python Core Audio Windows).

    Initialise les interfaces COM au démarrage. Si un périphérique est absent
    (ex: pas de micro), les méthodes correspondantes retournent silencieusement
    sans lever d'exception (dégradation gracieuse).
    """

    def __init__(self) -> None:
        # None = interface COM non initialisée (périphérique absent ou erreur)
        self._master_volume : Optional[IAudioEndpointVolume] = None
        self._mic_volume    : Optional[IAudioEndpointVolume] = None

        # Cache local du mute micro — évite un appel COM à chaque is_mic_muted()
        self._mic_muted : bool = False

        # Initialisation séparée sortie / entrée pour isoler les erreurs
        self._init_master()
        self._init_microphone()

    # =========================================================================
    # Volume Master (sortie audio par défaut)
    # =========================================================================

    def set_master_volume(self, percent: int) -> None:
        """
        Définit le volume master du périphérique de sortie par défaut.
        Équivalent au slider Windows dans le mixeur.

        @param percent  0-100 (clampé automatiquement)
        """
        percent = max(0, min(100, percent))
        try:
            if self._master_volume:
                # SetMasterVolumeLevelScalar attend un float 0.0-1.0
                self._master_volume.SetMasterVolumeLevelScalar(
                    percent / 100.0, None   # None = GUID event (non utilisé)
                )
                log.debug(f"Volume master → {percent}%")
        except Exception as e:
            log.error(f"set_master_volume({percent}) : {e}")

    def get_master_volume(self) -> int:
        """
        Lit le volume master actuel.
        @return  Entier 0-100, ou 0 en cas d'erreur.
        """
        try:
            if self._master_volume:
                scalar = self._master_volume.GetMasterVolumeLevelScalar()
                return int(scalar * 100)
        except Exception as e:
            log.error(f"get_master_volume : {e}")
        return 0

    # =========================================================================
    # Volume applicatif (par session audio Windows)
    # =========================================================================

    def set_app_volume(self, process_name: str, percent: int) -> bool:
        """
        Contrôle le volume d'une application dans le mixeur Windows.

        Windows gère un "graph audio" par application : chaque processus qui
        produit du son a une session audio indépendante. AudioUtilities.GetAllSessions()
        énumère toutes ces sessions et filtre par nom de processus.

        La comparaison est insensible à la casse pour gérer les variations
        (Spotify.exe vs spotify.exe selon la version).

        @param process_name  Nom exact du .exe, ex: "Spotify.exe"
        @param percent       0-100
        @return True si l'application a été trouvée et modifiée
        """
        percent = max(0, min(100, percent))
        try:
            sessions = AudioUtilities.GetAllSessions()
            for session in sessions:
                if session.Process and \
                   session.Process.name().lower() == process_name.lower():
                    # QueryInterface : récupère l'interface ISimpleAudioVolume depuis la session
                    volume = session._ctl.QueryInterface(ISimpleAudioVolume)
                    volume.SetMasterVolume(percent / 100.0, None)
                    log.debug(f"Volume {process_name} → {percent}%")
                    return True
        except Exception as e:
            log.error(f"set_app_volume({process_name}, {percent}) : {e}")
        return False

    def set_game_volume(self, percent: int) -> None:
        """
        Parcourt la liste de jeux connus et contrôle le premier qui tourne.
        On peut pas savoir à l'avance quel jeu est ouvert donc on tâte dans l'ordre.
        """
        for proc in config.audio.game_processes:
            if self.set_app_volume(proc, percent):
                return   # trouvé, on s'arrête là
        log.debug("Aucun processus jeu actif trouvé")

    def set_spotify_volume(self, percent: int) -> None:
        """Volume de Spotify (nom du processus dans config)."""
        self.set_app_volume(config.audio.spotify_process, percent)

    def set_discord_volume(self, percent: int) -> None:
        """Volume de Discord (nom du processus dans config)."""
        self.set_app_volume(config.audio.discord_process, percent)

    # =========================================================================
    # Microphone (entrée audio par défaut)
    # =========================================================================

    def toggle_mic_mute(self) -> bool:
        """
        Bascule le mute du microphone par défaut.
        Utilise l'interface IAudioEndpointVolume sur le périphérique d'entrée.

        @return  Nouvel état mute (True = muté)
        """
        try:
            if self._mic_volume:
                self._mic_muted = not self._mic_muted
                # SetMute attend un int (0 ou 1), pas un bool Python
                self._mic_volume.SetMute(int(self._mic_muted), None)
                log.info(f"Micro {'muté' if self._mic_muted else 'actif'}")
        except Exception as e:
            log.error(f"toggle_mic_mute : {e}")
        return self._mic_muted

    def is_mic_muted(self) -> bool:
        """
        Lit l'état mute réel depuis Windows (pas le cache local).
        Retombe sur le cache si la lecture COM échoue.
        """
        try:
            if self._mic_volume:
                return bool(self._mic_volume.GetMute())
        except Exception:
            pass
        return self._mic_muted   # Fallback sur le cache interne

    def set_mic_gain(self, percent: int) -> None:
        """
        Ajuste le niveau d'enregistrement du micro.
        Utilise SetMasterVolumeLevelScalar sur le périphérique d'entrée
        (même interface que le volume master, mais côté capture).

        @param percent  0-100 → 0.0-1.0 scalar
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
    # Initialisation COM (privé)
    # =========================================================================

    @staticmethod
    def _unwrap_device(dev):
        """
        Selon la version de pycaw, GetSpeakers() / GetMicrophone() peuvent
        renvoyer soit un IMMDevice COM natif (qui expose .Activate), soit un
        wrapper Python `AudioDevice` (qui encapsule le device sous ._dev).
        Cette helper déwrappe le second cas pour rester portable entre versions.
        """
        if dev is None or hasattr(dev, 'Activate'):
            return dev
        # AudioDevice wrapper : le device COM brut est dans ._dev
        inner = getattr(dev, '_dev', None)
        if inner is not None and hasattr(inner, 'Activate'):
            return inner
        # Dernier recours : on renvoie tel quel, l'appelant lèvera proprement
        return dev

    def _init_master(self) -> None:
        """
        Récupère le périphérique de sortie par défaut et son interface de volume.
        GetSpeakers() → IMMDevice (ou AudioDevice selon version pycaw),
        .Activate() → interface COM, cast() → objet Python utilisable.
        """
        try:
            device    = self._unwrap_device(AudioUtilities.GetSpeakers())
            interface = device.Activate(
                IAudioEndpointVolume._iid_, CLSCTX_ALL, None
            )
            self._master_volume = cast(interface, POINTER(IAudioEndpointVolume))
            log.info("Volume master initialisé")
        except Exception as e:
            log.error(f"Initialisation volume master : {e}")

    def _init_microphone(self) -> None:
        """
        Initialise IAudioEndpointVolume pour le microphone par défaut.
        Lit l'état mute initial pour synchroniser le cache _mic_muted.
        Si aucun microphone n'est détecté, _mic_volume reste None
        et toutes les méthodes micro échouent silencieusement.
        """
        try:
            mic = self._unwrap_device(AudioUtilities.GetMicrophone())
            if mic:
                interface = mic.Activate(
                    IAudioEndpointVolume._iid_, CLSCTX_ALL, None
                )
                self._mic_volume = cast(interface, POINTER(IAudioEndpointVolume))
                # Synchronise le cache avec l'état réel au démarrage
                self._mic_muted  = bool(self._mic_volume.GetMute())
                log.info("Microphone initialisé")
        except Exception as e:
            log.error(f"Initialisation microphone : {e}")
