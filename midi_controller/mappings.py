from .keyboard_actions import make_key_action
from .modes import mode_dial_knob
from .mpv_control import (
    mpv_save_and_quit,
    mpv_seek_scrub_knob,
    mpv_volume_knob,
    send_mpv_command,
    toggle_or_launch_mpv,
)
from .pad_lights import (
    animation_alternate,
    animation_binary_grid,
    animation_bounce,
    animation_checkerboard,
    animation_ripple,
    animation_scan,
    animation_strobe,
    stop_animation,
)
from .soundboard import build_soundboard_mode
from .system_actions import (
    make_monitor_toggle_action,
    restart_obs,
    toggle_mute,
    volume_knob,
)
from .vlc_control import (
    save_and_quit_vlc,
    video_toggle_and_raise,
    vlc_absolute_seek_knob,
    vlc_jog_knob,
    vlc_seek_relative,
    vlc_volume_knob,
)

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
        41: mpv_save_and_quit,
    },
    3: {},  # Karaoke (Ultrastar Deluxe) — placeholder
    5: build_soundboard_mode(),
    8: {  # Pad animations
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


CC_HANDLERS_GLOBAL = {
    5: mode_dial_knob,
    8: volume_knob,
}

CC_HANDLERS_BY_MODE = {
    1: {  # VLC
        3: vlc_absolute_seek_knob,
        4: vlc_jog_knob,
        7: vlc_volume_knob,
    },
    2: {  # MPV
        2: mpv_seek_scrub_knob,
        7: mpv_volume_knob,
    },
    3: {},
    4: {},
    5: {},
    6: {},
    7: {},
    8: {},
}


for _mode, _handlers in CC_HANDLERS_BY_MODE.items():
    _overlap = set(_handlers) & set(CC_HANDLERS_GLOBAL)
    if _overlap:
        raise ValueError(f"Mode {_mode} defines global CC(s) {_overlap} — remove from per-mode dict")