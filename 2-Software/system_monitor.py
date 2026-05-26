import ctypes
import struct
import time
from collections import deque
from contextlib import contextmanager
from typing import Optional

import psutil

from logger import log


_FILE_MAP_READ = 0x0004

# Lissage CPU/RAM : 1 échantillon brut/s, moyenne glissante sur 3 → publication stable.
_CPU_SAMPLE_INTERVAL = 1.0
_CPU_WINDOW_SIZE = 3


@contextmanager
def _map_view(handle, size: int):
    view = ctypes.windll.kernel32.MapViewOfFile(handle, _FILE_MAP_READ, 0, 0, size)
    if not view:
        raise OSError("MapViewOfFile a échoué")
    try:
        yield view
    finally:
        ctypes.windll.kernel32.UnmapViewOfFile(view)


class SystemMonitor:
    _HWINFO_SHMEM_NAME = "Global\\HWiNFO_SENS_SM2"

    def __init__(self) -> None:
        # None = jamais tenté, False = HWiNFO absent (pas de retry).
        self._hwinfo_available : Optional[bool] = None
        # Offset de la sonde FPS — stable tant que HWiNFO ne redémarre pas.
        self._fps_offset       : Optional[int]  = None

        self._cpu_samples : deque = deque(maxlen=_CPU_WINDOW_SIZE)
        self._ram_samples : deque = deque(maxlen=_CPU_WINDOW_SIZE)
        self._cached_cpu : int   = 0
        self._cached_ram : float = 0.0
        self._last_sample_t : float = 0.0

    def _maybe_sample(self) -> None:
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

        if self._cpu_samples:
            self._cached_cpu = int(sum(self._cpu_samples) / len(self._cpu_samples))
        if self._ram_samples:
            self._cached_ram = round(sum(self._ram_samples) / len(self._ram_samples), 1)

    def get_cpu_usage(self) -> int:
        self._maybe_sample()
        return self._cached_cpu

    def get_ram_usage(self) -> float:
        self._maybe_sample()
        return self._cached_ram

    def get_fps(self) -> int:
        if self._hwinfo_available is False:
            return 0
        try:
            return self._read_hwinfo_fps()
        except Exception:
            if self._hwinfo_available is None:
                log.info("HWiNFO non disponible — FPS désactivé")
            self._hwinfo_available = False
            return 0

    # HWiNFO SHM layout :
    #   header (40o) : +28 uint32 num_sensors, +32 uint32 num_elements
    #   element (128o à partir de l'offset 40) : +8 char[64] label, +88 float value
    def _read_hwinfo_fps(self) -> int:
        kernel32 = ctypes.windll.kernel32

        handle = kernel32.OpenFileMappingW(_FILE_MAP_READ, False, self._HWINFO_SHMEM_NAME)
        if not handle:
            raise OSError("HWiNFO shared memory non disponible")

        try:
            self._hwinfo_available = True

            HEADER_SIZE  = 40
            ELEMENT_SIZE = 128

            # Fast path : offset connu — on revérifie le label avant de l'utiliser.
            if self._fps_offset is not None:
                map_size = self._fps_offset + ELEMENT_SIZE
                with _map_view(handle, map_size) as view:
                    elem = bytes(
                        (ctypes.c_byte * ELEMENT_SIZE).from_address(view + self._fps_offset)
                    )
                label = elem[8:8 + 64].split(b'\x00')[0].decode('utf-8', errors='ignore').lower()
                if 'fps' in label or 'frame' in label:
                    return int(struct.unpack_from("<f", elem, 88)[0])
                self._fps_offset = None

            with _map_view(handle, HEADER_SIZE) as view:
                header_bytes = bytes((ctypes.c_byte * HEADER_SIZE).from_address(view))
                num_elements = struct.unpack_from("<I", header_bytes, 32)[0]

            if num_elements == 0:
                return 0

            total_size = HEADER_SIZE + num_elements * ELEMENT_SIZE
            with _map_view(handle, total_size) as view:
                data_bytes = bytes((ctypes.c_byte * total_size).from_address(view))

                for i in range(num_elements):
                    offset    = HEADER_SIZE + i * ELEMENT_SIZE
                    label_raw = data_bytes[offset + 8 : offset + 8 + 64]
                    label     = label_raw.split(b'\x00')[0].decode('utf-8', errors='ignore').lower()

                    if 'fps' in label or 'frame' in label:
                        self._fps_offset = offset
                        return int(struct.unpack_from("<f", data_bytes, offset + 88)[0])

            return 0

        finally:
            kernel32.CloseHandle(handle)
