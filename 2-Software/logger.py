# =============================================================================
# logger.py — Logging centralisé avec rotation de fichier
#
# Deux handlers configurés :
#   1. Console (stdout) : format court, horodatage HH:MM:SS — pour le développement
#   2. Fichier rotatif  : format long avec module — pour le diagnostic
#
# Rotation : le fichier koredeck.log est limité à 1 Mo.
# Quand il est plein, il est renommé koredeck.log.1 et un nouveau est créé.
# Les 3 derniers fichiers sont conservés (3 Mo d'historique maximum).
#
# Utilisation dans les autres modules :
#   from logger import log
#   log.info("Message")     → [14:32:05] INFO     Message
#   log.debug("Détail")     → [14:32:05] DEBUG    Détail  (visible uniquement en mode DEBUG)
#   log.warning("Alerte")   → [14:32:05] WARNING  Alerte
#   log.error("Erreur")     → [14:32:05] ERROR    Erreur
# =============================================================================

import logging
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path

_LOGGER_NAME = "koredeck"
_LOG_FILENAME = "koredeck.log"


def setup_logger(name: str = _LOGGER_NAME, level: str = "INFO") -> logging.Logger:
    """
    Configure le logger et retourne l'instance.
    Idempotent : si appelé deux fois, retourne le même logger sans recréer les handlers
    (sinon chaque message s'affiche en double).
    """
    logger = logging.getLogger(name)
    logger.setLevel(getattr(logging, level.upper(), logging.INFO))

    if logger.handlers:
        # Déjà configuré — on met juste à jour le niveau si l'appelant le demande
        return logger

    # --- Formatter console : compact, lisible en temps réel
    console_fmt = logging.Formatter(
        fmt="[%(asctime)s] %(levelname)-8s %(message)s",
        datefmt="%H:%M:%S"
    )

    # --- Formatter fichier : complet, avec module source pour le diagnostic
    file_fmt = logging.Formatter(
        fmt="%(asctime)s | %(levelname)-8s | %(module)-20s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )

    # --- Handler console (stdout pour compatibilité avec les redirections)
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(console_fmt)
    console_handler.setLevel(logging.DEBUG)

    # --- Handler fichier rotatif (à côté des scripts du projet)
    log_path = Path(__file__).parent / _LOG_FILENAME
    file_handler = RotatingFileHandler(
        log_path,
        maxBytes=1_000_000,
        backupCount=3,
        encoding="utf-8"
    )
    file_handler.setFormatter(file_fmt)
    file_handler.setLevel(logging.DEBUG)

    logger.addHandler(console_handler)
    logger.addHandler(file_handler)

    return logger


# Dans chaque fichier du projet : "from logger import log" et c'est bon
log = setup_logger()
