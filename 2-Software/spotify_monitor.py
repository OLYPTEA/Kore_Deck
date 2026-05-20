# =============================================================================
# spotify_monitor.py — récupère le titre en cours de lecture
#
# on utilise l'API Windows Media Session (winsdk) plutôt que l'API Spotify Web.
# avantages : pas de token OAuth, ça marche hors-ligne,
# et ça fonctionne avec n'importe quel lecteur (Spotify, VLC, navigateur...).
# =============================================================================

import asyncio
from typing import Optional

from logger import log


class SpotifyMonitor:
    """
    Moniteur du titre en cours via Windows Media Session.

    Dégradation gracieuse :
      - Si winsdk n'est pas installé  → log une fois, retourne "Aucune lecture"
      - Si aucun média actif          → retourne "Aucune lecture"
      - Si l'API plante               → retourne le dernier titre mis en cache
    """

    def __init__(self) -> None:
        self._current_track : str           = "Aucune lecture"
        # None = pas encore testé, False = winsdk absent ou API non dispo
        self._available     : Optional[bool] = None

    # -------------------------------------------------------------------------

    def get_current_track(self) -> str:
        """
        Retourne "Artiste - Titre" ou "Aucune lecture" si rien ne joue.
        asyncio.run() crée une boucle à chaque appel — c'est pas super optimisé
        mais comme on appelle ça seulement toutes les 2 s, c'est largement ok.
        """
        try:
            return asyncio.run(self._fetch_track())
        except Exception as e:
            # Log uniquement au premier échec pour éviter le spam
            if self._available is None:
                log.warning(f"Windows Media Session non disponible : {e}")
                self._available = False
            return self._current_track   # Retourne le cache

    # -------------------------------------------------------------------------

    async def _fetch_track(self) -> str:
        """
        Interroge l'API Windows Runtime pour obtenir les métadonnées du média actif.

        GlobalSystemMediaTransportControlsSessionManager :
          - request_async()          → obtient le gestionnaire de sessions
          - get_current_session()    → session du lecteur au premier plan
          - try_get_media_properties_async() → titre, artiste, album, durée…

        l'import de winsdk est là (dans la fonction) exprès :
        si winsdk n'est pas installé, ça lève ImportError ici seulement,
        pas au démarrage de tout l'agent — on dégrade proprement.
        """
        try:
            from winsdk.windows.media.control import (
                GlobalSystemMediaTransportControlsSessionManager as MediaManager,
            )

            manager = await MediaManager.request_async()
            session = manager.get_current_session()

            if not session:
                # Aucune application multimédia active en ce moment
                self._current_track = "Aucune lecture"
                return self._current_track

            info = await session.try_get_media_properties_async()

            if not info:
                return self._current_track   # Propriétés non disponibles → garde le cache

            artist = info.artist or ""
            title  = info.title  or ""

            # Construit "Artiste - Titre" seulement si les deux champs sont présents
            if artist and title:
                self._current_track = f"{artist} - {title}"
            elif title:
                self._current_track = title
            else:
                self._current_track = "Aucune lecture"

            self._available = True
            return self._current_track

        except ImportError:
            # winsdk non installé (requirements.txt non respecté ou Python 32-bit)
            if self._available is None:
                log.warning("winsdk non installé — titre Spotify désactivé")
                self._available = False
            return self._current_track
