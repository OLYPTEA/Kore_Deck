
# spotify_monitor.py, Lecture du titre Spotify via Windows Media Session API
#
# Utilise winsdk pour accéder aux métadonnées médias
# sans dépendre de l'API Spotify Web .
# Fonctionne avec toute application multimédia Windows (Spotify, VLC, etc.)


import asyncio
from typing import Optional

from logger import log


class SpotifyMonitor:
    """
    Moniteur du titre en cours de lecture via Windows Media Session.
    Compatible Spotify, navigateurs, VLC, et tout lecteur Windows.
    """

    def __init__(self) -> None:
        self._current_track: str = "Aucune lecture"
        self._available: Optional[bool] = None

    # -------------------------------------------------------------------------
    def get_current_track(self) -> str:
        """
        Retourne le titre en cours au format "Artiste - Titre".
        Retourne "Aucune lecture" si aucun média actif.
        """
        try:
            return asyncio.run(self._fetch_track())
        except Exception as e:
            if self._available is None:
                log.warning(f"Windows Media Session non disponible : {e}")
                self._available = False
            return self._current_track

    # -------------------------------------------------------------------------
    async def _fetch_track(self) -> str:
        """Récupère les métadonnées via l'API Windows Runtime."""
        try:
            from winsdk.windows.media.control import (
                GlobalSystemMediaTransportControlsSessionManager as MediaManager,
            )

            manager  = await MediaManager.request_async()
            session  = manager.get_current_session()

            if not session:
                self._current_track = "Aucune lecture"
                return self._current_track

            info = await session.try_get_media_properties_async()

            if not info:
                return self._current_track

            artist = info.artist or ""
            title  = info.title  or ""

            if artist and title:
                self._current_track = f"{artist} - {title}"
            elif title:
                self._current_track = title
            else:
                self._current_track = "Aucune lecture"

            self._available = True
            return self._current_track

        except ImportError:
            if self._available is None:
                log.warning("winsdk non installé — titre Spotify désactivé")
                self._available = False
            return self._current_track
