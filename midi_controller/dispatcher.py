import sys
import time

import mido

from .mappings import (
    CC_HANDLERS_BY_MODE,
    CC_HANDLERS_GLOBAL,
    PAD_PRESS_BY_MODE,
    PAD_PRESS_FIXED,
    PAD_PROGRAM_PRESS,
    PAD_RELEASE,
)
from .modes import (
    MODE_NOTES,
    apply_mode_leds,
    get_current_mode,
    set_mode,
)
from .pad_lights import reset_outport

MODE_PROGRAMS = {4: 1, 5: 2, 6: 3, 7: 4}


def find_port():
    for name in mido.get_input_names():
        if "LPD8" in name:
            return name
    raise RuntimeError("LPD8 not found — is it connected?")


def handle_message(msg):
    if msg.type == "note_on":
        if msg.velocity == 0:
            action = PAD_RELEASE.get(msg.note)
            if action:
                action()
            return

        apply_mode_leds()

        action = PAD_PRESS_BY_MODE.get(get_current_mode(), {}).get(msg.note) or PAD_PRESS_FIXED.get(msg.note)
        if action:
            print(f"PAD PRESS: note={msg.note}, velocity={msg.velocity}, mode={get_current_mode()}")
            action()

    elif msg.type == "note_off":
        action = PAD_RELEASE.get(msg.note)
        if action:
            action()
        if msg.note in MODE_NOTES.values():
            apply_mode_leds()

    elif msg.type == "control_change":
        handler = CC_HANDLERS_GLOBAL.get(msg.control)
        if handler is None:
            handler = CC_HANDLERS_BY_MODE.get(get_current_mode(), {}).get(msg.control)
        print(f"CC: control={msg.control}, value={msg.value}, mode={get_current_mode()}, handler={handler}")
        if handler:
            handler(msg.value)

    elif msg.type == "program_change":
        print(f"PROGRAM CHANGE: program={msg.program}")

        if msg.program in MODE_PROGRAMS:
            set_mode(MODE_PROGRAMS[msg.program])
            return

        action = PAD_PROGRAM_PRESS.get(msg.program)
        if action:
            action()


def main():
    try:
        while True:
            try:
                port_name = find_port()
            except RuntimeError:
                time.sleep(2)
                continue

            reset_outport()
            with mido.open_input(port_name, callback=handle_message):
                print(f"Listening on {port_name} — Ctrl+C to stop")
                set_mode(get_current_mode())
                while port_name in mido.get_input_names():
                    time.sleep(2)
            print("LPD8 disconnected, waiting for it to return")
    except KeyboardInterrupt:
        sys.exit(0)