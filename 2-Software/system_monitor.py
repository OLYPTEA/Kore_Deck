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
import time
from collections import deque
from contextlib import contextmanager
from typing import Optional

import psutil

from logger import log


# Constantes Win32
_FILE_MAP_READ = 0x0004

# Fenêtre de lissage CPU/RAM :
#   - 1 échantillon brut par seconde (suffisant, psutil renvoie déjà du %)
#   - moyenne glissante sur 3 échantillons → valeur publiée stable, refresh "perçu" 3 s
# Évite les sautillements visuels dus aux pics CPU instantanés capturés à 10 Hz.
_CPU_SAMPLE_INTERVAL = 1.0
_CPU_WINDOW_SIZE     = 3


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

        # Offset (en octets) de la sonde FPS dans la SHM HWiNFO une fois localisée.
        # Évite de re-scanner tous les capteurs à chaque appel — le layout HWiNFO
        # est stable tant que HWiNFO ne redémarre pas.
        self._fps_offset : Optional[int] = None

        # --- Lissage CPU/RAM
        # On garde N échantillons bruts dans une deque bornée. La moyenne est
        # recalculée au max toutes les 1 s ; les consommateurs (boucle agent à
        # 5-10 Hz) lisent toujours la même valeur cachée entre deux samples.
        self._cpu_samples : deque  = deque(maxlen=_CPU_WINDOW_SIZE)
        self._ram_samples : deque  = deque(maxlen=_CPU_WINDOW_SIZE)
        self._cached_cpu  : int    = 0
        self._cached_ram  : float  = 0.0
        self._last_sample_t : float = 0.0

    # -------------------------------------------------------------------------

    def _maybe_sample(self) -> None:
        """
        Échantillonne CPU/RAM si la dernière mesure date d'au moins 1 s.
        Recalcule la moyenne glissante seulement quand un nouvel échantillon
        est ajouté → coût quasi nul pour les appels rapprochés.
        """
        now = time.monotonic()
        if now - self._last_sample_t < _CPU_SAMPLE_INTERVAL:
            return
        self._last_sample_t = now

        try:
            self._cpu_samples.append(psutil.cpu_percent(interval=0.0))
        except Exception as e:
            log.warning(f"CPU usage read error: {e}")

        try:
            self._ram_samples.append(psutil.virtual_memory().percent)
        except Exception as e:
            log.warning(f"RAM usage read error: {e}")

        # Moyennes recalculées une fois par sample, pas à chaque getter
        if self._cpu_samples:
            self._cached_cpu = int(sum(self._cpu_samples) / len(self._cpu_samples))
        if self._ram_samples:
            self._cached_ram = round(sum(self._ram_samples) / len(self._ram_samples), 1)

    # -------------------------------------------------------------------------

    def get_cpu_usage(self) -> int:
        """
        Retourne le % CPU moyenné sur la fenêtre de lissage (3 s par défaut).
        Appelable à haute fréquence sans coût : la valeur n'est mise à jour
        qu'une fois par seconde au maximum.
        """
        self._maybe_sample()
        return self._cached_cpu

    # -------------------------------------------------------------------------

    def get_ram_usage(self) -> float:
        """
        Retourne le % RAM moyenné sur la fenêtre de lissage, 1 décimale.
        Même cadence que get_cpu_usage() — sample partagé.
        """
        self._maybe_sample()
        return self._cached_ram

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

            # --- Fast path : offset déjà connu, on ne mappe que 128 octets
            if self._fps_offset is not None:
                map_size = self._fps_offset + ELEMENT_SIZE
                with _map_view(handle, map_size) as view:
                    elem = bytes(
                        (ctypes.c_byte * ELEMENT_SIZE).from_address(view + self._fps_offset)
                    )
                # Sanity check : on vérifie que le label correspond toujours.
                # Si HWiNFO a réordonné ses capteurs, on invalide et on re-scanne.
                label = elem[8:8 + 64].split(b'\x00')[0].decode('utf-8', errors='ignore').lower()
                if 'fps' in label or 'frame' in label:
                    return int(struct.unpack_from("<f", elem, 88)[0])
                self._fps_offset = None   # Layout invalidé → full scan ci-dessous

            # --- Slow path : lecture du header pour le nombre d'éléments
            with _map_view(handle, HEADER_SIZE) as view:
                header_bytes = bytes((ctypes.c_byte * HEADER_SIZE).from_address(view))
                num_elements = struct.unpack_from("<I", header_bytes, 32)[0]

            if num_elements == 0:
                return 0

            # --- Scan complet pour localiser FPS, puis on mémorise l'offset
            total_size = HEADER_SIZE + num_elements * ELEMENT_SIZE
            with _map_view(handle, total_size) as view:
                data_bytes = bytes((ctypes.c_byte * total_size).from_address(view))

                for i in range(num_elements):
                    offset    = HEADER_SIZE + i * ELEMENT_SIZE
                    label_raw = data_bytes[offset + 8 : offset + 8 + 64]
                    label     = label_raw.split(b'\x00')[0].decode('utf-8', errors='ignore').lower()

                    if 'fps' in label or 'frame' in label:
                        self._fps_offset = offset   # Cache pour les appels suivants
                        return int(struct.unpack_from("<f", data_bytes, offset + 88)[0])

            return 0

        finally:
            kernel32.CloseHandle(handle)
