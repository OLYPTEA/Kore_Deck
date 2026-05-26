import subprocess
import time
import pyautogui
import screen_brightness_control as sbc

from logger import log
from audio_manager import AudioManager
from pomodoro import PomodoroTimer

# Le failsafe pyautogui interrompt sur un coin d'écran : indésirable ici.
pyautogui.FAILSAFE = False
pyautogui.PAUSE = 0.0


class ActionExecutor:
    def __init__(self, audio: AudioManager, pomodoro: PomodoroTimer) -> None:
        self._audion= audio
        self._pomodoro = pomodoro

        # Bumpés par les toggles DND/OBS : permettent à l'agent de re-lire
        # l'état Windows immédiatement plutôt que d'attendre le poll périodique.
        self.dnd_toggled_at: float = 0.0
        self.obs_toggled_at: float = 0.0

    #Dispatch

    def execute_action(self, action: str) -> None:
        log.debug(f"Action : {action}")
        handler = self._ACTION_MAP.get(action)
        if not handler:
            log.warning(f"Action inconnue : {action}")
            return
        try:
            handler(self)
        except Exception as e:
            log.error(f"Erreur action '{action}' : {e}")

    def execute_pot(self, pot_action: str, value: int) -> None:
        log.debug(f"Pot : {pot_action} = {value}")
        handler = self._POT_MAP.get(pot_action)
        if not handler:
            log.warning(f"Action pot inconnue : {pot_action}")
            return
        try:
            handler(self, value)
        except Exception as e:
            log.error(f"Erreur pot '{pot_action}'={value} : {e}")

    #HOME

    def _media_play(self) : pyautogui.press('playpause')
    def _media_next(self) : pyautogui.press('nexttrack')
    def _media_prev(self) : pyautogui.press('prevtrack')
    def _mic_toggle(self) : self._audio.toggle_mic_mute()
    def _screenshot(self) : pyautogui.hotkey('win', 'shift', 's')
    def _open_explorer(self) : pyautogui.hotkey('win', 'e')

    def _sleep_screens(self):
        # WM_SYSCOMMAND + SC_MONITORPOWER (0xF170) + 2 = écran éteint.
        subprocess.Popen(
            ['powershell', '-Command',
             '(Add-Type -MemberDefinition "[DllImport(\\"user32.dll\\")]'
             'public static extern int SendMessage(int hWnd,int hMsg,int wParam,int lParam);"'
             ' -Name U32 -PassThru)::SendMessage(-1,0x0112,0xF170,2)'],
            shell=True
        )

    #MAKING (Fusion 360)

    def _undo(self): pyautogui.hotkey('ctrl', 'z')
    def _redo(self) : pyautogui.hotkey('ctrl', 'y')
    def _save(self) : pyautogui.hotkey('ctrl', 's')
    def _view_home(self) : pyautogui.press('h')
    def _section_view(self) : pyautogui.hotkey('shift', 's')
    def _new_component(self): pyautogui.hotkey('ctrl', 'n')
    def _export_stl(self) : pyautogui.hotkey('ctrl', 'shift', 'e')

    # --- FOCUS

    def _pomo_toggle(self): self._pomodoro.toggle()
    def _pomo_reset(self) : self._pomodoro.reset()
    def _snap_left(self) : pyautogui.hotkey('win', 'left')
    def _snap_right(self): pyautogui.hotkey('win', 'right')
    def _next_vdesktop(self) : pyautogui.hotkey('ctrl', 'win', 'right')

    def _open_notion(self):
        subprocess.Popen(['start', '', 'notion://'], shell=True)

    def _dnd_toggle(self):
        pyautogui.hotkey('win', 'a')
        time.sleep(0.3)
        pyautogui.hotkey('win', 'a')
        self.dnd_toggled_at = time.monotonic()

    #GAME

    def _game_mic(self) : self._audio.toggle_mic_mute()
    def _discord_mute(self) : pyautogui.hotkey('ctrl', 'shift', 'm')
    def _game_screenshot(self) : pyautogui.press('f12')          # overlay Steam
    def _clip_30s(self) : pyautogui.hotkey('win', 'alt', 'g')  # Xbox Game Bar
    def _alt_tab(self)  : pyautogui.hotkey('alt', 'tab')
    def _task_manager(self): pyautogui.hotkey('ctrl', 'shift', 'esc')

    def _obs_toggle(self):
        subprocess.Popen(['start', '', 'obs://'], shell=True)
        self.obs_toggled_at = time.monotonic()

    # --- Potentiomètres

    def _pot_vol_master(self, v: int) : self._audio.set_master_volume(v)
    def _pot_vol_music(self, v: int)   : self._audio.set_spotify_volume(v)
    def _pot_vol_game(self, v: int)  : self._audio.set_game_volume(v)
    def _pot_vol_discord(self, v: int) : self._audio.set_discord_volume(v)
    def _pot_mic_gain(self, v: int)  : self._audio.set_mic_gain(v)

    def _pot_brightness(self, v: int):
        try:
            sbc.set_brightness(v)
        except Exception as e:
            log.warning(f"Luminosité : {e}")

    def _pot_zoom(self, v: int):
        # Ctrl+= / Ctrl+- simulés ; le sleep laisse Fusion encaisser chaque frappe.
        steps = int((v - 50) / 10)
        if steps > 0:
            for _ in range(steps):
                pyautogui.hotkey('ctrl', '=')
                time.sleep(0.05)
        elif steps < 0:
            for _ in range(-steps):
                pyautogui.hotkey('ctrl', '-')
                time.sleep(0.05)

    # TODO: brancher sur l'app CAO active
    def _pot_opacity(self, v: int) : pass
    def _pot_rotation(self, v: int) : pass
    # TODO: brancher sur le générateur de bruit blanc
    def _pot_white_noise(self, v: int) : pass

    def _pot_pomo_duration(self, v: int):
        minutes = 5 + int(v * 55 / 100)
        self._pomodoro.set_duration(minutes)

    # Tables de dispatch

    _ACTION_MAP = {
        "MEDIA_PLAY" : _media_play,
        "MEDIA_NEXT" : _media_next,
        "MEDIA_PREV" : _media_prev,
        "MIC_TOGGLE"   : _mic_toggle,
        "SCREENSHOT" : _screenshot,
        "OPEN_EXPLORER" : _open_explorer,
        "SLEEP_SCREENS" : _sleep_screens,

        "UNDO"  : _undo,
        "REDO" : _redo,
        "SAVE" : _save,
        "VIEW_HOME" : _view_home,
        "SECTION_VIEW" : _section_view,
        "NEW_COMPONENT" : _new_component,
        "EXPORT_STL"  : _export_stl,

        "POMO_TOGGLE": _pomo_toggle,
        "POMO_RESET" : _pomo_reset,
        "OPEN_NOTION": _open_notion,
        "DND_TOGGLE"  : _dnd_toggle,
        "SNAP_LEFT" : _snap_left,
        "SNAP_RIGHT" : _snap_right,
        "NEXT_VDESKTOP" : _next_vdesktop,

        "GAME_MIC" : _game_mic,
        "DISCORD_MUTE" : _discord_mute,
        "GAME_SCREENSHOT" : _game_screenshot,
        "CLIP_30S"  : _clip_30s,
        "OBS_TOGGLE"  : _obs_toggle,
        "ALT_TAB"   : _alt_tab,
        "TASK_MANAGER" : _task_manager,
    }

    _POT_MAP = {
        "VOL_MASTER"  : _pot_vol_master,
        "VOL_MUSIC"  : _pot_vol_music,
        "VOL_GAME"   : _pot_vol_game,
        "VOL_DISCORD": _pot_vol_discord,
        "BRIGHTNESS" : _pot_brightness,
        "MIC_GAIN"  : _pot_mic_gain,
        "ZOOM" : _pot_zoom,
        "OPACITY"  : _pot_opacity,
        "ROTATION"  : _pot_rotation,
        "WHITE_NOISE"  : _pot_white_noise,
        "POMO_DURATION" : _pot_pomo_duration,
    }
