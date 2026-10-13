import json
import threading

import tinytuya

from .config import SOCKETS_FILE

SOCKETS = {}


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


def build_smarthome_mode():
    notes = [36, 37, 38, 39, 40, 41, 42, 43]
    return {note: s.toggle for note, s in zip(notes, init_sockets().values(), strict=False)}