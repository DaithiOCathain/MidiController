import sys

import threading
import time

import mido

from .mappings import PAD_PRESS_BY_MODE, PAD_PRESS_FIXED, PAD_RELEASE, PAD_PROGRAM_PRESS, CC_HANDLERS_GLOBAL, CC_HANDLERS_BY_MODE
from .pad_lights import get_outport, light_pad, stop_animation
from .vlc_control import stop_video_jog
from .scrub import fine_scrub_release
from .modes import set_mode, apply_mode_leds, get_current_mode, MODE_NOTES

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
        port_name = find_port()
        with mido.open_input(port_name) as inport:
            print(f"Listening on {port_name} — Ctrl+C to stop")
            set_mode(1)
            for msg in inport:
                handle_message(msg)
    except KeyboardInterrupt:
        sys.exit(0)