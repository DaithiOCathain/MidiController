import os
import json
import socket
import subprocess
import threading

from .config import MPV_SOCKET_PATH, MPV_PLAYLIST
from .scrub import scrub_delta, scrub_seconds

from .config import RESUME_FILE
from .screens import resolve_screen_number
from .config import MPV_SOCKET_PATH, MPV_PLAYLIST, MPV_TARGET_SCREEN


def send_mpv_command(command):
    def action():
        try:
            with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as s:
                s.settimeout(0.5)
                s.connect(MPV_SOCKET_PATH)
                s.sendall(json.dumps({"command": command}).encode() + b"\n")
        except (FileNotFoundError, ConnectionRefusedError):
            pass
    return action

def mpv_get_property(prop):
    try:
        with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as s:
            s.settimeout(1.0)
            s.connect(MPV_SOCKET_PATH)
            s.sendall(
                json.dumps({"command": ["get_property", prop], "request_id": 1}).encode() + b"\n"
            )

            buffer = ""
            while True:
                chunk = s.recv(4096).decode()
                if not chunk:
                    break
                buffer += chunk
                for line in buffer.splitlines():
                    try:
                        msg = json.loads(line)
                    except json.JSONDecodeError:
                        continue
                    if msg.get("request_id") == 1:
                        return msg.get("data")
    except (FileNotFoundError, ConnectionRefusedError, socket.timeout, OSError):
        return None

def toggle_or_launch_mpv():
    try:
        with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as s:
            s.connect(MPV_SOCKET_PATH)
            s.sendall(json.dumps({"command": ["cycle", "pause"]}).encode() + b"\n")
    except (FileNotFoundError, ConnectionRefusedError):
        screen_args = []
        screen_num = MPV_TARGET_SCREEN
        if screen_num is not None:
            screen_args = [f"--screen={screen_num}", f"--fs-screen={screen_num}"]
        else:
            print(f"MPV: couldn't resolve screen '{MPV_TARGET_SCREEN}', using default")

        subprocess.Popen([
            "mpv",
            "--player-operation-mode=pseudo-gui",
            f"--input-ipc-server={MPV_SOCKET_PATH}",
            "--fullscreen",
            *screen_args,
            "--",
            MPV_PLAYLIST,
        ])


def mpv_seek_scrub_knob(value):
    delta, elapsed = scrub_delta(5, value)
    if delta == 0:
        return
    seconds = scrub_seconds(delta, elapsed)
    print(f"MPV seek: {seconds:+.0f}s")
    send_mpv_command(["seek", str(seconds), "relative"])()


def mpv_save_and_quit():
    time_pos = mpv_get_property("time-pos")
    playlist_pos = mpv_get_property("playlist-pos")

    if time_pos is not None and playlist_pos is not None:
        all_state = {}
        if os.path.exists(RESUME_FILE):
            try:
                with open(RESUME_FILE) as f:
                    all_state = json.load(f)
            except (OSError, json.JSONDecodeError):
                all_state = {}

        all_state["mpv"] = {"time": time_pos, "index": playlist_pos}

        with open(RESUME_FILE, "w") as f:
            json.dump(all_state, f)

        print(f"MPV: saved resume state -> {RESUME_FILE}")
    else:
        print(f"MPV: no time/index captured (time={time_pos}, index={playlist_pos})")

    send_mpv_command(["quit"])()


_mpv_save_lock = threading.Lock()

def save_and_quit_mpv():
    if not _mpv_save_lock.acquire(blocking=False):
        print("MPV: save/quit already in progress")
        return

    def worker():
        try:
            mpv_save_and_quit()
        finally:
            _mpv_save_lock.release()

    threading.Thread(target=worker, daemon=True).start()