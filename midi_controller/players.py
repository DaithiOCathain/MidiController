import random
import subprocess
import threading
import time

from .mpv_control import (
    mpv_get_property,
    mpv_set_property,
    send_mpv_command,
    toggle_or_launch_mpv,
)
from .vlc_control import VIDEO_VLC


from . import kwin


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

    def hide(self):
        windows = _x_windows(self._pid())
        if any(_is_fullscreen(w) for w in windows):
            self.vlc.http_command("fullscreen")
            time.sleep(0.4)
        for w in windows:
            subprocess.Popen(["xdotool", "windowminimize", w])

    def launch(self):
        self.vlc.launch_or_toggle()

    def show(self):
        windows = _x_windows(self._pid(), visible_only=False)
        for w in windows:
            subprocess.Popen(["xdotool", "windowactivate", w])
        time.sleep(0.3)
        if windows and not any(_is_fullscreen(w) for w in windows):
            self.vlc.http_command("fullscreen")
        if self._state() == "paused":
            self.vlc.http_command("pl_pause")

    def toggle_pause(self):
        self.vlc.http_command("pl_pause")
        for w in _x_windows(self._pid(), visible_only=False):
            subprocess.Popen(["xdotool", "windowactivate", w])


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
        _xdotool_pid(mpv_get_property("pid"), "windowminimize")

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

    def show(self):
        _xdotool_pid(mpv_get_property("pid"), "windowactivate")
        mpv_set_property("fullscreen", True)
        mpv_set_property("pause", False)

    def toggle_pause(self):
        send_mpv_command(["cycle", "pause"])()


VLC_PLAYER = VLCPlayer(VIDEO_VLC)
MPV_PLAYER = MPVPlayer()
PLAYERS = [VLC_PLAYER, MPV_PLAYER]

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