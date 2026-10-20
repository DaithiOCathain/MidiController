import os
import socket
import threading
from functools import partial

from .mpv_control import toggle_or_launch_mpv
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
from .smarthome import all_off, all_on, init_sockets
from .system_actions import (
    desk_monitors_off,
    desk_monitors_on,
    set_volume_percent,
    windows_minimize,
    windows_restore,
    windows_toggle,
)
from .vlc_control import video_toggle_and_raise

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

for _pct in range(10, 101, 10):
    COMMANDS[f"volume_{_pct}"] = partial(set_volume_percent, _pct)


def _register_sockets():
    for name, sock in init_sockets().items():
        COMMANDS[f"{name}_on"] = lambda s=sock: s.set(True)
        COMMANDS[f"{name}_off"] = lambda s=sock: s.set(False)
        COMMANDS[f"{name}_toggle"] = sock.toggle
    COMMANDS["sockets_all_off"] = all_off
    COMMANDS["sockets_all_on"] = all_on


_register_sockets()

def _handle(conn):
    with conn:
        data = conn.recv(256).decode().strip()
    action = COMMANDS.get(data)
    if action is None:
        print(f"Command: unknown '{data}'")
        return
    print(f"Command: {data}")
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
