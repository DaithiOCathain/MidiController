import os
import subprocess

from .config import SOUND_DIR


def play_sound(filename):
    def action():
        subprocess.Popen(
            ["ffplay", "-nodisp", "-autoexit", "-loglevel", "quiet", f"{SOUND_DIR}/{filename}"]
        )
    return action


def build_soundboard_mode():
    try:
        files = sorted(
            f for f in os.listdir(SOUND_DIR)
            if f.lower().endswith((".mp3", ".wav"))
        )
    except FileNotFoundError:
        print(f"Soundboard: {SOUND_DIR} not found")
        files = []

    notes = [36, 37, 38, 39, 40, 41, 42, 43]  # P1-P8
    handlers = {}

    for note, filename in zip(notes, files):
        handlers[note] = play_sound(filename)

    if len(files) < len(notes):
        print(f"Soundboard: only {len(files)} sound(s) found, {len(notes) - len(files)} pad(s) unbound")

    return handlers