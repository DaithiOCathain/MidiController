import threading

import mido

_outport = None
_animation_stop = None
_animation_speed = 1.0

ALL_NOTES = [36, 37, 38, 39, 40, 41, 42, 43]

TOP = ALL_NOTES[:4]
BOTTOM = ALL_NOTES[4:]
ROWS = (TOP, BOTTOM)

def _wait(stop_event, interval):
    return stop_event.wait(interval * _animation_speed)

def get_outport():
    global _outport

    if _outport is None:
        for name in mido.get_output_names():
            if "LPD8" in name:
                _outport = mido.open_output(name)
                break

    return _outport

def reset_outport():
    global _outport
    if _outport is not None:
        try:
            _outport.close()
        except Exception as e:  # noqa: BLE001 - port may already be gone
            print(f"pad_lights: outport close failed: {e!r}")
    _outport = None

def animation_speed_knob(value):
    """Set the global animation speed from MIDI CC 1 (0–127)."""
    global _animation_speed

    # 0 = fastest, 127 = slowest
    _animation_speed = 0.25 + (value / 127) * 3.75

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

    threading.Thread(
        target=loop_fn,
        args=(stop_event,),
        daemon=True,
    ).start()


def _set_grid(grid):
    for row, notes in enumerate(ROWS):
        for col, note in enumerate(notes):
            light_pad(note, on=grid[row][col])


def animation_chase(interval=0.12):
    def loop(stop_event):
        i = 0

        while not stop_event.is_set():
            note = ALL_NOTES[i % len(ALL_NOTES)]

            light_pad(note, on=True)
            if _wait(stop_event, interval):
                return
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
            if _wait(stop_event, interval):
                return
            light_pad(note, on=False)

            i += 1

    _start(loop)


def animation_alternate(interval=0.25):
    def loop(stop_event):
        evens = ALL_NOTES[0::2]
        odds = ALL_NOTES[1::2]
        state = True

        while not stop_event.is_set():
            group_on, group_off = (
                (evens, odds) if state else (odds, evens)
            )

            for n in group_on:
                light_pad(n, on=True)

            for n in group_off:
                light_pad(n, on=False)

            if _wait(stop_event, interval):
                return
            state = not state

    _start(loop)


def animation_strobe(interval=0.15):
    def loop(stop_event):
        state = True

        while not stop_event.is_set():
            for n in ALL_NOTES:
                light_pad(n, on=state)

            if _wait(stop_event, interval):
                return
            state = not state

    _start(loop)


def animation_scan(interval=0.12):
    """Sweep a light across both rows, then back."""
    def loop(stop_event):
        while not stop_event.is_set():
            for col in range(4):
                grid = [
                    [i == col for i in range(4)],
                    [i == col for i in range(4)],
                ]

                _set_grid(grid)

                if stop_event.wait(interval):
                    return

            for col in range(2, 0, -1):
                grid = [
                    [i == col for i in range(4)],
                    [i == col for i in range(4)],
                ]

                _set_grid(grid)

                if stop_event.wait(interval):
                    return

    _start(loop)


def animation_ripple(interval=0.15):
    """Pulse outwards from the centre of the 2x4 grid."""
    patterns = [
        [
            [False, False, False, False],
            [False, True, True, False],
        ],
        [
            [False, True, True, False],
            [True, False, False, True],
        ],
        [
            [True, False, False, True],
            [False, False, False, False],
        ],
        [
            [False, False, False, False],
            [False, False, False, False],
        ],
    ]

    def loop(stop_event):
        while not stop_event.is_set():
            for grid in patterns:
                _set_grid(grid)

                if stop_event.wait(interval):
                    return

    _start(loop)


def animation_checkerboard(interval=0.25):
    """Alternate between the two 2x4 checkerboard patterns."""
    patterns = (
        [
            [True, False, True, False],
            [False, True, False, True],
        ],
        [
            [False, True, False, True],
            [True, False, True, False],
        ],
    )

    def loop(stop_event):
        while not stop_event.is_set():
            for grid in patterns:
                _set_grid(grid)

                if stop_event.wait(interval):
                    return

    _start(loop)


def animation_binary_grid(interval=0.12):
    """
    Treat the 2x4 grid as eight bits.

    Each column is a two-bit number, with the top pad
    as the high bit and the bottom pad as the low bit.
    """
    def loop(stop_event):
        value = 0

        while not stop_event.is_set():
            grid = [
                [bool((value >> (col * 2 + 1)) & 1) for col in range(4)],
                [bool((value >> (col * 2)) & 1) for col in range(4)],
            ]

            _set_grid(grid)

            if stop_event.wait(interval):
                return

            value = (value + 1) % 256

    _start(loop)