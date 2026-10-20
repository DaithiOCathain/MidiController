from .keyboard_actions import make_key_action
from .modes import mode_dial_knob
from .mpv_control import (
    mpv_save_and_quit,
    mpv_seek_scrub_knob,
    mpv_volume_knob,
    send_mpv_command,
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
from .players import MPV_PLAYER, VLC_PLAYER, activate
from .smarthome import (
    PRESET_EVENING,
    PRESET_OFF,
    PRESET_WORK,
    brightness_scale,
    build_smarthome_mode,
    bulb_knob,
    color_temp_scale,
    hue_scale,
    saturation_scale,
)
from .soundboard import build_soundboard_mode
from .system_actions import (
    desk_monitors_off,
    desk_monitors_on,
    restart_obs,
    toggle_mute,
    volume_knob,
)
from .vlc_control import (
    save_and_quit_vlc,
    vlc_absolute_seek_knob,
    vlc_jog_knob,
    vlc_seek_relative,
    vlc_volume_knob,
)

PAD_PRESS_BY_MODE = {
    1: {  # VLC video
        36: lambda: activate(VLC_PLAYER),
        37: lambda: vlc_seek_relative(-4),
        38: make_key_action('v'),
        39: make_key_action('b'),
        40: save_and_quit_vlc,
    },
    2: {  # MPV
        37: lambda: activate(MPV_PLAYER),
        38: send_mpv_command(["playlist-next"]),
        41: mpv_save_and_quit,
    },
    3: {},  # Karaoke (Ultrastar Deluxe) — placeholder
    4: {},  # Recording — placeholder
    5: build_soundboard_mode(),    
    7: {
        **build_smarthome_mode(),
        39: PRESET_WORK,
        40: PRESET_EVENING,
        41: PRESET_OFF,
        42: desk_monitors_off,
        43: desk_monitors_on,
    },
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


PAD_PROGRAM_PRESS = {
    0: desk_monitors_off,
    1: toggle_mute,
    2: restart_obs,
    3: desk_monitors_on,
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
    7: {
        1: bulb_knob("set_brightness", brightness_scale),
        2: bulb_knob("set_color_temp", color_temp_scale),
        3: bulb_knob("set_hue", hue_scale),
        4: bulb_knob("set_saturation", saturation_scale),
    },
    8: {},
}


for _mode, _handlers in CC_HANDLERS_BY_MODE.items():
    _overlap = set(_handlers) & set(CC_HANDLERS_GLOBAL)
    if _overlap:
        raise ValueError(f"Mode {_mode} defines global CC(s) {_overlap} — remove from per-mode dict")