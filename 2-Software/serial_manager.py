
# serial_manager.py — Gestion robuste du port série ESP32 <=> PC
#
# Fonctionnalités : 
#   - Connexion initiale avec retry
#   - Reconnexion automatique si déconnexion détectée
#   - Thread de lecture non-bloquant
#   - Queue thread-safe pour les événements reçus

import serial
import threading
import queue
import time
from typing import Optional, Callable

from logger import log
from config import config


class SerialManager:
    """
    Gestionnaire de port série avec reconnexion automatique.
    Tourne dans un thread dédié pour ne pas bloquer la boucle principale.
    """

    def __init__(self, on_line_received: Callable[[str], None]) -> None:
        """
        @param on_line_received  Callback appelé pour chaque ligne reçue
        """
        self._callback   : Callable[[str], None] = on_line_received
        self._serial     : Optional[serial.Serial] = None
        self._connected  : bool = False
        self._stop_event : threading.Event = threading.Event()
        self._tx_queue   : queue.Queue = queue.Queue()

        self._reader_thread = threading.Thread(
            target=self._reader_loop, daemon=True, name="serial-reader"
        )
        self._writer_thread = threading.Thread(
            target=self._writer_loop, daemon=True, name="serial-writer"
        )

   
    # Cycle de vie, note : start() doit être appelé après l'instanciation pour démarrer les threads
    

    def start(self) -> None:
        """Démarre les threads de lecture et d'écriture."""
        self._reader_thread.start()
        self._writer_thread.start()
        log.info("Threads série démarrés")

    def stop(self) -> None:
        """Arrête proprement les threads et ferme le port."""
        self._stop_event.set()
        if self._serial and self._serial.is_open:
            self._serial.close()
        log.info("Port série fermé")

    
    # Envoi
   

    def send(self, line: str) -> None:
        """
        Enqueue une ligne à envoyer vers l'ESP32.
        Non-bloquant — la ligne sera envoyée par le thread writer.
        @param line  Chaîne sans '\n' (ajouté automatiquement)
        """
        self._tx_queue.put_nowait(line)

    def is_connected(self) -> bool:
        return self._connected

    
    # Thread reader — réception des trames ESP32 -> PC 
    

    def _reader_loop(self) -> None:
        while not self._stop_event.is_set():
            if not self._connected:
                self._try_connect()
                continue

            try:
                if self._serial and self._serial.in_waiting:
                    raw = self._serial.readline()
                    line = raw.decode('utf-8', errors='ignore').strip()
                    if line:
                        self._callback(line)
                else:
                    time.sleep(0.005)  # Évite la saturation CPU

            except serial.SerialException as e:
                log.warning(f"Déconnexion série : {e}")
                self._connected = False
                if self._serial:
                    try:
                        self._serial.close()
                    except Exception:
                        pass

    
    # Thread writer — envoi des trames PC -> ESP32 )
    

    def _writer_loop(self) -> None:
        while not self._stop_event.is_set():
            if not self._connected:
                time.sleep(0.1)
                continue

            try:
                line = self._tx_queue.get(timeout=0.1)
                if self._serial and self._serial.is_open:
                    self._serial.write((line + '\n').encode('utf-8'))
                    self._serial.flush()
            except queue.Empty:
                pass
            except serial.SerialException as e:
                log.warning(f"Erreur écriture série : {e}")
                self._connected = False

    
    # Connexion / reconnexion
    

    def _try_connect(self) -> None:
        """Tentative de connexion — retente toutes les reconnect_delay secondes."""
        log.info(f"Connexion sur {config.serial.port} @ {config.serial.baud}...")
        try:
            self._serial = serial.Serial(
                port     = config.serial.port,
                baudrate = config.serial.baud,
                timeout  = config.serial.timeout
            )
            self._connected = True
            log.info(f"Connecté sur {config.serial.port}")

        except serial.SerialException as e:
            log.warning(f"Connexion échouée : {e} — retry dans "
                        f"{config.serial.reconnect_delay}s")
            time.sleep(config.serial.reconnect_delay)

# Note pour le prochain dev : le fait que j'ai mis les threads dans le constructeur,
# c'est juste pour éviter d'avoir à les recréer à chaque reconnexion. 
# Ils tournent en boucle et gèrent eux même l'état de connexion. 
# C'est plus simple que de devoir arrêter et redémarrer des threads à chaque reconnexion.
