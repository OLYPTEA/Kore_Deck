# =============================================================================
# ws_bridge.py — Pour l'app et l'agent
#
# le serveur WebSocket tourne dans son propre thread avec sa propre boucle asyncio.
# quand l'agent veut envoyer quelque chose depuis le thread principal,
# il passe par asyncio.run_coroutine_threadsafe() pour que ça arrive dans le bon event loop.
# plusieurs clients en même temps sont gérés (ex: DevTools ouvert + appli Tauri).
#
# Format messages → UI  : { "type": "stats",      "payload": {...} }
#                          { "type": "connection", "payload": "connected"|"disconnected" }
#                          { "type": "agent",      "payload": "running"|"stopped" }
#
# Format messages ← UI  : { "type": "config_update", "data": {...} }
#                          { "type": "action",         "action": "MEDIA_PLAY" }
#                          { "type": "hello",          "version": "2.0" }
#
# Limite : les messages entrants sont rejetés au-delà de config.ws.max_message_size.
# Hôte/port/timeouts proviennent tous de config.ws — pas de magic numbers.
# =============================================================================

import asyncio
import json
import logging
import threading
from typing import Set, Optional, Callable

import websockets
from websockets.server import WebSocketServerProtocol

from config import config

# Logger spécifique à ce module (hérite de la config root via setup_logger)
log = logging.getLogger("ws_bridge")


class WebSocketBridge:
    """
    Serveur WebSocket local exposé à l'interface Tauri.

    Thread model :
      - Le thread "ws-bridge" possède la boucle asyncio et gère les connexions.
      - Les méthodes publiques (send_stats, etc.) sont appelables depuis n'importe
        quel thread grâce à asyncio.run_coroutine_threadsafe().

    Cycle de vie :
        bridge = WebSocketBridge()
        bridge.on_action = mon_callback
        bridge.start()
        bridge.send_stats({...})   # thread-safe
        bridge.stop()
    """

    def __init__(self) -> None:
        # Ensemble des connexions WebSocket actives (modifié uniquement dans l'event loop)
        self._clients : Set[WebSocketServerProtocol] = set()

        # Référence à la boucle asyncio du thread ws-bridge
        # Nécessaire pour run_coroutine_threadsafe depuis d'autres threads
        self._loop   : Optional[asyncio.AbstractEventLoop] = None
        self._server : Optional[websockets.WebSocketServer] = None
        self._thread : Optional[threading.Thread] = None

        # Callbacks à définir avant start() — appelés dans le thread ws-bridge
        self.on_config_update : Optional[Callable[[dict], None]] = None
        self.on_action        : Optional[Callable[[str], None]]  = None

    # =========================================================================
    # Cycle de vie
    # =========================================================================

    def start(self) -> None:
        """Démarre le serveur WebSocket dans un thread dédié (daemon)."""
        self._thread = threading.Thread(
            target=self._run_loop, daemon=True, name="ws-bridge"
        )
        self._thread.start()
        log.info(f"WebSocket bridge démarré sur ws://{config.ws.host}:{config.ws.port}")

    def stop(self) -> None:
        """
        Arrête le serveur en programmant la fermeture dans l'event loop.
        call_soon_threadsafe est la seule façon sûre d'interagir avec une boucle
        asyncio depuis un thread extérieur.
        """
        if self._loop and self._server:
            self._loop.call_soon_threadsafe(self._server.close)
        log.info("WebSocket bridge arrêté")

    # =========================================================================
    # Envoi de données vers l'UI (thread-safe)
    # =========================================================================

    def send_stats(self, stats: dict) -> None:
        """Envoie les stats (CPU/RAM/FPS/Pomo) à tous les clients."""
        self._broadcast({"type": "stats", "payload": stats})

    def send_connection_status(self, status: str) -> None:
        """status: connected | disconnected | reconnecting"""
        self._broadcast({"type": "connection", "payload": status})

    def send_agent_status(self, status: str) -> None:
        """status: running | stopped"""
        self._broadcast({"type": "agent", "payload": status})

    def get_client_count(self) -> int:
        return len(self._clients)

    # =========================================================================
    # Internals
    # =========================================================================

    def _broadcast(self, message: dict) -> None:
        """
        Envoie un message JSON à tous les clients connectés.
        run_coroutine_threadsafe() parce qu'on est dans le thread principal
        et que websockets veut qu'on passe par sa boucle asyncio.
        """
        if not self._clients or not self._loop:
            return
        raw = json.dumps(message)
        asyncio.run_coroutine_threadsafe(self._broadcast_async(raw), self._loop)

    async def _broadcast_async(self, raw: str) -> None:
        """Diffuse à tous les clients. Retire silencieusement les déconnectés."""
        if not self._clients:
            return
        disconnected = set()
        for client in self._clients.copy():
            try:
                await client.send(raw)
            except websockets.exceptions.ConnectionClosed:
                disconnected.add(client)
        self._clients -= disconnected

    async def _handler(self, websocket: WebSocketServerProtocol) -> None:
        """
        Coroutine invoquée par websockets pour chaque nouvelle connexion.
        Le bloc finally garantit le retrait du client même en cas d'erreur.
        """
        self._clients.add(websocket)
        log.info(f"UI connectée ({len(self._clients)} client(s))")

        # Message de bienvenue : l'UI sait immédiatement que l'agent tourne
        await websocket.send(json.dumps({"type": "agent", "payload": "running"}))

        try:
            async for raw in websocket:
                # Validation taille — coupe court aux messages absurdes
                if len(raw) > config.ws.max_message_size:
                    log.warning(f"Message UI trop gros ({len(raw)} octets) — rejeté")
                    continue
                await self._handle_message(raw)
        except websockets.exceptions.ConnectionClosed:
            pass
        finally:
            self._clients.discard(websocket)
            log.info(f"UI déconnectée ({len(self._clients)} client(s))")

    async def _handle_message(self, raw: str) -> None:
        """
        Parse et dispatche un message JSON reçu depuis l'UI.

        Types supportés :
          "hello"         → log de connexion (version UI)
          "config_update" → hot-reload de la config (callback on_config_update)
          "action"        → exécution d'une action (callback on_action)
        """
        try:
            msg = json.loads(raw)
        except json.JSONDecodeError:
            log.warning(f"Message non-JSON reçu : {raw[:100]}")
            return

        if not isinstance(msg, dict):
            log.warning(f"Message UI non-objet : {type(msg).__name__}")
            return

        msg_type = msg.get("type")

        if msg_type == "hello":
            log.info(f"UI connectée — version {msg.get('version', '?')}")

        elif msg_type == "config_update":
            if self.on_config_update:
                data = msg.get("data", {})
                if isinstance(data, dict):
                    self.on_config_update(data)

        elif msg_type == "action":
            action = msg.get("action", "")
            # Validation : action doit être une str courte (les noms sont < 32 chars)
            if isinstance(action, str) and 0 < len(action) <= 64 and self.on_action:
                self.on_action(action)
            else:
                log.warning(f"Action UI invalide : {action!r}")

        else:
            log.debug(f"Message UI inconnu : {msg_type}")

    def _run_loop(self) -> None:
        """
        Crée une boucle asyncio dans ce thread et démarre le serveur.
        Python ne crée pas de boucle automatiquement dans les threads secondaires.

        `await asyncio.Future()` = pattern "tourne indéfiniment sans rien faire"
        — plus propre que while True + sleep.
        """
        self._loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self._loop)

        async def _serve():
            async with websockets.serve(
                self._handler,
                config.ws.host,
                config.ws.port,
                ping_interval = config.ws.ping_interval,
                ping_timeout  = config.ws.ping_timeout,
                max_size      = config.ws.max_message_size,
            ) as server:
                self._server = server
                await asyncio.Future()

        try:
            self._loop.run_until_complete(_serve())
        except Exception as e:
            log.error(f"WebSocket bridge erreur : {e}")
