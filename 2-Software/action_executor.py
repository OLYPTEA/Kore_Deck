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
# =============================================================================

import subprocess
import time
import pyautogui
import screen_brightness_control as sbc
from typing import TYPE_CHECKING

from logger import log
from audio_manager import AudioManager
from pomodoro import PomodoroTimer

# par défaut pyautogui plante si la souris est dans un coin d'écran (mesure de sécurité).
# on désactive ça parce que notre StreamDeck doit marcher quoi qu'il arrive.
pyautogui.FAILSAFE = False

# sans ça pyautogui attend 0.1 s entre chaque touche — on le voit vraiment
pyautogui.PAUSE    = 0.0


class ActionExecutor:
    """
    Exécute toutes les actions déclenchées par les boutons et potentiomètres.

    Chaque action est une méthode privée. Les deux dicts _ACTION_MAP et _POT_MAP
    font le lien entre les chaînes reçues du firmware et ces méthodes.

    Ajouter une nouvelle action = 1 méthode + 1 entrée dans le dict.
    """

    def __init__(self, audio: AudioManager, pomodoro: PomodoroTimer) -> None:
        # Injection de dépendance : évite d'avoir des singletons globaux
        self._audio    = audio
        self._pomodoro = pomodoro

        # Edge-triggers consommés par agent._main_loop : chaque toggle UI bump
        # l'horodatage, l'agent compare avec sa dernière valeur vue et relit
        # l'état Windows immédiatement au lieu d'attendre le poll de 5 s.
        self.dnd_toggled_at: float = 0.0
        self.obs_toggled_at: float = 0.0

    # =========================================================================
    # Dispatch principal
    # =========================================================================

    def execute_action(self, action: str) -> None:
        """
        Reçoit le nom d'une action et appelle le handler correspondant.
        Les suffixes _LONG et _DBL (appui long / double) sont gérés par le firmware
        et transmis tels quels ici — ils doivent figurer dans _ACTION_MAP si utilisés.

        @param action  Ex: "MEDIA_PLAY", "MIC_TOGGLE_LONG", "SCREENSHOT_DBL"
        """
        log.debug(f"Action : {action}")
        handler = self._ACTION_MAP.get(action)
        if handler:
            try:
                handler(self)   # Appel de la méthode non-liée avec self
            except Exception as e:
                log.error(f"Erreur action '{action}' : {e}")
        else:
            log.warning(f"Action inconnue : {action}")

    def execute_pot(self, pot_action: str, value: int) -> None:
        """
        Reçoit le nom d'un potentiomètre et sa valeur brute (0-100, déjà normalisée
        par le firmware depuis les 12 bits ADC).

        @param pot_action  Ex: "VOL_MASTER", "BRIGHTNESS"
        @param value       Entier 0-100 (firmware garantit cette plage)
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

    def _media_play(self):
        """Lecture/pause — utilise la touche média virtuelle (fonctionne sur tous les lecteurs)."""
        pyautogui.press('playpause')

    def _media_next(self):
        """Piste suivante — touche média virtuelle."""
        pyautogui.press('nexttrack')

    def _media_prev(self):
        """Piste précédente — touche média virtuelle."""
        pyautogui.press('prevtrack')

    def _mic_toggle(self):
        """Bascule le mute du microphone par défaut via pycaw."""
        self._audio.toggle_mic_mute()

    def _screenshot(self):
        """Capture d'écran Windows — ouvre l'outil de capture (Win+Shift+S)."""
        pyautogui.hotkey('win', 'shift', 's')

    def _open_explorer(self):
        """Ouvre l'explorateur de fichiers Windows."""
        pyautogui.hotkey('win', 'e')

    def _sleep_screens(self):
        """
        Éteint les écrans sans mettre le PC en veille.
        On appelle user32.dll via PowerShell parce qu'il n'y a pas de lib Python propre pour ça.
        WM_SYSCOMMAND + SC_MONITORPOWER + paramètre 2 = éteint les moniteurs.
        Ouais c'est un peu hacky mais ça marche parfaitement.
        """
        subprocess.Popen(
            ['powershell', '-Command',
             '(Add-Type -MemberDefinition "[DllImport(\\"user32.dll\\")]'
             'public static extern int SendMessage(int hWnd,int hMsg,int wParam,int lParam);"'
             ' -Name U32 -PassThru)::SendMessage(-1,0x0112,0xF170,2)'],
            shell=True
        )

    # =========================================================================
    # Actions MAKING — Fusion 360 / création 3D
    # =========================================================================

    def _undo(self):       pyautogui.hotkey('ctrl', 'z')
    def _redo(self):       pyautogui.hotkey('ctrl', 'y')
    def _save(self):       pyautogui.hotkey('ctrl', 's')
    def _view_home(self):  pyautogui.press('h')          # Fusion 360 : remet la vue Home

    def _section_view(self):
        """Vue en coupe Fusion 360 — toggle avec Shift+S."""
        pyautogui.hotkey('shift', 's')

    def _new_component(self):
        """Nouveau composant Fusion 360."""
        pyautogui.hotkey('ctrl', 'n')

    def _export_stl(self):
        """Exporte en STL via Ctrl+Shift+E (raccourci Fusion 360)."""
        pyautogui.hotkey('ctrl', 'shift', 'e')

    # =========================================================================
    # Actions FOCUS — productivité / bureau
    # =========================================================================

    def _pomo_toggle(self):  self._pomodoro.toggle()
    def _pomo_reset(self):   self._pomodoro.reset()

    def _open_notion(self):
        """Ouvre Notion via le protocole URI notion:// (nécessite l'app desktop installée)."""
        subprocess.Popen(['start', '', 'notion://'], shell=True)

    def _dnd_toggle(self):
        """
        Active/désactive le mode Ne pas déranger.
        Microsoft n'expose pas d'API propre pour ça en Python, donc on ouvre et referme
        le centre de notifications en espérant que ça toggle le bon bouton.
        TODO: remplacer par Focus Assist API quand quelqu'un l'aura wrappée correctement.
        """
        pyautogui.hotkey('win', 'a')   # ouvre le centre de notifs
        time.sleep(0.3)                # laisse le temps au panneau de s'afficher
        pyautogui.hotkey('win', 'a')   # referme — le clic direct sur le toggle DND c'est trop fragile
        self.dnd_toggled_at = time.monotonic()

    def _snap_left(self):       pyautogui.hotkey('win', 'left')
    def _snap_right(self):      pyautogui.hotkey('win', 'right')
    def _next_vdesktop(self):   pyautogui.hotkey('ctrl', 'win', 'right')   # Bureau virtuel suivant

    # =========================================================================
    # Actions GAME — streaming / gaming
    # =========================================================================

    def _game_mic(self):
        """Mute micro pendant une session de jeu (même handler que HOME)."""
        self._audio.toggle_mic_mute()

    def _discord_mute(self):
        """Raccourci Discord global pour mute/unmute micro (Ctrl+Shift+M)."""
        pyautogui.hotkey('ctrl', 'shift', 'm')

    def _game_screenshot(self):
        """Capture Steam — F12 est le raccourci par défaut de l'overlay Steam."""
        pyautogui.press('f12')

    def _clip_30s(self):
        """
        Clip les 30 dernières secondes via Xbox Game Bar.
        Win+Alt+G = 'Enregistrer les 30 dernières secondes'.
        Nécessite que l'enregistrement en arrière-plan soit activé dans les paramètres Xbox.
        """
        pyautogui.hotkey('win', 'alt', 'g')

    def _obs_toggle(self):
        """Lance/bascule OBS via le protocole URI obs:// (nécessite OBS installé)."""
        subprocess.Popen(['start', '', 'obs://'], shell=True)
        self.obs_toggled_at = time.monotonic()

    def _alt_tab(self):         pyautogui.hotkey('alt', 'tab')
    def _task_manager(self):    pyautogui.hotkey('ctrl', 'shift', 'esc')

    # =========================================================================
    # Handlers potentiomètres
    # =========================================================================

    def _pot_vol_master(self, v: int):  self._audio.set_master_volume(v)
    def _pot_vol_music(self, v: int):   self._audio.set_spotify_volume(v)

    def _pot_brightness(self, v: int):
        """
        Contrôle la luminosité du ou des moniteurs via screen_brightness_control.
        Fonctionne avec les moniteurs DDC/CI et les écrans intégrés (laptops).
        En cas d'échec (moniteur sans DDC), on log et on continue.
        """
        try:
            sbc.set_brightness(v)
        except Exception as e:
            log.warning(f"Luminosité : {e}")

    def _pot_mic_gain(self, v: int):    self._audio.set_mic_gain(v)

    def _pot_zoom(self, v: int):
        """
        Zoom Fusion 360 via Ctrl+= / Ctrl+-.
        Pas d'API directe donc on simule des pressions de touche.
        50 = neutre, en dessous = dézoom, au dessus = zoom.
        Le sleep entre chaque pression c'est pour que Fusion 360 ait le temps de les traiter.
        """
        import time
        steps = int((v - 50) / 10)   # Calcul de l'écart normalisé
        if steps > 0:
            for _ in range(steps):
                pyautogui.hotkey('ctrl', '=')
                time.sleep(0.05)
        elif steps < 0:
            for _ in range(-steps):
                pyautogui.hotkey('ctrl', '-')
                time.sleep(0.05)

    def _pot_opacity(self, v: int):      pass   # TODO: à implémenter selon l'app CAO utilisée
    def _pot_rotation(self, v: int):     pass   # TODO: pareil
    def _pot_white_noise(self, v: int):  pass   # TODO: dépend de l'app bruit blanc choisie

    def _pot_pomo_duration(self, v: int):
        """
        Ajuste la durée de travail Pomodoro en temps réel via le potentiomètre P4 (mode FOCUS).
        Mapping linéaire : 0% → 5 min, 100% → 60 min.
        """
        minutes = 5 + int(v * 55 / 100)   # Plage 5-60 min
        self._pomodoro.set_duration(minutes)

    def _pot_vol_game(self, v: int):     self._audio.set_game_volume(v)
    def _pot_vol_discord(self, v: int):  self._audio.set_discord_volume(v)

    # =========================================================================
    # Tables de dispatch — définies au niveau classe (une seule allocation)
    # =========================================================================

    # Clé = chaîne reçue du firmware (après "ACTION:"), valeur = méthode non-liée
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

    # Clé = chaîne reçue du firmware (après "POT:"), valeur = méthode non-liée (v: int)
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
