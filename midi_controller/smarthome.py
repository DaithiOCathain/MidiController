import asyncio
import json
import threading

import tinytuya

from .config import SOCKETS_FILE

SOCKETS = {}

class KasaBulb:
    def __init__(self, name, ip):
        self.name = name
        self.ip = ip
        self._hs = [0, 100]
        self._lock = threading.Lock()
        self._pending = {}
        self._running = False

    def _submit(self, key, value):
        with self._lock:
            self._pending[key] = value
            if self._running:
                return
            self._running = True
        threading.Thread(target=self._worker, daemon=True).start()

    def _worker(self):
        try:
            asyncio.run(self._drain())
        except Exception as e:  # noqa: BLE001
            print(f"Bulb [{self.name}]: failed: {e!r}")
            with self._lock:
                self._pending.clear()
                self._running = False

    async def _drain(self):
        from kasa import Discover

        dev = await Discover.discover_single(self.ip)
        try:
            while True:
                with self._lock:
                    if not self._pending:
                        self._running = False
                        return
                    key = next(iter(self._pending))
                    value = self._pending.pop(key)
                await dev.update()
                await self._apply(dev, key, value)
        finally:
            await dev.disconnect()

    async def _apply(self, dev, key, value):
        from kasa import Module

        if key == "power":
            target = (not dev.is_on) if value is None else value
            if dev.is_on != target:
                await (dev.turn_on() if target else dev.turn_off())
            print(f"Bulb [{self.name}]: {'on' if target else 'off'}")
            return

        light = dev.modules.get(Module.Light)
        if light is None:
            return
        if key == "brightness" and light.is_dimmable:
            await light.set_brightness(value)
        elif key == "color_temp" and light.is_variable_color_temp:
            await light.set_color_temp(value)
        elif key == "hsv" and light.is_color:
            await light.set_hsv(*value)

    def toggle(self):
        self._submit("power", None)

    def set(self, on):
        self._submit("power", on)

    def set_brightness(self, pct):
        self._submit("brightness", pct)

    def set_color_temp(self, kelvin):
        self._submit("color_temp", kelvin)

    def set_hue(self, degrees):
        self._hs[0] = degrees
        self._submit("hsv", tuple(self._hs))

    def set_saturation(self, pct):
        self._hs[1] = pct
        self._submit("hsv", tuple(self._hs))

    def apply(self, power, brightness=None, kelvin=None):
        self._submit("power", power)
        if brightness is not None:
            self._submit("brightness", brightness)
        if kelvin is not None:
            self._submit("color_temp", kelvin)

class TuyaSocket:
    def __init__(self, name, dev_id, key, ip, version, dps="1"):
        self.name = name
        self.dev_id = dev_id
        self.key = key
        self.ip = ip
        self.version = float(version)
        self.dps = str(dps)
        self._busy = threading.Lock()

    def _device(self):
        return tinytuya.OutletDevice(
            self.dev_id,
            self.ip,
            self.key,
            version=self.version,
            connection_timeout=3,
            connection_retry_limit=1,
        )

    def _run(self, action):
        if not self._busy.acquire(blocking=False):
            print(f"Socket [{self.name}]: busy, ignored")
            return

        def worker():
            try:
                result = action(self._device())
                if "Unreachable" in result or "failed" in result:
                    print(f"Socket [{self.name}]: {result}, retrying once")
                    result = action(self._device())
                print(f"Socket [{self.name}]: {result}")
            except Exception as e:  # noqa: BLE001 - worker thread must log, not die silently
                print(f"Socket [{self.name}]: failed: {e!r}")
            finally:
                self._busy.release()

        threading.Thread(target=worker, daemon=True).start()

    def toggle(self):
        def action(d):
            status = d.status()
            state = (status or {}).get("dps", {}).get(self.dps)
            if state is None:
                return f"status read failed: {status!r}"
            d.set_status(not state, switch=int(self.dps))
            return f"{'on' if state else 'off'} -> {'off' if state else 'on'}"

        self._run(action)

    def set(self, on):
        def action(d):
            status = d.status()
            state = (status or {}).get("dps", {}).get(self.dps)
            if state is None:
                return f"status read failed: {status!r}"
            if state == on:
                return f"already {'on' if on else 'off'}"
            result = d.set_status(on, switch=int(self.dps))
            if result and "Error" in result:
                return f"set failed: {result!r}"
            return f"set {'on' if on else 'off'}"

        self._run(action)


def load_sockets():
    try:
        with open(SOCKETS_FILE) as f:
            entries = json.load(f)
    except (OSError, json.JSONDecodeError) as e:
        print(f"Smarthome: couldn't load {SOCKETS_FILE}: {e!r}")
        return []

    sockets = []
    for entry in entries:
        try:
            if entry.get("type") == "kasa":
                sockets.append(KasaBulb(entry["name"], entry["ip"]))
            else:
                sockets.append(TuyaSocket(
                    entry["name"], entry["id"], entry["key"], entry["ip"],
                    entry.get("version", 3.3), entry.get("dps", "1"),
                ))
        except KeyError as err:
            print(f"Smarthome: entry {entry.get('name', '?')} missing {err}")
    return sockets


def init_sockets():
    if not SOCKETS:
        for s in load_sockets():
            SOCKETS[s.name] = s
    return SOCKETS


def all_off():
    for s in SOCKETS.values():
        s.set(False)

def all_on():
    for s in SOCKETS.values():
        s.set(True)


def build_smarthome_mode():
    notes = [36, 37, 38, 39, 40, 41, 42, 43]
    return {note: s.toggle for note, s in zip(notes, init_sockets().values(), strict=False)}

def bulb_knob(attr, scale):
    def handler(value):
        for bulb in SOCKETS.values():
            if isinstance(bulb, KasaBulb):
                getattr(bulb, attr)(scale(value))
    return handler


def brightness_scale(v):
    return max(1, round(v / 127 * 100))


def color_temp_scale(v):
    return round(2500 + v / 127 * (9000 - 2500))


def hue_scale(v):
    return min(359, round(v / 127 * 360))

def saturation_scale(v):
    return round(v / 127 * 100)


def bulb_preset(power, brightness=None, kelvin=None):
    def action():
        for bulb in SOCKETS.values():
            if isinstance(bulb, KasaBulb):
                bulb.apply(power, brightness, kelvin)
    return action


PRESET_WORK = bulb_preset(True, 100, 4000)
PRESET_EVENING = bulb_preset(True, 30, 2700)
PRESET_OFF = bulb_preset(False)