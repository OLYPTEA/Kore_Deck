# =============================================================================
# pomodoro.py — Minuteur Pomodoro avec gestion des sessions
#
# Cycle standard :
#   25 min travail → 5 min pause courte (×4) → 15 min pause longue
#
# États : IDLE → WORK → SHORT_BREAK → WORK → ... → LONG_BREAK → WORK
# =============================================================================

import time
from enum import Enum, auto
from typing import Tuple

from logger import log
from config import config


class PomoState(Enum):
    IDLE        = auto()
    WORK        = auto()
    SHORT_BREAK = auto()
    LONG_BREAK  = auto()


class PomodoroTimer:
    """
    Minuteur Pomodoro avec comptage de sessions et pauses automatiques.
    Non-bloquant : basé sur time.monotonic(), à appeler dans la boucle principale.
    """

    def __init__(self) -> None:
        self._state          : PomoState = PomoState.IDLE
        self._start_time     : float     = 0.0
        self._duration_sec   : int       = config.pomodoro.default_duration_min * 60
        self._session_count  : int       = 0
        self._paused         : bool      = False
        self._pause_elapsed  : float     = 0.0  # Temps écoulé avant pause

    # =========================================================================
    # Contrôles
    # =========================================================================

    def toggle(self) -> None:
        """Lance, met en pause ou reprend le timer selon l'état actuel."""
        if self._state == PomoState.IDLE:
            self._start_work()
        elif self._paused:
            self._resume()
        else:
            self._pause()

    def reset(self) -> None:
        """Réinitialise complètement le timer (retour à IDLE, sessions = 0)."""
        self._state         = PomoState.IDLE
        self._paused        = False
        self._pause_elapsed = 0.0
        self._session_count = 0
        log.info("Pomodoro réinitialisé")

    def set_duration(self, minutes: int) -> None:
        """
        Modifie la durée de travail (via potentiomètre P4 en mode FOCUS).
        Plage : 5-60 minutes.
        """
        minutes = max(5, min(60, minutes))
        self._duration_sec = minutes * 60
        log.info(f"Durée Pomodoro → {minutes} min")

    # =========================================================================
    # Lecture de l'état
    # =========================================================================

    def get_remaining(self) -> Tuple[int, int]:
        """
        Retourne le temps restant sous forme (minutes, secondes).
        Retourne (0, 0) si IDLE.
        """
        remaining = self._get_remaining_seconds()
        if remaining <= 0:
            return (0, 0)
        return (remaining // 60, remaining % 60)

    def get_session_count(self) -> int:
        return self._session_count

    def is_running(self) -> bool:
        return self._state != PomoState.IDLE and not self._paused

    def is_paused(self) -> bool:
        return self._paused

    def get_state(self) -> PomoState:
        return self._state

    # =========================================================================
    # Mise à jour (à appeler dans la boucle principale)
    # =========================================================================

    def update(self) -> None:
        """
        Vérifie si le timer courant est expiré et déclenche la transition.
        À appeler régulièrement (toutes les 100ms environ).
        """
        if self._state == PomoState.IDLE or self._paused:
            return

        if self._get_remaining_seconds() <= 0:
            self._on_timer_expired()

    # =========================================================================
    # Privé
    # =========================================================================

    def _start_work(self) -> None:
        self._state       = PomoState.WORK
        self._paused      = False
        self._pause_elapsed = 0.0
        self._start_time  = time.monotonic()
        log.info(f"Pomodoro démarré — session {self._session_count + 1} "
                 f"({self._duration_sec // 60} min)")

    def _pause(self) -> None:
        self._pause_elapsed = time.monotonic() - self._start_time
        self._paused = True
        log.info("Pomodoro mis en pause")

    def _resume(self) -> None:
        self._start_time = time.monotonic() - self._pause_elapsed
        self._paused = False
        log.info("Pomodoro repris")

    def _get_remaining_seconds(self) -> int:
        if self._state == PomoState.IDLE:
            return 0
        elapsed   = time.monotonic() - self._start_time
        duration  = self._get_current_duration()
        remaining = int(duration - elapsed)
        return max(0, remaining)

    def _get_current_duration(self) -> int:
        if self._state == PomoState.WORK:
            return self._duration_sec
        elif self._state == PomoState.SHORT_BREAK:
            return config.pomodoro.short_break_min * 60
        elif self._state == PomoState.LONG_BREAK:
            return config.pomodoro.long_break_min * 60
        return 0

    def _on_timer_expired(self) -> None:
        if self._state == PomoState.WORK:
            self._session_count += 1
            log.info(f"Session {self._session_count} terminée")
            if self._session_count % config.pomodoro.sessions_before_long == 0:
                self._state      = PomoState.LONG_BREAK
                self._start_time = time.monotonic()
                self._pause_elapsed = 0.0
                log.info("Pause longue démarrée")
            else:
                self._state      = PomoState.SHORT_BREAK
                self._start_time = time.monotonic()
                self._pause_elapsed = 0.0
                log.info("Pause courte démarrée")

        elif self._state in (PomoState.SHORT_BREAK, PomoState.LONG_BREAK):
            self._start_work()
