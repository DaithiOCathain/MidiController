import threading
import time

from .pad_lights import light_pad, stop_animation
from .vlc_control import stop_video_jog
from .scrub import fine_scrub_release

_current_mode = 1
_led_retry_stop = None

MODE_NOTES = {1: 36, 2: 37, 3: 38, 4: 39, 5: 40, 6: 41, 7: 42, 8: 43}


def apply_mode_leds():
    for mode, note in MODE_NOTES.items():
        light_pad(note, on=(mode == _current_mode))


def set_mode(n):
    global _current_mode, _led_retry_stop

    stop_video_jog()
    fine_scrub_release()
    stop_animation()

    _current_mode = n

    if _led_retry_stop is not None:
        _led_retry_stop.set()

    stop_event = threading.Event()
    _led_retry_stop = stop_event

    def retry_leds():
        deadline = time.monotonic() + 4.0
        while time.monotonic() < deadline and not stop_event.is_set():
            apply_mode_leds()
            time.sleep(0.2)

    threading.Thread(target=retry_leds, daemon=True).start()

    print(f"Mode: {n}")


def get_current_mode():
    return _current_mode


_mode_knob_state = {"last_zone": None}
_MODE_KNOB_MARGIN = 3


def _classify_mode_zone(value):
    return min(value // 16 + 1, 8)


def mode_dial_knob(value):
    zone = _classify_mode_zone(value)
    last = _mode_knob_state["last_zone"]

    if last is None:
        _mode_knob_state["last_zone"] = zone
        set_mode(zone)
        return

    if zone == last:
        return

    if abs(zone - last) == 1:
        boundary = max(zone, last) * 16
        if abs(value - boundary) < _MODE_KNOB_MARGIN:
            return  # too close to the boundary — hold previous mode, avoid flicker

    _mode_knob_state["last_zone"] = zone
    set_mode(zone)