import time
from enum import Enum, auto
from typing import Tuple

from logger import log
from config import config


class PomoState(Enum):
    IDLE  = auto()
    WORK  = auto()
    SHORT_BREAK = auto()
    LONG_BREAK  = auto()


class PomodoroTimer:
    # Temps stocké uniquement comme _start_time ; tout le reste est calculé à la lecture.
    # Pause : on mémorise _pause_elapsed et on recale _start_time à la reprise.

    def __init__(self) -> None:
        self._state   : PomoState = PomoState.IDLE
        self._start_time  : float     = 0.0
        self._duration_sec : int       = config.pomodoro.default_duration_min * 60
        self._session_count : int       = 0

        self._paused : bool  = False
        self._pause_elapsed : float = 0.0

    #Contrôles

    def toggle(self) -> None:
        if self._state == PomoState.IDLE:
            self._start_work()
        elif self._paused:
            self._resume()
        else:
            self._pause()

    def reset(self) -> None:
        self._state   = PomoState.IDLE
        self._paused   = False
        self._pause_elapsed = 0.0
        self._session_count = 0
        log.info("Pomodoro réinitialisé")

    def set_duration(self, minutes: int) -> None:
        # Si une session est en cours et que la nouvelle durée est inférieure au temps
        # écoulé, le timer expire au prochain update().
        minutes = max(5, min(60, minutes))
        self._duration_sec = minutes * 60
        log.info(f"Durée Pomodoro → {minutes} min")

    #Lecture d'état

    def get_remaining(self) -> Tuple[int, int]:
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

    #tick

    def update(self) -> None:
        if self._state == PomoState.IDLE or self._paused:
            return
        if self._get_remaining_seconds() <= 0:
            self._on_timer_expired()

    #interne

    def _start_work(self) -> None:
        self._state = PomoState.WORK
        self._paused= False
        self._pause_elapsed = 0.0
        self._start_time = time.monotonic()
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
        elapsed = time.monotonic() - self._start_time
        duration = self._get_current_duration()
        return max(0, int(duration - elapsed))

    def _get_current_duration(self) -> int:
        if self._state == PomoState.WORK:
            return self._duration_sec
        if self._state == PomoState.SHORT_BREAK:
            return config.pomodoro.short_break_min * 60
        if self._state == PomoState.LONG_BREAK:
            return config.pomodoro.long_break_min * 60
        return 0

    def _on_timer_expired(self) -> None:
        if self._state == PomoState.WORK:
            self._session_count += 1
            log.info(f"Session {self._session_count} terminée")

            if self._session_count % config.pomodoro.sessions_before_long == 0:
                self._state = PomoState.LONG_BREAK
                self._start_time = time.monotonic()
                self._pause_elapsed = 0.0
                log.info("Pause longue démarrée")
            else:
                self._state = PomoState.SHORT_BREAK
                self._start_time = time.monotonic()
                self._pause_elapsed = 0.0
                log.info("Pause courte démarrée")

        elif self._state in (PomoState.SHORT_BREAK, PomoState.LONG_BREAK):
            self._start_work()
