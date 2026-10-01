from .keyboard_actions import make_key_action
from .mpv_control import send_mpv_command, mpv_seek_scrub_knob, toggle_or_launch_mpv, save_and_quit_mpv
from .vlc_control import (
    VIDEO_VLC,
    video_toggle_and_raise,
    vlc_absolute_seek_knob,
    vlc_seek_relative,
    vlc_jog_knob,
    save_and_quit_vlc,
)
from .system_actions import make_monitor_toggle_action, toggle_mute, restart_obs, volume_knob
from .pad_lights import (
    animation_chase,
    animation_bounce,
    animation_alternate,
    animation_strobe,
    animation_scan,
    animation_ripple,
    animation_checkerboard,
    animation_binary_grid,
    stop_animation,
)
from .modes import mode_dial_knob

PAD_PRESS_BY_MODE = {
    1: {  # VLC video
        36: video_toggle_and_raise,
        37: lambda: vlc_seek_relative(-4),
        38: make_key_action('v'),
        39: make_key_action('b'),
        40: save_and_quit_vlc,
    },
    2: {  # MPV
        37: toggle_or_launch_mpv,
        38: send_mpv_command(["playlist-next"]),
        41: save_and_quit_mpv,
    },
    3: {},  # Karaoke (Ultrastar Deluxe) — placeholder
    4: {  # Pad animations
        36: animation_bounce,
        37: animation_alternate,
        38: animation_strobe,
        39: animation_scan,
        40: animation_ripple,
        41: animation_checkerboard,
        42: animation_binary_grid,
        43: stop_animation,
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