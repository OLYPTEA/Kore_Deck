# =============================================================================
# action_executor.py — Exécution des actions reçues depuis l'ESP32 ou l'UI
#
# Pattern de dispatch :
#   execute_action("MEDIA_PLAY") → _ACTION_MAP["MEDIA_PLAY"](self) → pyautogui.press(...)
#   execute_pot("VOL_MASTER", 73) → _POT_MAP["VOL_MASTER"](self, 73) → audio.set_master_volume(73)
#
# _ACTION_MAP et _POT_MAP sont des attributs de classe (pas d'instance) :
#   → alloués une seule fois au chargement du module, partagés par toutes les instances.
#   → les valeurs sont des références de méthodes non-liées, appelées avec self explicite.
#
# Configuration pyautogui : faite dans __init__ (pas au niveau module) pour éviter
# les effets de bord à l'import. Permet aussi aux tests d'instancier sans toucher
# aux paramètres globaux de pyautogui.
# =============================================================================

import subprocess
import threading
import time

import pyautogui
import screen_brightness_control as sbc

from logger import log
from audio_manager import AudioManager
from pomodoro import PomodoroTimer


class ActionExecutor:
    """
    Exécute toutes les actions déclenchées par les boutons et potentiomètres.

    Chaque action est une méthode privée. Les deux dicts _ACTION_MAP et _POT_MAP
    font le lien entre les chaînes reçues du firmware et ces méthodes.

    Ajouter une nouvelle action = 1 méthode + 1 entrée dans le dict.
    """

    # Guard pour la config globale pyautogui — appliquée une seule fois,
    # même si plusieurs ActionExecutor sont instanciés
    _pyautogui_configured = False

    def __init__(self, audio: AudioManager, pomodoro: PomodoroTimer) -> None:
        # Injection de dépendance : évite d'avoir des singletons globaux
        self._audio    = audio
        self._pomodoro = pomodoro

        # État partagé exposé à l'agent (lecture seule depuis l'extérieur).
        # Toggled par les actions _dnd_toggle / _obs_toggle.
        self.dnd_toggled_at : float = 0.0
        self.obs_toggled_at : float = 0.0

        self._configure_pyautogui_once()

    @classmethod
    def _configure_pyautogui_once(cls) -> None:
        """
        Désactive FAILSAFE (sinon pyautogui plante si la souris est dans un coin)
        et PAUSE (sinon 100 ms de délai entre chaque touche pressée).
        Idempotent.
        """
        if cls._pyautogui_configured:
            return
        pyautogui.FAILSAFE = False
        pyautogui.PAUSE    = 0.0
        cls._pyautogui_configured = True

    # =========================================================================
    # Dispatch principal
    # =========================================================================

    def execute_action(self, action: str) -> None:
        """
        Reçoit le nom d'une action et appelle le handler correspondant.
        Les suffixes _LONG et _DBL (appui long / double) doivent figurer
        dans _ACTION_MAP si utilisés.
        """
        log.debug(f"Action : {action}")
        handler = self._ACTION_MAP.get(action)
        if handler:
            try:
                handler(self)
            except Exception as e:
                log.error(f"Erreur action '{action}' : {e}")
        else:
            log.warning(f"Action inconnue : {action}")

    def execute_pot(self, pot_action: str, value: int) -> None:
        """
        Reçoit le nom d'un potentiomètre et sa valeur normalisée 0-100.
        """
        log.debug(f"Pot : {pot_action} = {value}")
        handler = self._POT_MAP.get(pot_action)
        if handler:
            try:
                handler(self, value)
            except Exception as e:
                log.error(f"Erreur pot '{pot_action}'={value} : {e}")
        else:
            log.warning(f"Action pot inconnue : {pot_action}")

    # =========================================================================
    # Actions HOME — multimédia + système
    # =========================================================================

    def _media_play(self) -> None:
        pyautogui.press('playpause')

    def _media_next(self) -> None:
        pyautogui.press('nexttrack')

    def _media_prev(self) -> None:
        pyautogui.press('prevtrack')

    def _mic_toggle(self) -> None:
        self._audio.toggle_mic_mute()

    def _screenshot(self) -> None:
        pyautogui.hotkey('win', 'shift', 's')

    def _open_explorer(self) -> None:
        pyautogui.hotkey('win', 'e')

    def _sleep_screens(self) -> None:
        """
        Éteint les écrans sans mettre le PC en veille.
        On passe par PowerShell + DllImport user32 — pas de lib Python propre pour ça.
        WM_SYSCOMMAND (0x0112) + SC_MONITORPOWER (0xF170) + lParam=2 = écrans OFF.
        """
        ps_code = (
            '(Add-Type -MemberDefinition '
            '"[DllImport(\\"user32.dll\\")] '
            'public static extern int SendMessage(int hWnd,int hMsg,int wParam,int lParam);" '
            '-Name U32 -PassThru)::SendMessage(-1,0x0112,0xF170,2)'
        )
        # shell=False + liste d'args explicite — évite l'interprétation shell de la string
        subprocess.Popen(['powershell.exe', '-NoProfile', '-Command', ps_code])

    # =========================================================================
    # Actions MAKING — Fusion 360 / création 3D
    # =========================================================================

    def _undo(self) -> None:        pyautogui.hotkey('ctrl', 'z')
    def _redo(self) -> None:        pyautogui.hotkey('ctrl', 'y')
    def _save(self) -> None:        pyautogui.hotkey('ctrl', 's')
    def _view_home(self) -> None:   pyautogui.press('h')

    def _section_view(self) -> None:
        pyautogui.hotkey('shift', 's')

    def _new_component(self) -> None:
        pyautogui.hotkey('ctrl', 'n')

    def _export_stl(self) -> None:
        pyautogui.hotkey('ctrl', 'shift', 'e')

    # =========================================================================
    # Actions FOCUS — productivité / bureau
    # =========================================================================

    def _pomo_toggle(self) -> None:  self._pomodoro.toggle()
    def _pomo_reset(self) -> None:   self._pomodoro.reset()

    def _open_notion(self) -> None:
        """Ouvre Notion via le protocole URI notion:// (nécessite l'app desktop)."""
        # 'start' est une commande shell builtin → shell=True nécessaire ici
        subprocess.Popen(['start', '', 'notion://'], shell=True)

    def _dnd_toggle(self) -> None:
        """
        Active/désactive le mode Ne pas déranger (Focus Assist).
        Microsoft n'expose pas d'API stable pour ça en Python.
        On marque l'horodatage pour que l'agent puisse re-lire la registry Focus Assist.

        Méthode hack : ouvrir+fermer le centre de notifs (Win+A).
        TODO: utiliser Focus Assist API quand quelqu'un l'aura wrappée.
        """
        pyautogui.hotkey('win', 'a')
        time.sleep(0.3)
        pyautogui.hotkey('win', 'a')
        self.dnd_toggled_at = time.monotonic()   # signal à l'agent de relire l'état

    def _snap_left(self) -> None:     pyautogui.hotkey('win', 'left')
    def _snap_right(self) -> None:    pyautogui.hotkey('win', 'right')
    def _next_vdesktop(self) -> None: pyautogui.hotkey('ctrl', 'win', 'right')

    # =========================================================================
    # Actions GAME — streaming / gaming
    # =========================================================================

    def _game_mic(self) -> None:
        self._audio.toggle_mic_mute()

    def _discord_mute(self) -> None:
        pyautogui.hotkey('ctrl', 'shift', 'm')

    def _game_screenshot(self) -> None:
        pyautogui.press('f12')   # Steam overlay

    def _clip_30s(self) -> None:
        """Xbox Game Bar : enregistrer les 30 dernières secondes."""
        pyautogui.hotkey('win', 'alt', 'g')

    def _obs_toggle(self) -> None:
        """Lance OBS via le protocole URI obs:// (nécessite OBS installé)."""
        subprocess.Popen(['start', '', 'obs://'], shell=True)
        self.obs_toggled_at = time.monotonic()

    def _alt_tab(self) -> None:      pyautogui.hotkey('alt', 'tab')
    def _task_manager(self) -> None: pyautogui.hotkey('ctrl', 'shift', 'esc')

    # =========================================================================
    # Handlers potentiomètres
    # =========================================================================

    def _pot_vol_master(self, v: int) -> None:  self._audio.set_master_volume(v)
    def _pot_vol_music(self, v: int) -> None:   self._audio.set_spotify_volume(v)

    def _pot_brightness(self, v: int) -> None:
        """
        Contrôle la luminosité des moniteurs (DDC/CI + écrans intégrés).
        En cas d'échec (moniteur sans DDC), on log et on continue.
        """
        try:
            sbc.set_brightness(v)
        except Exception as e:
            log.warning(f"Luminosité : {e}")

    def _pot_mic_gain(self, v: int) -> None: self._audio.set_mic_gain(v)

    def _pot_zoom(self, v: int) -> None:
        """
        Zoom Fusion 360 via Ctrl+= / Ctrl+-.
        50 = neutre, en dessous = dézoom, au dessus = zoom.

        Lancé dans un thread daemon pour ne pas bloquer le reader série
        pendant les sleep(0.05) successifs — sinon on rate des trames quand
        l'utilisateur tourne le potard vite.
        """
        steps = int((v - 50) / 10)
        if steps == 0:
            return

        def _run_zoom_burst(n: int) -> None:
            key = '=' if n > 0 else '-'
            for _ in range(abs(n)):
                pyautogui.hotkey('ctrl', key)
                time.sleep(0.05)

        threading.Thread(
            target=_run_zoom_burst, args=(steps,),
            daemon=True, name="pot-zoom-burst"
        ).start()

    def _pot_opacity(self, v: int) -> None:
        log.debug(f"OPACITY={v} (non implémenté — dépend de l'app CAO)")

    def _pot_rotation(self, v: int) -> None:
        log.debug(f"ROTATION={v} (non implémenté — dépend de l'app CAO)")

    def _pot_white_noise(self, v: int) -> None:
        log.debug(f"WHITE_NOISE={v} (non implémenté — dépend de l'app de bruit blanc)")

    def _pot_pomo_duration(self, v: int) -> None:
        """
        Mapping linéaire 0-100 → 5-60 min pour la durée Pomodoro.
        """
        minutes = 5 + int(v * 55 / 100)
        self._pomodoro.set_duration(minutes)

    def _pot_vol_game(self, v: int) -> None:    self._audio.set_game_volume(v)
    def _pot_vol_discord(self, v: int) -> None: self._audio.set_discord_volume(v)

    # =========================================================================
    # Tables de dispatch — définies au niveau classe (une seule allocation)
    # =========================================================================

    _ACTION_MAP = {
        "MEDIA_PLAY"      : _media_play,
        "MEDIA_NEXT"      : _media_next,
        "MEDIA_PREV"      : _media_prev,
        "MIC_TOGGLE"      : _mic_toggle,
        "SCREENSHOT"      : _screenshot,
        "OPEN_EXPLORER"   : _open_explorer,
        "SLEEP_SCREENS"   : _sleep_screens,
        # --- MAKING
        "UNDO"            : _undo,
        "REDO"            : _redo,
        "SAVE"            : _save,
        "VIEW_HOME"       : _view_home,
        "SECTION_VIEW"    : _section_view,
        "NEW_COMPONENT"   : _new_component,
        "EXPORT_STL"      : _export_stl,
        # --- FOCUS
        "POMO_TOGGLE"     : _pomo_toggle,
        "POMO_RESET"      : _pomo_reset,
        "OPEN_NOTION"     : _open_notion,
        "DND_TOGGLE"      : _dnd_toggle,
        "SNAP_LEFT"       : _snap_left,
        "SNAP_RIGHT"      : _snap_right,
        "NEXT_VDESKTOP"   : _next_vdesktop,
        # --- GAME
        "GAME_MIC"        : _game_mic,
        "DISCORD_MUTE"    : _discord_mute,
        "GAME_SCREENSHOT" : _game_screenshot,
        "CLIP_30S"        : _clip_30s,
        "OBS_TOGGLE"      : _obs_toggle,
        "ALT_TAB"         : _alt_tab,
        "TASK_MANAGER"    : _task_manager,
    }

    _POT_MAP = {
        "VOL_MASTER"    : _pot_vol_master,
        "VOL_MUSIC"     : _pot_vol_music,
        "VOL_GAME"      : _pot_vol_game,
        "VOL_DISCORD"   : _pot_vol_discord,
        "BRIGHTNESS"    : _pot_brightness,
        "MIC_GAIN"      : _pot_mic_gain,
        "ZOOM"          : _pot_zoom,
        "OPACITY"       : _pot_opacity,
        "ROTATION"      : _pot_rotation,
        "WHITE_NOISE"   : _pot_white_noise,
        "POMO_DURATION" : _pot_pomo_duration,
    }
