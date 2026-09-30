# LPD8 Media & Desktop Controller

A Python-based MIDI controller mapper for the **Akai LPD8**, turning its pads and knobs into a physical control surface for **VLC (video)**, **MPV (audio)**, system audio, OBS, screenshots, monitor power control, and a self-contained 8-mode switching system with pad-LED feedback and animations.

The mapper listens for MIDI messages from the LPD8 and translates them into application commands (via VLC's HTTP interface and MPV's IPC socket), keyboard shortcuts, or system actions.

## Features

- 🎬 **VLC (video)** — launch/toggle + raise window, save position + quit, absolute seeking, jog/shuttle control, subtitle/audio track cycling, automatic playlist export (including session-added items) to `.m3u`
- 🎵 **MPV (audio)** — play/pause, next track, quit, speed-sensitive scrubbing
- 🕹️ **8-mode system** — switch via PROG CHNG (modes 1–4) or a dedicated knob dial (modes 1–8), with P1–P8 LEDs showing the active mode
- 💡 **Pad LED feedback** — persistent, software-controlled indicator lights; mode 4 includes 4 selectable pad-chase animations
- 🔊 **System audio** — volume control, mute toggle
- 🖥️ **Desktop control** — toggle secondary monitors via DPMS, screenshots via Spectacle
- 🎥 **Scripting** — add user-provided scripts

## Hardware Layout

```
Top:       P5  P6  P7  P8   | K1  K2  K3  K4
Bottom:    P1  P2  P3  P4   | K5  K6  K7  K8
```

Three physical device modes, switched via the corresponding buttons on the LPD8 itself:

- **PAD** — note messages (used for P1–P8 actions and LED-lit mode indicators)
- **CC** — control-change messages (used for knobs)
- **PROG CHNG** — program-change messages (used for modes 1–4 and a few fixed system actions)

---

## Project Structure

```
MidiController/
├── lpd8_mapper.py              # entry point only
├── midi_listen.py              # standalone debug utility — dumps raw MIDI messages
├── tests/                      # pytest suite — see Testing section below
└── midi_controller/
    ├── __init__.py
    ├── config.py                # paths, ports, playlists, target screen — all constants
    ├── keyboard_actions.py      # make_key_action, make_shift_key_action
    ├── system_actions.py        # screenshot, monitor toggle, mute, OBS restart, volume
    ├── scrub.py                 # scrub_delta, scrub_seconds, fine_scrub state
    ├── mpv_control.py           # MPV IPC functions, MPV save+quit (resume state)
    ├── vlc_control.py           # VLCInstance class (HTTP-only), VIDEO_VLC, jog/seek knobs
    ├── pad_lights.py            # MIDI output / LED primitives, animation loops
    ├── modes.py                 # mode state, mode-switch LED logic, mode-dial knob handler
    ├── mappings.py               # PAD_PRESS_BY_MODE / PAD_PRESS_FIXED / PAD_PROGRAM_PRESS / CC_HANDLERS
    └── dispatcher.py            # find_port, handle_message, main()
```

Install
- clone the repo, 
- install dependencies, 
- edit `midi_controller/config.py` to match your own media locations,
- run `lpd8_mapper.py` directly.

---

## Installation

### Requirements

- Linux desktop (developed against KDE Plasma; `kscreen-doctor` and `spectacle` are KDE-specific)
- An Akai LPD8 connected over USB
- `mpv`, `vlc`, `pactl`, `spectacle`, `kscreen-doctor`, `xdotool`, `xrandr`
- An OBS restart script (user-provided, executable)
- Python packages: `mido`, `pynput`, and a MIDI backend (`python-rtmidi`)

```
python3 -m pip install mido pynput python-rtmidi
```

Debian/Ubuntu-based systems may prefer the system packages instead:

```
sudo apt install python3-mido python3-pynput python3-rtmidi
```

---

## Configuration

Constants live in `midi_controller/config.py`. Paths are built from the current user's home directory via `pathlib.Path.home()`:

```python
from pathlib import Path

HOME = Path.home()

MPV_SOCKET_PATH = "/tmp/mpvsocket"
MPV_PLAYLIST = str(HOME / "Documents" / "allmusic.m3u")

SCREENSHOT_PATH = str(HOME / "sofa_screenshot.png")
OBS_RESTART_SCRIPT = str(HOME / ".local" / "bin" / "restart-obs.sh")

RESUME_FILE = str(HOME / ".vlc_resume.json")

VIDEO_VLC_CONFIG = dict(
    name="video",
    host="127.0.0.1",
    http_port=8081,
    http_password="videopass",
    playlist=str(HOME / "Documents" / "video.m3u"),
    resume_file=RESUME_FILE,
    target_screen="DVI-I-1",
    extra_args=["--fullscreen", "--no-spu", "--avcodec-hw=none"],
)
```

**Change `http_password` from the placeholder value.** It's local-loopback-only (`127.0.0.1`), so the stakes are low, but don't ship the literal example password.

**`target_screen`** must exactly match an output name from:

```
xrandr --listmonitors
```

(e.g. `DVI-I-1`, not `DVI-1` — match case and naming precisely). This is resolved to a numeric index at launch time and passed as `--qt-fullscreen-screennumber=N`. `[verifiable]` VLC's own forum has multiple reports of this flag behaving unreliably — sometimes affecting only the interface and not the video output, sometimes ignored outright. Test it after any monitor/cable change rather than assuming it still works.

### VLC — resume state

On save-and-quit, current playback time and the VLC-internal current-item ID (`currentplid`, from `status.json`) are written to `RESUME_FILE`, keyed by instance name. On next launch, playback resumes at that item and time. This replaced an earlier RC-based approach that tracked playlist *position* rather than item ID — ID-based resume is more robust since item IDs don't shift when the playlist is reordered or added to.

### VLC — playlist export

Every VLC instance periodically (default: every 10 minutes while running) and on every save-and-quit exports its *live* playlist — including anything added during the session, not just the original file — back over its own configured `.m3u` path, via `/requests/playlist.json`. Output includes `#EXTM3U`/`#EXTINF` headers with proper per-track titles (falling back to filename if VLC has no title metadata for an item), not bare file paths.

### Window raising

`raise_window()` uses `xdotool` to bring the video instance's window to the front by tracked PID — requires an X11 session. No Wayland equivalent is implemented.

### Launch race guard

`VLCInstance.launching` is a boolean guard preventing a second VLC process from spawning if the pad is pressed again while a previous launch is still completing (the async "wait for HTTP interface to come up" step). Rapid repeated presses during startup are ignored rather than spawning duplicate processes.

---

## The 8-mode system

Modes are tracked centrally in `midi_controller/modes.py` (`get_current_mode()` / `set_mode(n)`), imported by both `dispatcher.py` (for PROG CHNG and pad dispatch) and `mappings.py` (for the knob dial), avoiding a circular import between the two.

### Switching modes

- **Knob K1 (CC 1)** → modes 1–8, via `mode_dial_knob()` in `modes.py`. The knob's 0–127 range is split into 8 zones (~16 values each) with a small hysteresis dead-band (±3) at zone boundaries to prevent flicker when the knob rests near an edge.
- **PROG CHNG programs 4–7** → modes 1–4 (`MODE_PROGRAMS` in `dispatcher.py`). Programs 0–3 remain fixed system actions (monitor toggle, mute, OBS restart), unrelated to mode-switching.

### Mode indicator LEDs

`MODE_NOTES` maps each mode (1–8) to its corresponding pad's note (P1=36 … P8=43). `apply_mode_leds()` lights exactly one pad at a time, matching the current mode; `set_mode()` also stops any running VLC jog/shuttle, releases fine-scrub, and stops any running pad animation, before updating the LED state — this is deliberate: switching modes force-stops whatever was mid-action rather than leaving it running in the background.

### Mode content

| Mode | Trigger | P1 | P2 | P3 | P4 | P5 |
| ---- | ------- | -- | -- | -- | -- | -- |
| 1 | PROG CHNG / knob | VLC launch/toggle + raise | Seek −4s | Cycle subtitle track (`V` key) | Cycle audio track (`B` key) | VLC save + quit |
| 2 | PROG CHNG / knob | MPV launch/toggle | MPV next track | *(unset)* | *(unset)* | MPV save + quit (resume state) |
| 3 | knob only | — | — | — | — | *(unset — placeholder, possible karaoke/Ultrastar Deluxe)* |
| 4 | PROG CHNG / knob | Chase animation | Bounce animation | Alternate animation | Strobe animation | Stop animation |
| 5–8 | knob only | — | — | — | — | *(unset — placeholders)* |

P6–P8 are currently unbound in every mode. Mode 1's save-quit (P5) goes through `save_and_quit_vlc()`, a lock-guarded wrapper preventing a second save-and-quit from starting while one is already in progress.

### Pad animations (mode 4)

Defined in `pad_lights.py`: `animation_chase`, `animation_bounce`, `animation_alternate`, `animation_strobe`, each running on a background daemon thread with a `threading.Event` stop flag (`stop_animation()`). Animations use all 8 pads (P1–P8) as their canvas, independent of the mode-indicator LEDs, which reassert themselves via the retry loop and on the next real pad press.

---

## Pad Mapping — PROG CHNG Mode (fixed, non-mode-dependent)

| Pad | Program | Action |
| --- | ------- | ------ |
| P1 | 0 | Toggle secondary monitors |
| P2 | 1 | Toggle system mute |
| P3 | 2 | Restart OBS |
| P4 | 3 | Toggle secondary monitors (shares state with P1) |
| P5–P8 | 4–7 | Switch to mode 1–4 (see above) |

## Knob Mapping — CC Mode

| Knob | CC | Action |
| ---- | -- | ------ |
| K1 | 1 | 8-mode dial (see above) |
| K3 | 3 | VLC absolute seek, 0–100% |
| K4 | 4 | VLC jog/shuttle |
| K5 | 5 | MPV speed-sensitive scrub |
| K8 | 8 | System volume, 0–100% |

K2, K6, K7 are unused.

### K4 — jog/shuttle zones

| MIDI value | Zone | Behaviour |
| ---------- | ---- | --------- |
| 0–15 | Fast fast rewind | Repeated `-10s` seeks |
| 16–31 | Fast rewind | Repeated `-3s` seeks |
| 32–47 | Slow rewind | Repeated `-1s` seeks |
| 48–79 | Normal | Normal playback |
| 80–95 | Step forward | Frame-by-frame advance (forward only — see HTTP limitation above) |
| 96–111 | Fast forward | 2× rate |
| 112–127 | Fast fast forward | 4× rate |

VLC doesn't reliably support negative playback rates, so rewind is simulated via repeated backward seeks rather than a negative rate.

### K5 — MPV scrub speed curve

| Knob movement speed | Seek per MIDI step |
| -------------------- | ------------------- |
| < 2 steps/sec | 1 second |
| < 5 steps/sec | 2 seconds |
| < 10 steps/sec | 5 seconds |
| < 20 steps/sec | 15 seconds |
| ≥ 20 steps/sec | 30 seconds |

---

## Running

```
python3 lpd8_mapper.py
```

The mapper searches available MIDI input ports for one whose name contains `LPD8`. On success:

```
Listening on <port name> — Ctrl+C to stop
```

Mode 1's LED lights on startup by default. Stop with `Ctrl+C`.

### Debugging raw MIDI

`midi_listen.py` is a separate, standalone script — not used by the mapper — that connects to a hard-coded port name and prints every incoming MIDI message verbatim.

```
python3 midi_listen.py
```

---

## Testing

`tests/` contains a pytest suite. Currently: one import-smoke-test per module (`tests/test_imports.py`), confirming every module parses and imports cleanly without a running MIDI device or live VLC/MPV instance.

```
pip install pytest --break-system-packages
pytest tests/
```

**Run this after every edit, before restarting the live service.** Most bugs hit during development tonight were import-time failures — bad indentation, a stray `...` placeholder left in real code, an undefined-name typo, a method missing `self` in its signature — all things this suite catches in under a second, versus discovering them via a crash-looping systemd service and a `journalctl` round-trip.

### TODO — testing & logging improvements

- [ ] Add `ruff` (or `pyflakes`) as a static-analysis pass — catches undefined-name bugs (e.g. a variable referenced but never assigned) *before* runtime, which plain import-success tests can't catch if the bad code path isn't exercised at import time
- [ ] Add attribute-existence tests per module (e.g. `hasattr(VLCInstance, "export_playlist")`) — catches the specific failure mode of a method accidentally landing outside its class body (wrong indentation), which import-success alone doesn't catch
- [ ] Add a smoke test against a *running* VLC HTTP interface (`VIDEO_VLC.http_command()` returns a dict with `"state"`) — catches "this HTTP command doesn't actually exist" bugs (e.g. the fabricated `key`/`key-frame-next` command that silently no-op'd)
- [ ] Switch from bare `print()` to Python's `logging` module with levels (`DEBUG`/`INFO`/`ERROR`), so `journalctl` output can be filtered by severity
- [ ] Ensure every `except Exception:` block logs the exception (`except Exception as e: print(f"...: {e!r}")`) rather than silently swallowing it — a silent bare `except` hid the `current_index` `NameError` bug for an extended period during development

---

## Troubleshooting

**`LPD8 not found`** — list MIDI inputs and confirm the device appears:

```
python3 -c "import mido; print(mido.get_input_names())"
```

**VLC controls do nothing** — confirm the HTTP interface is actually listening:

```
curl -u ":videopass" "http://127.0.0.1:8081/requests/status.json"
```

(replace `videopass` with your configured `http_password`). If this fails, check the journal for whether VLC's HTTP module actually bound on startup.

**VLC keeps re-launching instead of toggling** — this was previously caused by VLC's RC interface being silently dropped when loaded alongside HTTP (`--extraintf=rc,http` limitation); the HTTP-only refactor should have eliminated this class of bug entirely. If it recurs, confirm `is_running()` is actually able to reach the HTTP port.

**Video doesn't open on the target screen** — confirm the configured `target_screen` exactly matches `xrandr --listmonitors` output; check the journal for `couldn't resolve screen '...'` messages, which list the actually-detected output names if no match is found.

**Mode LED doesn't show after switching via PROG CHNG** — expected if you haven't returned to PAD mode yet; LEDs only render in PAD mode. A retry loop re-asserts the LED for ~4 seconds after any switch. If it's still dark after returning to PAD mode within that window, press any pad — this also re-asserts current mode LEDs as a fallback.

**Monitor toggle does nothing** — check actual output names:

```
kscreen-doctor output
```

**Volume control does nothing** — test the sink directly:

```
pactl get-default-sink
pactl set-sink-volume @DEFAULT_SINK@ 50%
```

---

## Known limitations

- `xdotool`-based window raising and screen-targeting require X11; no Wayland path exists.
- VLC frame-stepping: forward-only (keyboard simulation, requires window focus), backward frame-stepping does not exist in VLC at all.
- Modes 3 and 5–8 are unbound placeholders.
- P6–P8 are unbound in every mode.
- `save_and_quit()` (VLC) blocks briefly waiting on the HTTP status fetch and on `SIGTERM`/`wait(timeout=3)` before falling back to `SIGKILL` — a hung VLC process delays the next MIDI event's processing for that window.
- `target_screen` resolution depends on `xrandr` output naming staying stable; a monitor/cable change may require updating `config.py`.
- No automated tests beyond import-smoke-tests yet (see TODO above).

---

## License

Released into the public domain under The Unlicense. See the `LICENSE` file for full text.