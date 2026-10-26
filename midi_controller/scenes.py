import subprocess
import threading
from concurrent.futures import ThreadPoolExecutor

from .config import ALERT_BULBS, SOUND_DIR
from .smarthome import PRESET_EVENING, SOCKETS, KasaBulb

UNIT = 0.3  # seconds per Morse unit; bulb LAN latency sets the floor
ALERT_SOUND = f"{SOUND_DIR}/red_alert.mpga"

_pool = ThreadPoolExecutor(max_workers=8)
_stop = None
_sound = None


def _color_bulbs():
    return [b for b in SOCKETS.values()
            if isinstance(b, KasaBulb) and b.name in ALERT_BULBS]

def _set_red(bulb):
    bulb.set_hue(0)
    bulb.set_saturation(100)

def _set_power(bulb, on):
    bulb.set(on)

def _restore():
    PRESET_EVENING()


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