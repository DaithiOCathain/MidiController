import os
import subprocess

KEY_BACKEND = os.environ.get("LPD8_KEY_BACKEND", "pynput")
_EVDEV = {"esc": 1, "tab": 15, "enter": 28, "space": 57,
          "up": 103, "left": 105, "right": 106, "down": 108}


def make_named_key_action(name):
    def action():
        if KEY_BACKEND == "ydotool":
            c = _EVDEV[name]
            subprocess.Popen(["ydotool", "key", f"{c}:1", f"{c}:0"])
        else:
            from pynput.keyboard import Controller, Key
            k = getattr(Key, name)
            kb = Controller()
            kb.press(k)
            kb.release(k)
    return action
    
    
def make_key_action(key):
    def action():
        from pynput.keyboard import Controller

        keyboard = Controller()
        keyboard.press(key)
        keyboard.release(key)

    return action


def make_shift_key_action(key):
    def action():
        from pynput.keyboard import Controller, Key

        keyboard = Controller()
        keyboard.press(Key.shift)
        keyboard.press(key)
        keyboard.release(key)
        keyboard.release(Key.shift)

    return action