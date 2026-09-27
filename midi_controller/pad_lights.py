import threading
import time

import mido

_outport = None
_animation_stop = None

ALL_NOTES = [36, 37, 38, 39, 40, 41, 42, 43]


def get_outport():
    global _outport
    if _outport is None:
        for name in mido.get_output_names():
            if "LPD8" in name:
                _outport = mido.open_output(name)
                break
    return _outport


def light_pad(note, on=True):
    outport = get_outport()
    if outport is None:
        return
    if on:
        outport.send(mido.Message('note_on', note=note, velocity=127))
    else:
        outport.send(mido.Message('note_off', note=note))


def stop_animation():
    global _animation_stop
    if _animation_stop is not None:
        _animation_stop.set()
        _animation_stop = None


def _start(loop_fn):
    global _animation_stop
    stop_animation()
    stop_event = threading.Event()
    _animation_stop = stop_event
    threading.Thread(target=loop_fn, args=(stop_event,), daemon=True).start()


def animation_chase(interval=0.12):
    def loop(stop_event):
        i = 0
        while not stop_event.is_set():
            note = ALL_NOTES[i % len(ALL_NOTES)]
            light_pad(note, on=True)
            time.sleep(interval)
            light_pad(note, on=False)
            i += 1
    _start(loop)


def animation_bounce(interval=0.12):
    def loop(stop_event):
        seq = ALL_NOTES + ALL_NOTES[-2:0:-1]
        i = 0
        while not stop_event.is_set():
            note = seq[i % len(seq)]
            light_pad(note, on=True)
            time.sleep(interval)
            light_pad(note, on=False)
            i += 1
    _start(loop)


def animation_alternate(interval=0.25):
    def loop(stop_event):
        evens = ALL_NOTES[0::2]
        odds = ALL_NOTES[1::2]
        state = True
        while not stop_event.is_set():
            group_on, group_off = (evens, odds) if state else (odds, evens)
            for n in group_on:
                light_pad(n, on=True)
            for n in group_off:
                light_pad(n, on=False)
            time.sleep(interval)
            state = not state
    _start(loop)


def animation_strobe(interval=0.15):
    def loop(stop_event):
        state = True
        while not stop_event.is_set():
            for n in ALL_NOTES:
                light_pad(n, on=state)
            time.sleep(interval)
            state = not state
    _start(loop)