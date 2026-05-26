import asyncio
import json
import logging
import threading
from typing import Set, Optional, Callable

import websockets
from websockets.server import WebSocketServerProtocol

from config import config

log = logging.getLogger("ws_bridge")


class WebSocketBridge:
    def __init__(self) -> None:
        self._clients : Set[WebSocketServerProtocol] = set()
        self._loop : Optional[asyncio.AbstractEventLoop]   = None
        self._server : Optional[websockets.WebSocketServer]  = None
        self._thread : Optional[threading.Thread]            = None

        self.on_config_update : Optional[Callable[[dict], None]] = None
        self.on_action : Optional[Callable[[str], None]]  = None

    #Cycle de vie

    def start(self) -> None:
        self._thread = threading.Thread(
            target=self._run_loop, daemon=True, name="ws-bridge",
        )
        self._thread.start()
        log.info(f"WebSocket bridge démarré sur ws://{config.ws.host}:{config.ws.port}")

    def stop(self) -> None:
        # call_soon_threadsafe : seule façon sûre d'interagir avec la loop depuis l'extérieur.
        if self._loop and self._server:
            self._loop.call_soon_threadsafe(self._server.close)
        log.info("WebSocket bridge arrêté")

    #Émission vers l'UI

    def send_stats(self, stats: dict) -> None:
        self._broadcast({"type": "stats", "payload": stats})

    def send_connection_status(self, status: str) -> None:
        self._broadcast({"type": "connection", "payload": status})

    def send_agent_status(self, status: str) -> None:
        self._broadcast({"type": "agent", "payload": status})

    def get_client_count(self) -> int:
        return len(self._clients)

    #Interne

    def _broadcast(self, message: dict) -> None:
        if not self._clients or not self._loop:
            return
        raw = json.dumps(message)
        asyncio.run_coroutine_threadsafe(self._broadcast_async(raw), self._loop)

    async def _broadcast_async(self, raw: str) -> None:
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
        self._clients.add(websocket)
        log.info(f"UI connectée ({len(self._clients)} client(s))")

        await websocket.send(json.dumps({"type": "agent", "payload": "running"}))

        try:
            async for raw in websocket:
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
            if isinstance(action, str) and 0 < len(action) <= 64 and self.on_action:
                self.on_action(action)
            else:
                log.warning(f"Action UI invalide : {action!r}")

        else:
            log.debug(f"Message UI inconnu : {msg_type}")

    def _run_loop(self) -> None:
        self._loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self._loop)

        async def _serve():
            async with websockets.serve(
                self._handler,
                config.ws.host,
                config.ws.port,
                ping_interval = config.ws.ping_interval,
                ping_timeout = config.ws.ping_timeout,
                max_size = config.ws.max_message_size,
            ) as server:
                self._server = server
                await asyncio.Future()

        try:
            self._loop.run_until_complete(_serve())
        except Exception as e:
            log.error(f"WebSocket bridge erreur : {e}")
