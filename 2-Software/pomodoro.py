# =============================================================================
# pomodoro.py — Minuteur Pomodoro avec gestion des sessions
#
# =============================================================================

import time
from enum import Enum, auto
from typing import Tuple

from logger import log
from config import config


class PomoState(Enum):
    """États possibles du minuteur."""
    IDLE        = auto()   # Pas démarré / réinitialisé
    WORK        = auto()   # Session de travail en cours
    SHORT_BREAK = auto()   # Pause courte (5 min par défaut)
    LONG_BREAK  = auto()   # Pause longue après N sessions (15 min par défaut)


class PomodoroTimer:
    """
    Minuteur Pomodoro non-bloquant.

    Design : tout le calcul de temps est fait à la lecture (get_remaining),
    pas à l'écriture. On stocke uniquement _start_time et on calcule
    le temps restant = duration - (now - start_time).

    La pause est gérée en sauvegardant le temps écoulé avant la pause
    (_pause_elapsed) et en recalculant _start_time à la reprise.
    """

    def __init__(self) -> None:
        self._state         : PomoState = PomoState.IDLE
        self._start_time    : float     = 0.0
        self._duration_sec  : int       = config.pomodoro.default_duration_min * 60
        self._session_count : int       = 0     # Nombre de sessions WORK complétées

        self._paused        : bool  = False
        self._pause_elapsed : float = 0.0   # Secondes écoulées avant la mise en pause

    # =========================================================================
    # Contrôles publics
    # =========================================================================

    def toggle(self) -> None:
        """
        Lance, met en pause ou reprend le timer selon l'état courant.

        Transitions :
          IDLE + toggle()        → WORK démarre
          WORK (actif) + toggle() → mise en pause
          WORK (pausé) + toggle() → reprise
        """
        if self._state == PomoState.IDLE:
            self._start_work()
        elif self._paused:
            self._resume()
        else:
            self._pause()

    def reset(self) -> None:
        """
        Réinitialise complètement le minuteur.
        Remet le compteur de sessions à 0 (utile en début de journée).
        """
        self._state         = PomoState.IDLE
        self._paused        = False
        self._pause_elapsed = 0.0
        self._session_count = 0
        log.info("Pomodoro réinitialisé")

    def set_duration(self, minutes: int) -> None:
        """
        Modifie la durée d'une session de travail.
        Appelé par le potentiomètre P4 en mode FOCUS (mapping 0-100 → 5-60 min).

        Effet immédiat : si une session WORK est en cours, le temps restant
        est recalculé en live (peut passer à zéro si on réduit en dessous
        du temps déjà écoulé → expiration immédiate).

        @param minutes  Plage 5-60 (clampée automatiquement)
        """
        minutes = max(5, min(60, minutes))
        self._duration_sec = minutes * 60
        log.info(f"Durée Pomodoro → {minutes} min")

    # =========================================================================
    # Lecture de l'état
    # =========================================================================

    def get_remaining(self) -> Tuple[int, int]:
        """
        Calcule et retourne le temps restant.
        @return  (minutes, secondes), ex: (22, 30) pour 22:30 restantes.
                 Retourne (0, 0) si IDLE ou temps expiré.
        """
        remaining = self._get_remaining_seconds()
        if remaining <= 0:
            return (0, 0)
        return (remaining // 60, remaining % 60)

    def get_session_count(self) -> int:
        """Retourne le nombre de sessions WORK complétées depuis le dernier reset."""
        return self._session_count

    def is_running(self) -> bool:
        """True si le timer est actif et non en pause (affichage indicateur UI)."""
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
        Vérifie si le timer courant est expiré et déclenche la transition d'état.
        Doit être appelée régulièrement (toutes les 5-100 ms) pour une précision correcte.
        Ne fait rien si IDLE ou en pause.
        """
        if self._state == PomoState.IDLE or self._paused:
            return   # Rien à vérifier

        if self._get_remaining_seconds() <= 0:
            self._on_timer_expired()

    # =========================================================================
    # Internals — calcul du temps
    # =========================================================================

    def _start_work(self) -> None:
        """Démarre une nouvelle session de travail depuis zéro."""
        self._state         = PomoState.WORK
        self._paused        = False
        self._pause_elapsed = 0.0
        self._start_time    = time.monotonic()
        log.info(f"Pomodoro démarré — session {self._session_count + 1} "
                 f"({self._duration_sec // 60} min)")

    def _pause(self) -> None:
        """
        Sauvegarde le temps écoulé avant de figer le timer.
        _pause_elapsed = secondes écoulées entre _start_time et maintenant.
        """
        self._pause_elapsed = time.monotonic() - self._start_time
        self._paused = True
        log.info("Pomodoro mis en pause")

    def _resume(self) -> None:
        """
        Recalcule _start_time pour que le temps restant soit inchangé.
        Si on a pausé après X secondes, le nouveau _start_time est
        X secondes dans le passé → le calcul restant = duration - X reprend.
        """
        self._start_time = time.monotonic() - self._pause_elapsed
        self._paused     = False
        log.info("Pomodoro repris")

    def _get_remaining_seconds(self) -> int:
        """
        Calcule les secondes restantes selon l'état et le temps écoulé.
        Retourne 0 (jamais négatif) — le déclenchement d'expiration se fait dans update().
        """
        if self._state == PomoState.IDLE:
            return 0
        elapsed   = time.monotonic() - self._start_time
        duration  = self._get_current_duration()
        remaining = int(duration - elapsed)
        return max(0, remaining)

    def _get_current_duration(self) -> int:
        """Durée en secondes de la phase courante selon l'état actif."""
        if self._state == PomoState.WORK:
            return self._duration_sec
        elif self._state == PomoState.SHORT_BREAK:
            return config.pomodoro.short_break_min * 60
        elif self._state == PomoState.LONG_BREAK:
            return config.pomodoro.long_break_min * 60
        return 0

    def _on_timer_expired(self) -> None:
        """
        Transition d'état à la fin d'une phase.

        Après WORK :
          - si session_count % sessions_before_long == 0 → LONG_BREAK
          - sinon → SHORT_BREAK

        Après SHORT_BREAK ou LONG_BREAK :
          - retour automatique à WORK (démarrage de la session suivante)

        _start_time est réinitialisé ici pour la nouvelle phase.
        _pause_elapsed est remis à 0 (on repart d'une phase fraîche).
        """
        if self._state == PomoState.WORK:
            self._session_count += 1
            log.info(f"Session {self._session_count} terminée")

            if self._session_count % config.pomodoro.sessions_before_long == 0:
                # Toutes les N sessions → pause longue méritée
                self._state         = PomoState.LONG_BREAK
                self._start_time    = time.monotonic()
                self._pause_elapsed = 0.0
                log.info("Pause longue démarrée")
            else:
                self._state         = PomoState.SHORT_BREAK
                self._start_time    = time.monotonic()
                self._pause_elapsed = 0.0
                log.info("Pause courte démarrée")

        elif self._state in (PomoState.SHORT_BREAK, PomoState.LONG_BREAK):
            # Fin de pause → retour au travail automatiquement
            self._start_work()
