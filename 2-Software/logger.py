# =============================================================================
# logger.py — Logging centralisé avec rotation de fichier
# =============================================================================

import logging
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path


def setup_logger(name: str = "streamdeck", level: str = "INFO") -> logging.Logger:
    """
    Configure et retourne le logger principal.

    Format console : [HH:MM:SS] LEVEL   message
    Format fichier : timestamp | level | module | message
    Rotation       : 1 Mo max, 3 fichiers conservés
    """
    logger = logging.getLogger(name)
    logger.setLevel(getattr(logging, level.upper(), logging.INFO))

    if logger.handlers:
        return logger  # Déjà configuré

    # --- Formatter console (lisible)
    console_fmt = logging.Formatter(
        fmt="[%(asctime)s] %(levelname)-8s %(message)s",
        datefmt="%H:%M:%S"
    )

    # --- Formatter fichier (détaillé)
    file_fmt = logging.Formatter(
        fmt="%(asctime)s | %(levelname)-8s | %(module)-20s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )

    # --- Handler console
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(console_fmt)
    console_handler.setLevel(logging.DEBUG)

    # --- Handler fichier rotatif
    log_path = Path(__file__).parent / "streamdeck.log"
    file_handler = RotatingFileHandler(
        log_path, maxBytes=1_000_000, backupCount=3, encoding="utf-8"
    )
    file_handler.setFormatter(file_fmt)
    file_handler.setLevel(logging.DEBUG)

    logger.addHandler(console_handler)
    logger.addHandler(file_handler)

    return logger


# Logger global importable
log = setup_logger()
