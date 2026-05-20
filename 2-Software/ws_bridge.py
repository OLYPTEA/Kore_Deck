# =============================================================================
# ws_bridge.py — le lien entre l'UI Tauri et l'agent Python
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
# =============================================================================

import asyncio
import json
import logging
import threading
from typing import Set, Optional, Callable

import websockets
from websockets.server import WebSocketServerProtocol

# Logger spécifique à ce module (hérite de la config root via setup_logger)
log = logging.getLogger("ws_bridge")

WS_HOST = "localhost"   # Écoute uniquement en local — ne pas exposer sur le réseau
WS_PORT = 8765


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
        log.info(f"WebSocket bridge démarré sur ws://{WS_HOST}:{WS_PORT}")

    def stop(self) -> None:
        """
        Arrête le serveur proprement en programmant la fermeture dans l'event loop.
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
        """
        Envoie les stats système (CPU, RAM, FPS, Pomodoro…) à tous les clients.
        Peut être appelé depuis n'importe quel thread.
        """
        self._broadcast({"type": "stats", "payload": stats})

    def send_connection_status(self, status: str) -> None:
        """
        Envoie le statut de la connexion ESP32.
        @param status  "connected" | "disconnected" | "reconnecting"
        """
        self._broadcast({"type": "connection", "payload": status})

    def send_agent_status(self, status: str) -> None:
        """
        Envoie le statut de l'agent Python.
        @param status  "running" | "stopped"
        """
        self._broadcast({"type": "agent", "payload": status})

    def get_client_count(self) -> int:
        """Retourne le nombre de clients WebSocket connectés."""
        return len(self._clients)

    # =========================================================================
    # Internals
    # =========================================================================

    def _broadcast(self, message: dict) -> None:
        """
        Envoie un message JSON à tout le monde.
        run_coroutine_threadsafe() parce qu'on est dans le thread principal
        et que websockets veut qu'on passe par sa boucle asyncio — on n'a pas le choix.
        """
        if not self._clients or not self._loop:
            return   # personne d'connecté ou loop pas encore prête
        raw = json.dumps(message)
        asyncio.run_coroutine_threadsafe(
            self._broadcast_async(raw), self._loop
        )

    async def _broadcast_async(self, raw: str) -> None:
        """
        Envoie un message à tous les clients dans l'event loop asyncio.
        Les clients déconnectés sont retirés de l'ensemble silencieusement.
        """
        if not self._clients:
            return
        disconnected = set()
        for client in self._clients.copy():   # copy() sinon on modifie le set pendant l'itération
            try:
                await client.send(raw)
            except websockets.exceptions.ConnectionClosed:
                disconnected.add(client)
        self._clients -= disconnected

    async def _handler(self, websocket: WebSocketServerProtocol) -> None:
        """
        Coroutine invoquée par websockets pour chaque nouvelle connexion client.
        Enregistre le client, envoie le message de bienvenue, puis lit en boucle.
        Le bloc finally garantit le retrait du client même en cas d'erreur.
        """
        self._clients.add(websocket)
        log.info(f"UI connectée ({len(self._clients)} client(s))")

        # Message de bienvenue : l'UI sait immédiatement que l'agent tourne
        await websocket.send(json.dumps({"type": "agent", "payload": "running"}))

        try:
            # Boucle de réception — s'arrête quand la connexion est fermée
            async for raw in websocket:
                await self._handle_message(raw)
        except websockets.exceptions.ConnectionClosed:
            pass   # Fermeture normale (navigateur fermé, Tauri rechargé, etc.)
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
            msg_type = msg.get("type")

            if msg_type == "hello":
                # Premier message envoyé par l'UI après connexion — juste un log
                log.info(f"UI connectée — version {msg.get('version', '?')}")

            elif msg_type == "config_update":
                # L'UI demande à changer la configuration (port, baud, etc.)
                if self.on_config_update:
                    self.on_config_update(msg.get("data", {}))

            elif msg_type == "action":
                # L'UI déclenche une action directe (ex: clic sur bouton MUTE)
                action = msg.get("action", "")
                if action and self.on_action:
                    self.on_action(action)

            else:
                log.debug(f"Message UI inconnu : {msg_type}")

        except json.JSONDecodeError:
            log.warning(f"Message non-JSON reçu : {raw[:100]}")

    def _run_loop(self) -> None:
        """
        Crée une boucle asyncio dans ce thread et démarre le serveur.
        Python ne crée pas de boucle automatiquement dans les threads secondaires,
        donc on en crée une manuellement.

        `await asyncio.Future()` c'est le pattern pour "tourne indéfiniment sans rien faire".
        C'est plus propre que while True + sleep.

        ping_interval/timeout : pour détecter les clients qui ont disparu sans dire au revoir.
        """
        self._loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self._loop)

        async def _serve():
            async with websockets.serve(
                self._handler, WS_HOST, WS_PORT,
                ping_interval=20,    # Envoie un PING toutes les 20 s
                ping_timeout=10,     # Déconnecte si pas de PONG après 10 s
            ) as server:
                self._server = server
                await asyncio.Future()   # Maintient le serveur actif indéfiniment

        try:
            self._loop.run_until_complete(_serve())
        except Exception as e:
            log.error(f"WebSocket bridge erreur : {e}")
