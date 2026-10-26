"""Safe defaults. Put your own values in config_local.py (gitignored).

Every UPPERCASE name in config_local.py overrides the default here.
Dict-valued settings are merged, so overriding one key is enough:

    VIDEO_VLC_CONFIG = {"http_password": "something-better"}
"""
import importlib
from pathlib import Path

HOME = Path.home()


def _overlay():
    """Apply config_local.py on top of this module, if it exists."""
    try:
        local = importlib.import_module(f"{__package__}.config_local")
    except ModuleNotFoundError as e:
        if e.name != f"{__package__}.config_local":
            raise  # config_local exists but is itself broken: don't hide that
        return
    for key, value in vars(local).items():
        if not key.isupper():
            continue
        current = globals().get(key)
        if isinstance(current, dict) and isinstance(value, dict):
            current.update(value)
        else:
            globals()[key] = value


# --- machine-specific: override these in config_local.py -------------------
MEDIA_OUTPUT = ""          # xrandr / KWin output name, e.g. "HDMI-A-1"
DESK_SERIALS = []          # monitor serials for ddcutil (see `ddcutil detect`)

MPV_SOCKET_PATH = "/tmp/mpvsocket"
MPV_PLAYLIST = str(HOME / "Documents" / "audio.m3u")
SOCKETS_FILE = str(HOME / ".config" / "lpd8-mapper" / "sockets.json")

SCREENSHOT_PATH = str(HOME / "screenshot.png")
OBS_RESTART_SCRIPT = str(HOME / ".local" / "bin" / "restart-obs.sh")

RESUME_FILE = str(HOME / ".vlc_resume.json")
SOUND_DIR = str(HOME / "Sounds")

ULTRASTAR_CMD = ["ultrastardx"]  # flatpak: ["flatpak", "run", "eu.usdx.UltraStarDeluxe"]

_overlay()  # first pass: scalars, so the derived values below pick them up

# --- derived ----------------------------------------------------------------
MEDIA_RULES = {"mpv": MEDIA_OUTPUT, "vlc": MEDIA_OUTPUT, "ultrastar": MEDIA_OUTPUT}

VIDEO_VLC_CONFIG = {
    "name": "video",
    "host": "127.0.0.1",
    "http_port": 8081,
    "http_password": "change-me",
    "playlist": str(HOME / "Documents" / "video.m3u"),
    "resume_file": RESUME_FILE,
    "extra_args": ["--fullscreen", "--no-spu", "--avcodec-hw=none"],
}

_overlay()  # second pass: merges dict overrides into the derived values
