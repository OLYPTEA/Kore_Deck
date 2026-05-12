# =============================================================================
# system_monitor.py — Monitoring des ressources système
#
# Données collectées :
#   - CPU usage (%)
#   - RAM usage (%)
#   - FPS via HWiNFO shared memory (optionnel, retourne 0 si absent)
# =============================================================================

import ctypes
import struct
from typing import Optional

import psutil

from logger import log


class SystemMonitor:
    """
    Moniteur des ressources système Windows.
    Thread-safe (lecture seule de données système).
    """

    # Nom du shared memory HWiNFO (si installé et actif)
    _HWINFO_SHMEM_NAME = "Global\\HWiNFO_SENS_SM2"

    def __init__(self) -> None:
        self._hwinfo_available: Optional[bool] = None  # None = pas encore testé

    # -------------------------------------------------------------------------
    def get_cpu_usage(self) -> int:
        """Retourne le % d'utilisation CPU (0-100), moyenné sur 0.1s."""
        try:
            return int(psutil.cpu_percent(interval=0.0))
        except Exception as e:
            log.warning(f"CPU usage read error: {e}")
            return 0

    # -------------------------------------------------------------------------
    def get_ram_usage(self) -> float:
        """Retourne le % d'utilisation RAM (0.0-100.0, 1 décimale)."""
        try:
            return round(psutil.virtual_memory().percent, 1)
        except Exception as e:
            log.warning(f"RAM usage read error: {e}")
            return 0.0

    # -------------------------------------------------------------------------
    def get_fps(self) -> int:
        """
        Tente de lire le FPS depuis HWiNFO shared memory.
        Retourne 0 si HWiNFO n'est pas actif ou si aucun capteur FPS trouvé.
        """
        if self._hwinfo_available is False:
            return 0

        try:
            return self._read_hwinfo_fps()
        except Exception:
            if self._hwinfo_available is None:
                log.info("HWiNFO non disponible — FPS désactivé")
            self._hwinfo_available = False
            return 0

    # -------------------------------------------------------------------------
    def _read_hwinfo_fps(self) -> int:
        """
        Lecture du FPS depuis HWiNFO shared memory.
        Structure : voir documentation HWiNFO SDK.
        """
        kernel32 = ctypes.windll.kernel32

        handle = kernel32.OpenFileMappingW(
            0x0004,  # FILE_MAP_READ
            False,
            self._HWINFO_SHMEM_NAME
        )

        if not handle:
            raise OSError("HWiNFO shared memory non disponible")

        self._hwinfo_available = True

        try:
            # Taille header HWiNFO
            HEADER_SIZE = 40
            ELEMENT_SIZE = 128

            view = ctypes.windll.kernel32.MapViewOfFile(
                handle, 0x0004, 0, 0, HEADER_SIZE
            )
            if not view:
                return 0

            # Lecture header
            header = (ctypes.c_byte * HEADER_SIZE).from_address(view)
            header_bytes = bytes(header)

            num_sensors = struct.unpack_from("<I", header_bytes, 28)[0]
            num_elements = struct.unpack_from("<I", header_bytes, 32)[0]

            ctypes.windll.kernel32.UnmapViewOfFile(view)

            if num_elements == 0:
                return 0

            # Lecture des éléments pour trouver "FPS"
            total_size = HEADER_SIZE + num_elements * ELEMENT_SIZE
            view2 = ctypes.windll.kernel32.MapViewOfFile(
                handle, 0x0004, 0, 0, total_size
            )
            if not view2:
                return 0

            data = (ctypes.c_byte * total_size).from_address(view2)
            data_bytes = bytes(data)

            fps_value = 0
            for i in range(num_elements):
                offset = HEADER_SIZE + i * ELEMENT_SIZE
                # Label est à l'offset 8, longueur 128
                label_raw = data_bytes[offset + 8: offset + 8 + 64]
                label = label_raw.split(b'\x00')[0].decode('utf-8', errors='ignore')

                if 'fps' in label.lower() or 'frame' in label.lower():
                    # Valeur float à offset 88
                    val = struct.unpack_from("<f", data_bytes, offset + 88)[0]
                    fps_value = int(val)
                    break

            ctypes.windll.kernel32.UnmapViewOfFile(view2)
            return fps_value

        finally:
            kernel32.CloseHandle(handle)
