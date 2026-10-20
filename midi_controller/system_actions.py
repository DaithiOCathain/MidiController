import shutil
import subprocess

from .config import DESK_SERIALS, OBS_RESTART_SCRIPT, SCREENSHOT_PATH

_QDBUS = shutil.which("qdbus6") or shutil.which("qdbus-qt6") or shutil.which("qdbus")
_windows_hidden = False

def _ddc_power(mode):
    for sn in DESK_SERIALS:
        subprocess.Popen(["ddcutil", "--sn", sn, "--noverify", "setvcp", "d6", mode])


def desk_monitors_off():
    _ddc_power("4")


def desk_monitors_on():
    _ddc_power("1")

def make_screenshot_action():
    def action():
        subprocess.Popen(["spectacle", "-b", "-o", SCREENSHOT_PATH, "-m", "-n"])
    return action

def windows_minimize():
    global _windows_hidden
    if _windows_hidden:
        print("Action: windows already minimised, ignored")
        return
    _kwin_shortcut("MinimizeAll")
    _windows_hidden = True


def windows_restore():
    global _windows_hidden
    _kwin_shortcut("RestoreAll")
    _windows_hidden = False


def windows_toggle():
    if _windows_hidden:
        windows_restore()
    else:
        windows_minimize()


def toggle_mute():
    subprocess.Popen("pactl set-sink-mute @DEFAULT_SINK@ toggle", shell=True)


def restart_obs():
    subprocess.Popen([OBS_RESTART_SCRIPT])


def set_volume_percent(pct):
    subprocess.Popen(["pactl", "set-sink-volume", "@DEFAULT_SINK@", f"{pct}%"])


def volume_knob(value):
    set_volume_percent(round(value / 127 * 100))

def _kwin_shortcut(name):
    if _QDBUS is None:
        print("system_actions: no qdbus binary found")
        return
    subprocess.Popen([_QDBUS, "org.kde.kglobalaccel", "/component/kwin", "invokeShortcut", name])