import asyncio
from typing import Optional

from logger import log


class SpotifyMonitor:
    def __init__(self) -> None:
        self._current_track : str = "Aucune lecture"
        self._available : Optional[bool] = None

    def get_current_track(self) -> str:
        try:
            return asyncio.run(self._fetch_track())
        except Exception as e:
            if self._available is None:
                log.warning(f"Windows Media Session non disponible : {e}")
                self._available = False
            return self._current_track

    async def _fetch_track(self) -> str:
        try:
            from winsdk.windows.media.control import (
                GlobalSystemMediaTransportControlsSessionManager as MediaManager,
            )

            manager = await MediaManager.request_async()
            session = manager.get_current_session()
            if not session:
                self._current_track = "Aucune lecture"
                return self._current_track

            info = await session.try_get_media_properties_async()
            if not info:
                return self._current_track

            artist = info.artist or ""
            title = info.title  or ""

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
