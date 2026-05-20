# =============================================================================
# serial_manager.py — tout ce qui touche au port série
#
# deux threads séparés pour la lecture et l'écriture :
#   - serial-reader : attend les messages de l'ESP32 et appelle le callback
#   - serial-writer : prend ce qu'il y a dans la queue et envoie
#
# la séparation évite que lire bloque écrire et vice-versa.
# la queue.Queue gère la thread-safety pour l'envoi :)
# si le câble se débranche, le reader détecte l'erreur et retente tout seul.
# =============================================================================

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

    Deux threads dédiés (daemon=True → tués automatiquement si le processus s'arrête) :
      - _reader_thread : boucle de lecture, détecte les déconnexions
      - _writer_thread : boucle d'écriture, consomme la _tx_queue

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

        # Event permettant d'arrêter proprement les deux threads
        self._stop_event : threading.Event = threading.Event()

        # Queue FIFO thread-safe pour l'envoi — n'importe quel thread peut appeler send()
        self._tx_queue   : queue.Queue = queue.Queue()

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
        Signale aux threads de s'arrêter et ferme le port.
        Pas de join() nécessaire — daemon=True les tue automatiquement à la mort du process.
        """
        self._stop_event.set()
        if self._serial and self._serial.is_open:
            self._serial.close()
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

        Si déconnecté : tente de se reconnecter via _try_connect() (bloquant jusqu'au succès).
        Si connecté    : lit les octets disponibles sans bloquer (in_waiting check),
                         décode en UTF-8 et appelle le callback pour chaque ligne.

        on catch large avec SerialException pour couvrir tout : câble débranché,
        erreur IO Windows, timeout — dans tous les cas on reconnecte.
        """
        while not self._stop_event.is_set():
            if not self._connected:
                self._try_connect()
                continue   # Retour au début de la boucle après tentative

            try:
                # in_waiting : nombre d'octets en attente dans le buffer UART
                # On vérifie avant de lire pour éviter un readline() bloquant
                if self._serial and self._serial.in_waiting:
                    raw  = self._serial.readline()   # Lit jusqu'à '\n' (ou timeout)
                    line = raw.decode('utf-8', errors='ignore').strip()
                    if line:   # Ignore les lignes vides (lignes contenant seulement \r\n)
                        self._callback(line)
                else:
                    time.sleep(0.005)   # 5 ms de repos pour ne pas saturer le CPU

            except serial.SerialException as e:
                # Déconnexion physique ou erreur IO → on ferme proprement et on retente
                log.warning(f"Déconnexion série : {e}")
                self._connected = False
                if self._serial:
                    try:
                        self._serial.close()
                    except Exception:
                        pass   # Ignore les erreurs de fermeture sur un port déjà mort

    # =========================================================================
    # Thread writer — envoi des trames PC → ESP32
    # =========================================================================

    def _writer_loop(self) -> None:
        """
        Consomme la queue TX et envoie chaque ligne sur le port série.

        queue.get(timeout=0.1) bloque 100 ms maximum si la queue est vide,
        ce qui permet de vérifier régulièrement _stop_event sans busy-wait.

        Si le port se déconnecte pendant une écriture, on flag _connected = False
        pour que le reader_loop déclenche la reconnexion.
        """
        while not self._stop_event.is_set():
            if not self._connected:
                time.sleep(0.1)   # Attente de reconnexion — pas besoin d'écrire
                continue

            try:
                # Bloque jusqu'à 100 ms, lève queue.Empty si rien à envoyer
                line = self._tx_queue.get(timeout=0.1)
                if self._serial and self._serial.is_open:
                    self._serial.write((line + '\n').encode('utf-8'))
                    self._serial.flush()   # Force l'envoi immédiat (vide le buffer OS)

            except queue.Empty:
                pass   # Normal — pas de donnée à envoyer, on reboucle

            except serial.SerialException as e:
                # Écriture sur un port mort → signale la déconnexion au reader
                log.warning(f"Erreur écriture série : {e}")
                self._connected = False

    # =========================================================================
    # Connexion / reconnexion
    # =========================================================================

    def _try_connect(self) -> None:
        """
        Essaie d'ouvrir le port. Si ça rate, on attend quelques secondes et on revient.
        On recrée l'objet serial.Serial à chaque tentative pour repartir d'un état propre
        plutôt que de réutiliser une instance peut-être dans un état bizarre.
        """
        log.info(f"Connexion sur {config.serial.port} @ {config.serial.baud}...")
        try:
            self._serial = serial.Serial(
                port     = config.serial.port,
                baudrate = config.serial.baud,
                timeout  = config.serial.timeout   # Timeout de readline() en secondes
            )
            self._connected = True
            log.info(f"Connecté sur {config.serial.port}")

        except serial.SerialException as e:
            # Port occupé, absent, ou pilote absent → on attend et on retente
            log.warning(f"Connexion échouée : {e} — retry dans "
                        f"{config.serial.reconnect_delay}s")
            time.sleep(config.serial.reconnect_delay)
