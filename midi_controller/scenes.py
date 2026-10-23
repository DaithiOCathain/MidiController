import subprocess
import threading
from concurrent.futures import ThreadPoolExecutor

from .config import SOUND_DIR

UNIT = 0.3  # seconds per Morse unit; bulb LAN latency sets the floor
ALERT_SOUND = f"{SOUND_DIR}/red_alert.mp3"

_pool = ThreadPoolExecutor(max_workers=8)
_stop = None
_sound = None


# --- ADAPT: wire these to your KasaBulb class -------------------------
def _color_bulbs():
    """Return only bulbs that can do colour (KL130B yes; KL110B probably not)."""
    return []

def _set_red(bulb):
    pass  # e.g. bulb.set_hsv(0, 100, 100)

def _set_power(bulb, on):
    pass  # fast on/off; or toggle brightness 100 <-> 1 if power is too slow

def _restore():
    pass  # e.g. call your lights_evening preset, or re-apply a saved snapshot
# ----------------------------------------------------------------------


def _sos():
    letters = ("...", "---", "...")
    while True:
        for li, letter in enumerate(letters):
            for ei, el in enumerate(letter):
                yield True, UNIT if el == "." else 3 * UNIT
                if ei < len(letter) - 1:
                    yield False, UNIT
                else:
                    yield False, 3 * UNIT if li < len(letters) - 1 else 7 * UNIT


def red_alert():
    global _stop, _sound
    red_alert_off()
    stop = threading.Event()
    _stop = stop
    _sound = subprocess.Popen(
        ["ffplay", "-nodisp", "-loop", "0", "-loglevel", "quiet", ALERT_SOUND]
    )

    def run():
        try:
            bulbs = _color_bulbs()
            for b in bulbs:
                _set_red(b)
            for on, secs in _sos():
                for b in bulbs:
                    _pool.submit(_set_power, b, on)
                if stop.wait(secs):
                    break
        except Exception as e:  # noqa: BLE001
            print(f"red_alert: failed: {e!r}")
        finally:
            _restore()

    threading.Thread(target=run, daemon=True).start()


def red_alert_off():
    global _stop, _sound
    if _stop is not None:
        _stop.set()
        _stop = None
    if _sound is not None:
        _sound.terminate()
        _sound = None