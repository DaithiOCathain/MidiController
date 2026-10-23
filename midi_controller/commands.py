import os
import socket
import threading
from functools import partial

from .mpv_control import send_mpv_command, toggle_or_launch_mpv
from .pad_lights import animation_binary_grid, stop_animation
from .players import (
    MPV_PLAYER,
    VLC_PLAYER,
    activate,
    pause_all,
    resume_current,
    skip,
    skip_back,
    skip_random,
)
from .smarthome import (
    PRESET_EVENING,
    PRESET_OFF,
    PRESET_WORK,
    all_off,
    all_on,
    init_sockets,
)
from .system_actions import (
    desk_monitors_off,
    desk_monitors_on,
    set_volume_percent,
    windows_minimize,
    windows_restore,
    windows_toggle,
)
from .vlc_control import video_toggle_and_raise, vlc_seek_relative

SOCKET_PATH = os.path.join(os.environ.get("XDG_RUNTIME_DIR", "/tmp"), "lpd8-mapper.sock")

COMMANDS = {
    "binary_clock": animation_binary_grid,
    "stop_lights": stop_animation,
    "video_toggle": video_toggle_and_raise,
    "music_toggle": toggle_or_launch_mpv,
    "stories": lambda: activate(VLC_PLAYER),
    "tunes": lambda: activate(MPV_PLAYER)
}
COMMANDS["watch"] = lambda: activate(VLC_PLAYER)
COMMANDS["music"] = lambda: activate(MPV_PLAYER)
COMMANDS["next_track"] = skip
COMMANDS["prev_track"] = skip_back
COMMANDS["random_track"] = skip_random
COMMANDS["desk_monitors_off"] = desk_monitors_off
COMMANDS["desk_monitors_on"] = desk_monitors_on
COMMANDS["play"] = resume_current
COMMANDS["pause"] = pause_all
COMMANDS["music_play"] = lambda: activate(MPV_PLAYER, toggle=False)
COMMANDS["music_pause"] = MPV_PLAYER.pause
COMMANDS["video_play"] = lambda: activate(VLC_PLAYER, toggle=False)
COMMANDS["video_pause"] = VLC_PLAYER.pause
COMMANDS["windows_minimize"] = windows_minimize
COMMANDS["windows_restore"] = windows_restore
COMMANDS["windows_toggle"] = windows_toggle
COMMANDS["lights_work"] = PRESET_WORK
COMMANDS["lights_evening"] = PRESET_EVENING
COMMANDS["lights_off"] = PRESET_OFF

for _pct in range(10, 101, 10):
    COMMANDS[f"volume_{_pct}"] = partial(set_volume_percent, _pct)

for _s in (4, 10, 30, 60):
    COMMANDS[f"video_forward_{_s}"] = partial(vlc_seek_relative, _s)
    COMMANDS[f"video_back_{_s}"] = partial(vlc_seek_relative, -_s)

def _register_sockets():
    for name, sock in init_sockets().items():
        COMMANDS[f"{name}_on"] = lambda s=sock: s.set(True)
        COMMANDS[f"{name}_off"] = lambda s=sock: s.set(False)
        COMMANDS[f"{name}_toggle"] = sock.toggle
    COMMANDS["sockets_all_off"] = all_off
    COMMANDS["sockets_all_on"] = all_on


_register_sockets()


def _flash(name):
    send_mpv_command(["script-message", "flash", name])()


def _handle(conn):
    with conn:
        data = conn.recv(256).decode().strip()
    cmd, _, spoken = data.partition("\t")
    action = COMMANDS.get(cmd)
    if action is None:
        print(f"Command: unknown '{cmd}'")
        return
    print(f"Command: {cmd}")
    _flash(spoken or cmd.replace("_", " "))
    action()


def start_command_server():
    try:
        os.unlink(SOCKET_PATH)
    except FileNotFoundError:
        pass

    server = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    server.bind(SOCKET_PATH)
    os.chmod(SOCKET_PATH, 0o600)
    server.listen(4)

    def loop():
        while True:
            conn, _ = server.accept()
            threading.Thread(target=_handle, args=(conn,), daemon=True).start()

    threading.Thread(target=loop, daemon=True).start()
    print(f"Command socket: {SOCKET_PATH}")
