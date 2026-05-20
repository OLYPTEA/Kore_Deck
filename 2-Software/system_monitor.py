# =============================================================================
# system_monitor.py — Monitoring des ressources systeme
#
# CPU / RAM : via psutil, rien de fancy
# FPS       : via HWiNFO64 Shared Memory — optionnel, désactivé si HWiNFO pas lancé
#
# pour le FPS : HWiNFO64 expose ses capteurs en mémoire partagée ("Global\HWiNFO_SENS_SM2").
# on lit ce bloc directement avec les API Win32, pas besoin de DLL tierce.
# pour que ça marche : HWiNFO64 doit être lancé avec "Shared Memory Support" activé
# (dans ses paramètres). si c'est pas le cas, get_fps() retourne 0 sans planter.
# =============================================================================

import ctypes
import struct
from typing import Optional

import psutil

from logger import log


class SystemMonitor:
    """
    Moniteur des ressources système Windows.
    Toutes les méthodes sont thread-safe (lecture seule de données système).
    """

    # Nom du bloc de mémoire partagée HWiNFO — défini dans la doc HWiNFO SDK
    _HWINFO_SHMEM_NAME = "Global\\HWiNFO_SENS_SM2"

    def __init__(self) -> None:
        # None = pas encore testé, False = HWiNFO absent (évite les tentatives répétées)
        self._hwinfo_available : Optional[bool] = None

    # -------------------------------------------------------------------------

    def get_cpu_usage(self) -> int:
        """
        Retourne le pourcentage d'utilisation CPU global (toutes logiques confondues).

        interval=0.0 : lecture non-bloquante du dernier échantillon psutil.
        psutil maintient en interne un cache mis à jour en arrière-plan.
        Retourne 0 en cas d'erreur.
        """
        try:
            return int(psutil.cpu_percent(interval=0.0))
        except Exception as e:
            log.warning(f"CPU usage read error: {e}")
            return 0

    # -------------------------------------------------------------------------

    def get_ram_usage(self) -> float:
        """
        Retourne le pourcentage d'utilisation de la RAM physique (0.0-100.0).
        Arrondi à 1 décimale pour le format de la trame série (RAM:61.2).
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
        Si HWiNFO n'est pas là, on retourne 0 sans essayer à chaque tick —
        on a déjà tenté une fois, pas besoin de rejouer la même erreur 10 fois par seconde.
        """
        if self._hwinfo_available is False:
            return 0   # Court-circuit — on sait déjà que HWiNFO est absent

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

        Structure de la mémoire partagée (layout simplifié) :
          Offset 0   : Header (40 octets)
            +28 : uint32  num_sensors   — nombre de capteurs
            +32 : uint32  num_elements  — nombre total d'éléments (valeurs)
          Offset 40  : Tableau d'éléments (ELEMENT_SIZE = 128 octets chacun)
            +8  : char[64]  label       — nom du capteur (ex: "GPU1 FPS")
            +88 : float     value       — valeur courante

        On cherche le premier élément dont le label contient "fps" ou "frame"
        (insensible à la casse) et on retourne sa valeur entière.
        """
        kernel32 = ctypes.windll.kernel32

        # Ouvre le mapping en lecture seule (FILE_MAP_READ = 0x0004)
        handle = kernel32.OpenFileMappingW(
            0x0004,  # FILE_MAP_READ
            False,
            self._HWINFO_SHMEM_NAME
        )

        if not handle:
            raise OSError("HWiNFO shared memory non disponible")

        self._hwinfo_available = True

        try:
            HEADER_SIZE  = 40     # Taille du header HWiNFO en octets
            ELEMENT_SIZE = 128    # Taille d'un élément capteur en octets

            # --- Lecture du header pour connaître le nombre d'éléments
            view = ctypes.windll.kernel32.MapViewOfFile(
                handle, 0x0004, 0, 0, HEADER_SIZE
            )
            if not view:
                return 0

            header       = (ctypes.c_byte * HEADER_SIZE).from_address(view)
            header_bytes = bytes(header)

            # num_sensors  à l'offset 28 (non utilisé ici mais disponible)
            # num_elements à l'offset 32 : nombre d'éléments à parcourir
            num_sensors  = struct.unpack_from("<I", header_bytes, 28)[0]
            num_elements = struct.unpack_from("<I", header_bytes, 32)[0]

            ctypes.windll.kernel32.UnmapViewOfFile(view)

            if num_elements == 0:
                return 0

            # --- Lecture de tous les éléments pour trouver "FPS"
            total_size = HEADER_SIZE + num_elements * ELEMENT_SIZE
            view2 = ctypes.windll.kernel32.MapViewOfFile(
                handle, 0x0004, 0, 0, total_size
            )
            if not view2:
                return 0

            data       = (ctypes.c_byte * total_size).from_address(view2)
            data_bytes = bytes(data)

            fps_value = 0
            for i in range(num_elements):
                offset    = HEADER_SIZE + i * ELEMENT_SIZE

                # Le label est une chaîne C (null-terminated) à l'offset +8, max 64 chars
                label_raw = data_bytes[offset + 8 : offset + 8 + 64]
                label     = label_raw.split(b'\x00')[0].decode('utf-8', errors='ignore')

                if 'fps' in label.lower() or 'frame' in label.lower():
                    # La valeur float est stockée à l'offset +88 en little-endian
                    val       = struct.unpack_from("<f", data_bytes, offset + 88)[0]
                    fps_value = int(val)
                    break   # On prend le premier capteur FPS trouvé

            ctypes.windll.kernel32.UnmapViewOfFile(view2)
            return fps_value

        finally:
            # Toujours fermer le handle, même en cas d'exception
            kernel32.CloseHandle(handle)
