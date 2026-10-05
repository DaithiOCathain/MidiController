# NOTE: frame-stepping via HTTP is currently broken — VLC's HTTP API has
# no frame-step command. This zone silently no-ops until fixed (see TODO
# in mappings.py for the planned keyboard-simulation approach).

import base64
import json
import os
import subprocess
import threading
import time
import urllib.parse
import urllib.request

from .config import VIDEO_VLC_CONFIG
from .keyboard_actions import make_key_action
from .screens import resolve_screen_number


class VLCInstance:
    def __init__(self, name, host, playlist, resume_file, http_port, http_password, target_screen=None, extra_args=None):
        self.name = name
        self.host = host
        self.http_port = http_port
        self.http_password = http_password
        self.playlist = playlist
        self.resume_file = resume_file
        self.target_screen = target_screen
        self.extra_args = extra_args or []
        self.process = None
        self.launching = False


    def _auth_header(self):
        auth = base64.b64encode(f":{self.http_password}".encode()).decode()
        return {"Authorization": f"Basic {auth}"}

    def http_command(self, command=None, **params):
        query = dict(params)
        if command is not None:
            query["command"] = command
        url = f"http://{self.host}:{self.http_port}/requests/status.json"
        if query:
            url += "?" + urllib.parse.urlencode(query)

        req = urllib.request.Request(url, headers=self._auth_header())
        try:
            with urllib.request.urlopen(req, timeout=2) as resp:
                return json.loads(resp.read().decode())
        except Exception:
            return None

    def is_running(self):
        return self.http_command() is not None

    def start_playlist_export_timer(self, interval=600):
        def loop():
            while True:
                time.sleep(interval)
                self.export_playlist()

        threading.Thread(target=loop, daemon=True).start()

    def raise_window(self):
        if self.process is not None:
            try:
                subprocess.Popen(
                    ["xdotool", "search", "--pid", str(self.process.pid), "windowactivate"]
                )
            except FileNotFoundError:
                print(f"VLC [{self.name}]: xdotool not found, skipping window raise")

    def launch_or_toggle(self):
        if self.is_running():
            self.http_command("pl_pause")
            print(f"VLC [{self.name}]: toggled play/pause")
            return

        if self.launching:
            print(f"VLC [{self.name}]: launch already in progress")
            return

        self.launching = True
        print(f"VLC [{self.name}]: launching")

        resume_id = None
        resume_time = None

        if os.path.exists(self.resume_file):
            try:
                with open(self.resume_file) as f:
                    all_state = json.load(f)
                entry = all_state.get(self.name)
                if entry:
                    resume_time = entry.get("time")
                    resume_id = entry.get("id")
            except (OSError, json.JSONDecodeError):
                pass

        screen_args = []
        if self.target_screen:
            screen_num = resolve_screen_number(self.target_screen)
            if screen_num is not None:
                screen_args = [f"--qt-fullscreen-screennumber={screen_num}"]
            else:
                print(f"VLC [{self.name}]: couldn't resolve screen '{self.target_screen}', using default")

        args = [
            "vlc",
            "--extraintf=http",
            f"--http-host={self.host}",
            f"--http-port={self.http_port}",
            f"--http-password={self.http_password}",
            "--no-random",
            *screen_args,
            *self.extra_args,
            self.playlist,
        ]

        try:
            self.process = subprocess.Popen(args)
        except Exception:
            self.launching = False
            raise

        self.start_playlist_export_timer()

        def wait_for_ready():
            for _ in range(20):
                if self.is_running():
                    self.launching = False
                    if resume_id and resume_time:
                        self.http_command("pl_play", id=resume_id)
                        time.sleep(0.3)
                        self.http_command("seek", val=resume_time)
                    return
                time.sleep(0.5)
            self.launching = False

        threading.Thread(target=wait_for_ready, daemon=True).start()

    def save_and_quit(self):
        status = self.http_command()

        if status is not None:
            current_time = status.get("time")
            current_id = status.get("currentplid")

            if current_time is not None and current_id is not None and current_id != -1:
                all_state = {}
                if os.path.exists(self.resume_file):
                    try:
                        with open(self.resume_file) as f:
                            all_state = json.load(f)
                    except (OSError, json.JSONDecodeError):
                        all_state = {}

                all_state[self.name] = {
                    "time": current_time,
                    "id": current_id,
                }

                with open(self.resume_file, "w") as f:
                    json.dump(all_state, f)

                print(f"VLC [{self.name}]: saved resume state -> {self.resume_file}")
            else:
                print(f"VLC [{self.name}]: no time/id captured, resume not saved (time={current_time}, id={current_id})")
        else:
            print(f"VLC [{self.name}]: status fetch failed, resume not saved")

        self.export_playlist()

        if self.process is not None:
            self.process.terminate()
            try:
                self.process.wait(timeout=3)
            except subprocess.TimeoutExpired:
                print(f"VLC [{self.name}]: terminate timed out, killing")
                self.process.kill()
                self.process.wait()
            self.process = None
        else:
            print(f"VLC [{self.name}]: no tracked PID — kill manually")

    def export_playlist(self):
        url = f"http://{self.host}:{self.http_port}/requests/playlist.json"
        req = urllib.request.Request(url, headers=self._auth_header())

        try:
            with urllib.request.urlopen(req, timeout=3) as resp:
                data = json.loads(resp.read().decode())
        except Exception as e:
            print(f"VLC [{self.name}]: playlist export failed: {e!r}")
            return

        entries = []

        def walk(node):
            for child in node.get("children", []):
                if "uri" in child:
                    uri = child["uri"]
                    if uri.startswith("file://"):
                        path = urllib.parse.unquote(uri[len("file://"):])
                        name = child.get("name", os.path.basename(path))
                        entries.append((name, path))
                walk(child)

        walk(data)

        if entries:
            with open(self.playlist, "w") as f:
                f.write("#EXTM3U\n")
                for name, path in entries:
                    f.write(f"#EXTINF:-1,{name}\n")
                    f.write(f"{path}\n")
            print(f"VLC [{self.name}]: exported {len(entries)} items -> {self.playlist}")
        else:
            print(f"VLC [{self.name}]: export produced no items, not overwriting")


_vlc_save_lock = threading.Lock()


def save_and_quit_vlc():
    if not _vlc_save_lock.acquire(blocking=False):
        print("VLC: save/quit already in progress")
        return

    def worker():
        try:
            VIDEO_VLC.save_and_quit()
        finally:
            _vlc_save_lock.release()

    threading.Thread(target=worker, daemon=True).start()


VIDEO_VLC = VLCInstance(**VIDEO_VLC_CONFIG)


def video_toggle_and_raise():
    VIDEO_VLC.launch_or_toggle()
    VIDEO_VLC.raise_window()


def vlc_absolute_seek_knob(value):
    pct = round(value / 127 * 100)
    VIDEO_VLC.http_command("seek", val=f"{pct}%")
    print(f"VLC video seek: {pct}%")


def vlc_seek_relative(seconds):
    VIDEO_VLC.http_command("seek", val=f"{seconds:+d}")


_vlc_jog_state = {"zone": None, "value": None, "stop_event": None, "thread": None}


def _vlc_jog_classify(value):
    if value <= 15:
        return "ff_rewind"
    elif value <= 31:
        return "fast_rewind"
    elif value <= 47:
        return "slow_rewind"
    elif value <= 79:
        return "normal"
    elif value <= 95:
        return "step_forward"
    elif value <= 111:
        return "fast_forward"
    else:
        return "ff_forward"


def _vlc_jog_stop_repeat():
    if _vlc_jog_state["stop_event"] is not None:
        _vlc_jog_state["stop_event"].set()
    _vlc_jog_state["stop_event"] = None
    _vlc_jog_state["thread"] = None


def stop_video_jog():
    _vlc_jog_stop_repeat()


def _vlc_jog_start_repeat(command, interval, **params):
    stop_event = threading.Event()

    def loop():
        while not stop_event.wait(interval):
            VIDEO_VLC.http_command(command, **params)

    t = threading.Thread(target=loop, daemon=True)
    _vlc_jog_state["stop_event"] = stop_event
    _vlc_jog_state["thread"] = t
    t.start()

def _vlc_jog_start_repeat_fn(fn, interval):
    stop_event = threading.Event()

    def loop():
        while not stop_event.wait(interval):
            fn()

    t = threading.Thread(target=loop, daemon=True)
    _vlc_jog_state["stop_event"] = stop_event
    _vlc_jog_state["thread"] = t
    t.start()

_frame_next = make_key_action('e')

def vlc_volume_knob(value):
    vlc_vol = round(value / 127 * 256)
    VIDEO_VLC.http_command("volume", val=vlc_vol)
    print(f"VLC volume: {vlc_vol}/256")

def vlc_jog_knob(value):
    zone = _vlc_jog_classify(value)

    if 80 <= value <= 85:
        previous = _vlc_jog_state["value"]
        _vlc_jog_stop_repeat()
        if previous is not None and 80 <= previous <= 85:
            if value > previous:
                _frame_next()
        _vlc_jog_state["zone"] = zone
        _vlc_jog_state["value"] = value
        return

    if zone == _vlc_jog_state["zone"]:
        if zone == "step_forward":
            _vlc_jog_stop_repeat()
            interval = 0.25 - ((value - 86) / 9.0) * 0.20
            _vlc_jog_start_repeat_fn(_frame_next, interval)
        _vlc_jog_state["value"] = value
        return

    _vlc_jog_stop_repeat()
    _vlc_jog_state["zone"] = zone
    _vlc_jog_state["value"] = value
    print(f"VLC video jog: {zone}")

    match zone:
        case "ff_rewind":
            _vlc_jog_start_repeat("seek", 0.3, val="-10")
        case "fast_rewind":
            _vlc_jog_start_repeat("seek", 0.3, val="-3")
        case "slow_rewind":
            _vlc_jog_start_repeat("seek", 0.4, val="-1")
        case "normal":
            VIDEO_VLC.http_command("rate", val=1)
            VIDEO_VLC.http_command("pl_play")
        case "step_forward":
            interval = 0.25 - ((value - 86) / 9.0) * 0.20
            _vlc_jog_start_repeat_fn(_frame_next, interval)
        case "fast_forward":
            VIDEO_VLC.http_command("rate", val=2)
            VIDEO_VLC.http_command("pl_play")
        case "ff_forward":
            VIDEO_VLC.http_command("rate", val=4)
            VIDEO_VLC.http_command("pl_play")