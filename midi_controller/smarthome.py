import json
import threading

import tinytuya

from .config import SOCKETS_FILE


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

    def toggle(self):
        if not self._busy.acquire(blocking=False):
            print(f"Socket [{self.name}]: toggle already in progress")
            return

        def worker():
            try:
                d = self._device()
                status = d.status()
                state = (status or {}).get("dps", {}).get(self.dps)
                if state is None:
                    print(f"Socket [{self.name}]: status read failed: {status!r}")
                    return
                result = d.set_status(not state, switch=int(self.dps))
                print(f"Socket [{self.name}]: {'on' if state else 'off'} -> {'off' if state else 'on'} ({result!r})")
            except Exception as e:  # noqa: BLE001 - worker thread must log, not die silently
                print(f"Socket [{self.name}]: toggle failed: {e!r}")
            finally:
                self._busy.release()

        threading.Thread(target=worker, daemon=True).start()


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


def build_smarthome_mode():
    notes = [36, 37, 38, 39, 40, 41, 42, 43]  # P1-P8, in file order
    return {note: s.toggle for note, s in zip(notes, load_sockets())}