# TODO: no VLC HTTP command exists for frame-stepping on HTTP
# make_key_action('e') instead of trying to do this through jog/shuttle.

from .keyboard_actions import make_key_action
from .mpv_control import send_mpv_command, mpv_seek_scrub_knob, toggle_or_launch_mpv, save_and_quit_mpv
from .vlc_control import (
    VIDEO_VLC,
    video_toggle_and_raise,
    vlc_absolute_seek_knob,
    vlc_jog_knob,
    save_and_quit_vlc,
)
from .system_actions import make_monitor_toggle_action, toggle_mute, restart_obs, volume_knob
from .pad_lights import animation_chase, animation_bounce, animation_alternate, animation_strobe, stop_animation
from .modes import mode_dial_knob

PAD_PRESS_BY_MODE = {
    1: {  # VLC video
        36: video_toggle_and_raise,
        37: lambda: VIDEO_VLC.rc_send("seek -4"),  # short jump back
        38: make_key_action('v'),                    # cycle subtitle track
        39: make_key_action('b'),                     # cycle audio track
        40: save_and_quit_vlc,
    },
    2: {  # MPV
        37: toggle_or_launch_mpv,
        38: send_mpv_command(["playlist-next"]),
        41: save_and_quit_mpv,
        # P3/P4 left blank per spec
    },
    3: {},  # Karaoke (Ultrastar Deluxe) — placeholder
    4: {
        36: animation_chase,
        37: animation_bounce,
        38: animation_alternate,
        39: animation_strobe,
        40: stop_animation,  
    },
}

PAD_PRESS_FIXED = {}

PAD_RELEASE = {}

_monitor_toggle_action = make_monitor_toggle_action()

PAD_PROGRAM_PRESS = {
    0: _monitor_toggle_action,
    1: toggle_mute,
    2: restart_obs,
    3: _monitor_toggle_action,
}

CC_HANDLERS = {
    1: mode_dial_knob,
    3: vlc_absolute_seek_knob,
    4: vlc_jog_knob,
    5: mpv_seek_scrub_knob,
    8: volume_knob,
}