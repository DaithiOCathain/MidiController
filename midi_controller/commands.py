import os
import socket
import threading

from .pad_lights import animation_binary_grid, stop_animation
from .vlc_control import video_toggle_and_raise
from .mpv_control import toggle_or_launch_mpv

SOCKET_PATH = os.path.join(os.environ.get("XDG_RUNTIME_DIR", "/tmp"), "lpd8-mapper.sock")

COMMANDS = {
    "binary_clock": animation_binary_grid,
    "stop_lights": stop_animation,
    "video_toggle": video_toggle_and_raise,
    "music_toggle": toggle_or_launch_mpv,
}


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