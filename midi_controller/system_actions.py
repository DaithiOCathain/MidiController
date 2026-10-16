import subprocess

from .config import DESK_MONITORS, OBS_RESTART_SCRIPT, SCREENSHOT_PATH


def make_screenshot_action():
    def action():
        subprocess.Popen(["spectacle", "-b", "-o", SCREENSHOT_PATH, "-m", "-n"])
    return action


_desk_off = False


def _kscreen(action):
    args = [f"output.{name}.{action}" for name in DESK_MONITORS]
    subprocess.Popen(["kscreen-doctor", *args])


def desk_monitors_off():
    global _desk_off
    print(f"Action: disabling {DESK_MONITORS}")
    _kscreen("disable")
    _desk_off = True


def desk_monitors_on():
    global _desk_off
    print(f"Action: enabling {DESK_MONITORS}")
    _kscreen("enable")
    _desk_off = False


def desk_monitors_toggle():
    if _desk_off:
        desk_monitors_on()
    else:
        desk_monitors_off()


def make_monitor_toggle_action():
    return desk_monitors_toggle


def toggle_mute():
    subprocess.Popen("pactl set-sink-mute @DEFAULT_SINK@ toggle", shell=True)


def restart_obs():
    subprocess.Popen([OBS_RESTART_SCRIPT])


def set_volume_percent(pct):
    subprocess.Popen(["pactl", "set-sink-volume", "@DEFAULT_SINK@", f"{pct}%"])


def volume_knob(value):
    set_volume_percent(round(value / 127 * 100))
