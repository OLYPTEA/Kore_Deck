# =============================================================================
# serial_manager.py 
#
# deux threads séparés pour la lecture et l'écriture :
#   - serial-reader : attend les messages de l'ESP32 et appelle le callback
#   - serial-writer : prend ce qu'il y a dans la queue et envoie
#
# la séparation évite que lire bloque écrire et vice-versa.
# la queue.Queue gère la thread-safety pour l'envoi.
# un threading.Lock (_serial_lock) protège l'objet serial.Serial lui-même
# contre les accès concurrents reader/writer/_try_connect/stop.
# =============================================================================

import threading
import queue
import time
from typing import Optional, Callable

import serial

from logger import log
from config import config


class SerialManager:
    """
    Gestionnaire de port série avec reconnexion automatique.

    Deux threads dédiés (daemon=True → tués automatiquement si le process s'arrête) :
      - _reader_thread : boucle de lecture, détecte les déconnexions
      - _writer_thread : boucle d'écriture, consomme la _tx_queue

    Thread-safety : tous les accès à self._serial passent par _serial_lock.
    L'attribut bool _connected utilise un Lock séparé pour les lectures non bloquantes.

    Usage minimal :
        sm = SerialManager(on_line_received=mon_callback)
        sm.start()
        sm.send("CAT:2")
        sm.stop()
    """

    def __init__(self, on_line_received: Callable[[str], None]) -> None:
        """
        @param on_line_received  Callback(line: str) → None, appelé depuis le thread reader.
                                 Ne pas bloquer dans ce callback (risque de manquer des lignes).
        """
        self._callback   : Callable[[str], None] = on_line_received
        self._serial     : Optional[serial.Serial] = None
        self._connected  : bool = False

        # Lock protégeant TOUS les accès à self._serial (open/close/read/write/réassignation)
        # → évite la race entre reader, writer et _try_connect
        self._serial_lock : threading.Lock = threading.Lock()

        # Event d'arrêt propre des threads
        self._stop_event  : threading.Event = threading.Event()

        # Queue FIFO thread-safe pour l'envoi — n'importe quel thread peut appeler send()
        self._tx_queue    : queue.Queue = queue.Queue()

        # daemon=True : les threads ne bloquent pas la sortie du programme
        self._reader_thread = threading.Thread(
            target=self._reader_loop, daemon=True, name="serial-reader"
        )
        self._writer_thread = threading.Thread(
            target=self._writer_loop, daemon=True, name="serial-writer"
        )

    # =========================================================================
    # Cycle de vie
    # =========================================================================

    def start(self) -> None:
        """Démarre les threads de lecture et d'écriture."""
        self._reader_thread.start()
        self._writer_thread.start()
        log.info("Threads série démarrés")

    def stop(self) -> None:
        """
        Signale aux threads de s'arrêter et ferme le port sous le Lock.
        Pas de join() nécessaire — daemon=True les tue à la mort du process.
        """
        self._stop_event.set()
        self._close_serial()
        log.info("Port série fermé")

    # =========================================================================
    # Envoi (thread-safe, non-bloquant)
    # =========================================================================

    def send(self, line: str) -> None:
        """
        Enfile une ligne dans la queue TX — retour immédiat, sans attente.
        Le thread writer la dépilera et l'écrira sur le port dès possible.

        @param line  Chaîne sans '\n' (le '\n' est ajouté par _writer_loop)
        """
        self._tx_queue.put_nowait(line)

    def is_connected(self) -> bool:
        """Retourne True si le port est actuellement ouvert et opérationnel."""
        return self._connected

    # =========================================================================
    # Thread reader — réception des trames ESP32 → PC
    # =========================================================================

    def _reader_loop(self) -> None:
        """
        Boucle de lecture principale.
        Si déconnecté → tente reconnexion (bloquant jusqu'au succès ou stop).
        Si connecté   → lit non-bloquant, décode, appelle le callback ligne par ligne.
        """
        while not self._stop_event.is_set():
            if not self._connected:
                self._try_connect()
                continue

            try:
                raw = self._read_line_safe()
                if raw is None:
                    time.sleep(0.005)   # Rien à lire — pas de busy-wait
                    continue

                line = raw.decode('utf-8', errors='ignore').strip()
                if line:
                    self._callback(line)

            except serial.SerialException as e:
                # Déconnexion physique ou erreur IO → reset propre
                log.warning(f"Déconnexion série : {e}")
                self._close_serial()

    def _read_line_safe(self) -> Optional[bytes]:
        """
        Lit une ligne sous le Lock. Retourne None si rien n'est disponible.
        Lève serial.SerialException si le port est mort.
        """
        with self._serial_lock:
            ser = self._serial
            if ser is None or not ser.is_open:
                raise serial.SerialException("Port fermé")
            if ser.in_waiting == 0:
                return None
            return ser.readline()

    # =========================================================================
    # Thread writer — envoi des trames PC → ESP32
    # =========================================================================

    def _writer_loop(self) -> None:
        """
        Consomme la queue TX et envoie chaque ligne sur le port série.
        get(timeout=0.1) débloque toutes les 100 ms pour vérifier _stop_event.
        """
        while not self._stop_event.is_set():
            if not self._connected:
                time.sleep(0.1)
                continue

            try:
                line = self._tx_queue.get(timeout=0.1)
            except queue.Empty:
                continue

            try:
                self._write_line_safe(line)
            except serial.SerialException as e:
                log.warning(f"Erreur écriture série : {e}")
                self._close_serial()

    def _write_line_safe(self, line: str) -> None:
        """
        Écrit une ligne sous le Lock + flush.
        Lève serial.SerialException si le port est mort.
        """
        payload = (line + '\n').encode('utf-8')
        with self._serial_lock:
            ser = self._serial
            if ser is None or not ser.is_open:
                raise serial.SerialException("Port fermé")
            ser.write(payload)
            ser.flush()

    # =========================================================================
    # Connexion / reconnexion / fermeture
    # =========================================================================

    def _try_connect(self) -> None:
        """
        Tente d'ouvrir le port. Si ça rate, attend reconnect_delay et revient.
        On recrée l'objet serial.Serial à chaque tentative pour repartir d'un état propre.
        """
        log.info(f"Connexion sur {config.serial.port} @ {config.serial.baud}...")
        try:
            new_serial = serial.Serial(
                port     = config.serial.port,
                baudrate = config.serial.baud,
                timeout  = config.serial.timeout
            )
            with self._serial_lock:
                self._serial = new_serial
            self._connected = True
            log.info(f"Connecté sur {config.serial.port}")

        except serial.SerialException as e:
            log.warning(f"Connexion échouée : {e} — retry dans "
                        f"{config.serial.reconnect_delay}s")
            # Sleep interruptible pour réagir vite à un stop()
            self._stop_event.wait(timeout=config.serial.reconnect_delay)

    def _close_serial(self) -> None:
        """
        Ferme le port et flag déconnecté, le tout sous Lock.
        Sûr à appeler depuis n'importe quel thread, idempotent.
        """
        self._connected = False
        with self._serial_lock:
            if self._serial is not None:
                try:
                    if self._serial.is_open:
                        self._serial.close()
                except Exception:
                    pass   # Port déjà mort — on s'en fiche
                self._serial = None
