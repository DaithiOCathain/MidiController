import json
import random
import subprocess
import threading
import time

from . import kwin
from .config import ULTRASTAR_CMD
from .keyboard_actions import make_named_key_action
from .mpv_control import (
    mpv_get_property,
    mpv_set_property,
    send_mpv_command,
    toggle_or_launch_mpv,
)
from .vlc_control import VIDEO_VLC


class Player:
    def is_running(self):
        raise NotImplementedError

    def pause(self):
        raise NotImplementedError

    def hide(self):
        raise NotImplementedError

    def launch(self):
        raise NotImplementedError

    def show(self):
        raise NotImplementedError

    def toggle_pause(self):
        raise NotImplementedError
    
    def is_playing(self):
        raise NotImplementedError

    def next_track(self):
        raise NotImplementedError

    def prev_track(self):
        raise NotImplementedError

    def random_track(self):
        raise NotImplementedError

    def resume(self):
        raise NotImplementedError

    def make_room(self):
        self.pause()
        self.hide()


class VLCPlayer(Player):
    def __init__(self, vlc):
        self.vlc = vlc

    def _pid(self):
        if self.vlc.process is not None:
            return self.vlc.process.pid
        try:
            out = subprocess.run(
                ["pgrep", "-f", "--", f"--http-port={self.vlc.http_port}"],
                capture_output=True, text=True, check=False,
            ).stdout.split()
        except FileNotFoundError:
            return None
        return int(out[0]) if out else None

    def hide(self):
        kwin.hide("vlc")

    def show(self):
        kwin.show("vlc")
        if self._state() == "paused":
            self.vlc.http_command("pl_pause")

    def toggle_pause(self):
        self.vlc.http_command("pl_pause")
        kwin.show("vlc")

    def is_playing(self):
        return self._state() == "playing"

    def next_track(self):
        self.vlc.http_command("pl_next")

    def prev_track(self):
        self.vlc.http_command("pl_previous")
    
    def is_running(self):
        return self.vlc.is_running()

    def _state(self):
        return (self.vlc.http_command() or {}).get("state")

    def pause(self):
        if self._state() == "playing":
            self.vlc.http_command("pl_pause")
    
    def resume(self):
        state = self._state()
        if state == "paused":
            self.vlc.http_command("pl_pause")
        elif state == "stopped":
            self.vlc.http_command("pl_play")


    def launch(self):
        self.vlc.launch_or_toggle()


class MPVPlayer(Player):
    def is_running(self):
        return mpv_get_property("pause") is not None

    def pause(self):
        mpv_set_property("pause", True)

    def resume(self):
        mpv_set_property("pause", False)

    def next(self):
        mpv_set_property("pause", True)

    def hide(self):
        kwin.hide("mpv")

    def show(self):
        kwin.show("mpv")
        mpv_set_property("fullscreen", True)
        mpv_set_property("pause", False)

    def launch(self):
        toggle_or_launch_mpv()

    def is_playing(self):
        return mpv_get_property("pause") is False

    def next_track(self):
        send_mpv_command(["playlist-next"])()

    def prev_track(self):
        send_mpv_command(["playlist-prev"])()

    def random_track(self):
        count = mpv_get_property("playlist-count")
        current = mpv_get_property("playlist-pos")
        if not count:
            return
        choices = [i for i in range(count) if i != current] or [0]
        send_mpv_command(["playlist-play-index", random.choice(choices)])()


    def toggle_pause(self):
        send_mpv_command(["cycle", "pause"])()



def _usdx_mute(mute):
    try:
        out = subprocess.run(
            ["pactl", "--format=json", "list", "sink-inputs"],
            capture_output=True, text=True, timeout=2, check=False,
        ).stdout
        inputs = json.loads(out)
    except (FileNotFoundError, subprocess.TimeoutExpired, json.JSONDecodeError):
        return
    for si in inputs:
        if "ultrastar" in json.dumps(si.get("properties", {})).lower():
            subprocess.Popen(["pactl", "set-sink-input-mute",
                              str(si["index"]), "1" if mute else "0"])

class UltrastarPlayer(Player):
    """Pause/skip are deliberate no-ops: USDX has no IPC, and a blind
    Space would toggle pause mid-song when it's made to yield."""

    def is_running(self):
        r = subprocess.run(["pgrep", "-f", "ultrastardx"],
                           capture_output=True, check=False)
        return r.returncode == 0

    def launch(self):
        subprocess.Popen(ULTRASTAR_CMD)

    def show(self):
        kwin.show("ultrastar")
        _usdx_mute(False)

    def hide(self):
        kwin.hide("ultrastar")
        _usdx_mute(True)

    def toggle_pause(self):
        kwin.show("ultrastar")
        _usdx_mute(False)
        time.sleep(0.2)
        make_named_key_action("space")()

    def pause(self): pass
    def resume(self): pass
    def is_playing(self): return False
    def next_track(self): pass
    def prev_track(self): pass
    def random_track(self): pass


ULTRASTAR_PLAYER = UltrastarPlayer()
VLC_PLAYER = VLCPlayer(VIDEO_VLC)
MPV_PLAYER = MPVPlayer()
PLAYERS = [VLC_PLAYER, MPV_PLAYER, ULTRASTAR_PLAYER]

_active = None
_lock = threading.Lock()


def activate(player, toggle=True):
    global _active
    if not _lock.acquire(blocking=False):
        print("players: activation in progress, ignored")
        return
    try:
        if _active is player and player.is_running():
            if toggle:
                player.toggle_pause()
            else:
                player.resume()
            return
        for other in PLAYERS:
            if other is not player and other.is_running():
                other.make_room()
        if player.is_running():
            player.show()
        else:
            player.launch()
        _active = player
    finally:
        _lock.release()

def current_player():
    playing = [p for p in PLAYERS if p.is_running() and p.is_playing()]
    if _active in playing:
        return _active
    if playing:
        return playing[0]
    return _active if _active is not None and _active.is_running() else None


def skip():
    player = current_player()
    if player is None:
        print("players: nothing running to skip")
        return
    player.next_track()

def skip_random():
    player = current_player()
    if player is None:
        print("players: nothing running to randomise")
        return
    player.random_track()

def skip_back():
    player = current_player()
    if player is None:
        print("players: nothing running to go back on")
        return
    player.prev_track()

def pause_all():
    for p in PLAYERS:
        if p.is_running():
            p.pause()

def resume_current():
    player = current_player()
    if player is None:
        print("players: nothing to resume")
        return
    player.resume()