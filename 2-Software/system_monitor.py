# =============================================================================
# system_monitor.py — Monitoring des ressources système
#
# CPU / RAM : via psutil, rien de fancy
# FPS       : via HWiNFO64 Shared Memory — optionnel, désactivé si HWiNFO pas lancé
#
# pour le FPS : HWiNFO64 expose ses capteurs en mémoire partagée ("Global\HWiNFO_SENS_SM2").
# on lit ce bloc directement avec les API Win32, pas besoin de DLL tierce.
# pour que ça marche : HWiNFO64 doit être lancé avec "Shared Memory Support" activé.
# si c'est pas le cas, get_fps() retourne 0 sans planter.
# =============================================================================

import ctypes
import struct
from contextlib import contextmanager
from typing import Optional

import psutil

from logger import log


# Constantes Win32
_FILE_MAP_READ = 0x0004


@contextmanager
def _map_view(handle, size: int):
    """
    Context manager autour de MapViewOfFile / UnmapViewOfFile.
    Garantit le démappage même en cas d'exception → pas de leak mémoire.
    """
    view = ctypes.windll.kernel32.MapViewOfFile(handle, _FILE_MAP_READ, 0, 0, size)
    if not view:
        raise OSError("MapViewOfFile a échoué")
    try:
        yield view
    finally:
        ctypes.windll.kernel32.UnmapViewOfFile(view)


class SystemMonitor:
    """
    Moniteur des ressources système Windows.
    Toutes les méthodes sont thread-safe (lecture seule de données système).
    """

    # Nom du bloc de mémoire partagée HWiNFO — défini dans la doc HWiNFO SDK
    _HWINFO_SHMEM_NAME = "Global\\HWiNFO_SENS_SM2"

    def __init__(self) -> None:
        # None = pas encore testé, False = HWiNFO absent (évite les retries inutiles)
        self._hwinfo_available : Optional[bool] = None

    # -------------------------------------------------------------------------

    def get_cpu_usage(self) -> int:
        """
        Retourne le pourcentage d'utilisation CPU global.
        interval=0.0 : lecture non-bloquante du dernier échantillon psutil.
        """
        try:
            return int(psutil.cpu_percent(interval=0.0))
        except Exception as e:
            log.warning(f"CPU usage read error: {e}")
            return 0

    # -------------------------------------------------------------------------

    def get_ram_usage(self) -> float:
        """
        Retourne le pourcentage d'utilisation RAM (0.0-100.0), 1 décimale.
        """
        try:
            return round(psutil.virtual_memory().percent, 1)
        except Exception as e:
            log.warning(f"RAM usage read error: {e}")
            return 0.0

    # -------------------------------------------------------------------------

    def get_fps(self) -> int:
        """
        Lit le FPS depuis HWiNFO.
        Si HWiNFO n'est pas là, on retourne 0 sans réessayer à chaque tick.
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
        Lecture du FPS depuis HWiNFO Shared Memory.

        Structure simplifiée :
          Offset 0   : Header (40 octets)
            +28 : uint32  num_sensors
            +32 : uint32  num_elements
          Offset 40  : Tableau d'éléments (ELEMENT_SIZE = 128 octets chacun)
            +8  : char[64]  label    (ex: "GPU1 FPS")
            +88 : float     value
        """
        kernel32 = ctypes.windll.kernel32

        handle = kernel32.OpenFileMappingW(
            _FILE_MAP_READ, False, self._HWINFO_SHMEM_NAME
        )
        if not handle:
            raise OSError("HWiNFO shared memory non disponible")

        try:
            self._hwinfo_available = True

            HEADER_SIZE  = 40
            ELEMENT_SIZE = 128

            # --- Lecture du header pour connaître le nombre d'éléments
            with _map_view(handle, HEADER_SIZE) as view:
                header       = (ctypes.c_byte * HEADER_SIZE).from_address(view)
                header_bytes = bytes(header)
                num_elements = struct.unpack_from("<I", header_bytes, 32)[0]

            if num_elements == 0:
                return 0

            # --- Lecture de tous les éléments pour trouver "FPS"
            total_size = HEADER_SIZE + num_elements * ELEMENT_SIZE
            with _map_view(handle, total_size) as view:
                data       = (ctypes.c_byte * total_size).from_address(view)
                data_bytes = bytes(data)

                for i in range(num_elements):
                    offset = HEADER_SIZE + i * ELEMENT_SIZE

                    # Label : C-string null-terminée à offset+8, max 64 chars
                    label_raw = data_bytes[offset + 8 : offset + 8 + 64]
                    label     = label_raw.split(b'\x00')[0].decode('utf-8', errors='ignore')

                    if 'fps' in label.lower() or 'frame' in label.lower():
                        # Valeur float little-endian à offset+88
                        val = struct.unpack_from("<f", data_bytes, offset + 88)[0]
                        return int(val)

            return 0

        finally:
            kernel32.CloseHandle(handle)
