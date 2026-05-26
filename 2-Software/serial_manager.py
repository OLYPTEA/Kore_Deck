import threading
import queue
import time
from typing import Optional, Callable

import serial

from logger import log
from config import config


class SerialManager:
    def __init__(self, on_line_received: Callable[[str], None]) -> None:
        # Callback appelé depuis le thread reader — ne pas bloquer dedans.
        self._callback : Callable[[str], None] = on_line_received
        self._serial  : Optional[serial.Serial] = None
        self._connected  : bool = False

        self._serial_lock : threading.Lock  = threading.Lock()
        self._stop_event : threading.Event = threading.Event()
        self._tx_queue  : queue.Queue     = queue.Queue()

        self._reader_thread = threading.Thread(
            target=self._reader_loop, daemon=True, name="serial-reader",
        )
        self._writer_thread = threading.Thread(
            target=self._writer_loop, daemon=True, name="serial-writer",
        )

    #Cycle de vie

    def start(self) -> None:
        self._reader_thread.start()
        self._writer_thread.start()
        log.info("Threads série démarrés")

    def stop(self) -> None:
        self._stop_event.set()
        self._close_serial()
        log.info("Port série fermé")

    # API publique

    def send(self, line: str) -> None:
        self._tx_queue.put_nowait(line)

    def is_connected(self) -> bool:
        return self._connected

    #Reader

    def _reader_loop(self) -> None:
        while not self._stop_event.is_set():
            if not self._connected:
                self._try_connect()
                continue

            try:
                raw = self._read_line_safe()
                if raw is None:
                    time.sleep(0.005)
                    continue

                line = raw.decode('utf-8', errors='ignore').strip()
                if line:
                    self._callback(line)

            except serial.SerialException as e:
                log.warning(f"Déconnexion série : {e}")
                self._close_serial()

    def _read_line_safe(self) -> Optional[bytes]:
        with self._serial_lock:
            ser = self._serial
            if ser is None or not ser.is_open:
                raise serial.SerialException("Port fermé")
            if ser.in_waiting == 0:
                return None
            return ser.readline()

    #Writer

    def _writer_loop(self) -> None:
        # timeout=0.1 sur get() permet de re-vérifier _stop_event périodiquement.
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
        payload = (line + '\n').encode('utf-8')
        with self._serial_lock:
            ser = self._serial
            if ser is None or not ser.is_open:
                raise serial.SerialException("Port fermé")
            ser.write(payload)
            ser.flush()

    #Connexion / fermeture

    def _try_connect(self) -> None:
        log.info(f"Connexion sur {config.serial.port} @ {config.serial.baud}...")
        try:
            new_serial = serial.Serial(
                port = config.serial.port,
                baudrate = config.serial.baud,
                timeout = config.serial.timeout,
            )
            with self._serial_lock:
                self._serial = new_serial
            self._connected = True
            log.info(f"Connecté sur {config.serial.port}")

        except serial.SerialException as e:
            log.warning(f"Connexion échouée : {e} — retry dans "
                        f"{config.serial.reconnect_delay}s")
            # Wait interruptible : un stop() débloque immédiatement.
            self._stop_event.wait(timeout=config.serial.reconnect_delay)

    def _close_serial(self) -> None:
        self._connected = False
        with self._serial_lock:
            if self._serial is not None:
                try:
                    if self._serial.is_open:
                        self._serial.close()
                except Exception:
                    pass
                self._serial = None
