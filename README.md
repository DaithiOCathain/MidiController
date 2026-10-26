<div align="center">

# 🎛️ LPD8 Desk Controller

**Eight pads. Eight knobs. Eight modes. One very well-behaved desk.**

Turn an Akai LPD8 into a physical control surface for your media players, smart sockets, bulbs, monitors and soundboard, with pad lights that tell you what mode you're in.

`🎬 video` · `🎵 music` · `💡 lights` · `🔌 sockets` · `🖥️ monitors` · `🔊 sounds` · `🗣️ voice`

</div>

---

## ✨ What it does

The mapper listens to the LPD8 over MIDI and turns pads and knobs into actions. It talks to **VLC** over HTTP, **mpv** over its IPC socket, **Tuya** sockets and **Kasa** bulbs over the LAN, **KWin** over D-Bus, and everything else through plain subprocess calls.

- 🕹️ **Eight modes**, chosen with a dial knob. The active mode lights its own pad.
- 💡 **Pad light feedback**, including a small gallery of animations (bounce, scan, ripple, checkerboard, a binary counter…).
- 🪟 **Player juggling**: starting one player politely pauses and hides the other.
- 🎚️ **Smart knobs**: speed-sensitive scrubbing, jog/shuttle, bulb brightness, colour temperature and hue.
- 🗣️ **A command socket**, so voice tools, scripts and cron can trigger the same actions the pads do.
- 🔁 **Hot-plug friendly**: unplug the LPD8, plug it back in, carry on.

> The pad and knob layout is *yours*. This README doesn't prescribe one; see [Wiring things up](#-wiring-things-up).

---

## 🗺️ How it fits together

```
   ┌──────────┐   MIDI    ┌────────────┐        ┌───────────────┐
   │   LPD8   │ ────────▶ │ dispatcher │ ─────▶ │ mappings.py   │──▶ players, lights,
   │ pads+knobs│ ◀──────── │  (modes)   │        │ (your wiring) │    sockets, system
   └──────────┘  LED notes └─────┬──────┘        └───────────────┘
                                 ▲
        voice / scripts ─▶ unix socket ─▶ commands.py
```

---

## 🧰 Hardware

```
Top:       P5  P6  P7  P8   | K1  K2  K3  K4
Bottom:    P1  P2  P3  P4   | K5  K6  K7  K8
```

The LPD8 has three message types, switched with buttons on the device itself:

- **PAD** sends notes (pad actions, and the lights you see)
- **CC** sends control changes (knobs)
- **PROG CHNG** sends program changes (quick mode jumps and a few fixed actions)

---

## 🚀 Install

You'll need a Linux desktop (built and tested on **KDE Plasma 6 / Wayland**), an LPD8, and:

```
mpv  vlc  pactl  ffplay  ddcutil  spectacle  qdbus6  xrandr
```

Python side:

```
python3 -m pip install --user mido python-rtmidi pynput tinytuya python-kasa
```

> 💡 If you develop in a Flatpak editor, `pip` installs into the sandbox. Install from a host terminal if you run the mapper under system Python.

Then:

```
git clone <your-repo-url>
cd MidiController
python3 lpd8_mapper.py
```

On success you'll see `Listening on <port name> — Ctrl+C to stop`.

---

## ⚙️ Configuration

Two layers, so a fresh clone just works and your private bits never get committed.

**1. Defaults live in `midi_controller/config.py`.** Paths, ports, playlists, safe placeholder values. It's committed.

**2. Your overrides live in `midi_controller/config_local.py`.** It's gitignored and optional. Any UPPERCASE name you set there wins, and dictionaries merge, so overriding one key is enough. A broken `config_local.py` fails loudly rather than being ignored. Start from the committed example:

```
cp midi_controller/config_local.example.py midi_controller/config_local.py
```

```python
# midi_controller/config_local.py
MEDIA_OUTPUT = "HDMI-A-1"
DESK_SERIALS = ["YOUR-MONITOR-SERIAL"]
VIDEO_VLC_CONFIG = {"http_password": "something-better"}
```

Find output names with:

```
xrandr --listmonitors
```

and monitor serials with:

```
ddcutil detect
```

### 🔌 Smart devices

Devices come from `~/.config/lpd8-mapper/sockets.json`, outside the repo. Copy the committed example and edit it:

```
mkdir -p ~/.config/lpd8-mapper
cp sockets.example.json ~/.config/lpd8-mapper/sockets.json
```

```json
[
  {"name": "lamp", "id": "REPLACE_ME", "key": "REPLACE_ME", "ip": "192.168.1.50", "version": 3.3, "dps": "1"},
  {"name": "desk-bulb", "type": "kasa", "ip": "192.168.1.60"}
]
```

Tuya entries need the device `id` and local `key` (the `tinytuya` wizard will fetch them). Kasa entries only need an IP. `kasa discover` doesn't always find bulbs; this does:

```
kasa --host 192.168.1.60 state
```

---

## 🎹 Modes

There are **eight modes**. Turn the dial knob (CC 5) to pick one, or send program changes 4–7 for the first four. The active mode's pad stays lit, and switching modes stops whatever was mid-flight: jogs, scrubs, animations.

Each mode is just a dictionary of pad handlers and a dictionary of knob handlers. What goes in them is up to you.

---

## 🔧 Wiring things up

Everything lives in `midi_controller/mappings.py`. A few possible wirings to steal from:

**A pad runs a function**

```python
PAD_PRESS_BY_MODE = {
    1: {
        36: lambda: activate(VLC_PLAYER),      # P1: show / pause the video player
        37: lambda: vlc_seek_relative(-4),     # P2: back four seconds
    },
}
```

**A knob drives a handler**

```python
CC_HANDLERS_BY_MODE = {
    7: {
        1: bulb_knob("set_brightness", brightness_scale),
        2: bulb_knob("set_color_temp", color_temp_scale),
    },
}
```

**Pads become socket toggles**

```python
PAD_PRESS_BY_MODE[7] = {
    **build_smarthome_mode(),   # one pad per socket, in sockets.json order
    43: desk_monitors_off,      # careful: later keys overwrite earlier ones
}
```

Knobs that should work in *every* mode go in `CC_HANDLERS_GLOBAL`. A per-mode knob that collides with a global one is rejected at startup with a clear error, which is the point.

---

## 🗣️ The command socket

The mapper also listens on a Unix socket at `$XDG_RUNTIME_DIR/lpd8-mapper.sock`. Send it a command name and it runs the same code the pads do:

```
echo watch | nc -U "$XDG_RUNTIME_DIR/lpd8-mapper.sock"
```

Handy for voice-control tools, shell aliases, cron and automation. Commands are fire-and-forget (nothing comes back), and every device in `sockets.json` registers `<name>_on`, `<name>_off` and `<name>_toggle` automatically. The full list lives in `commands.py`; add your own with one line:

```python
COMMANDS["movie_night"] = lambda: (activate(VLC_PLAYER), PRESET_EVENING())
```

---

## 🛠️ Development

Run this before restarting the live service:

```
ruff check --fix midi_controller/ && pytest tests/ && systemctl --user restart lpd8-mapper
```

The tests are import smoke tests, which catch most breakages (bad indentation, undefined names, stray placeholders) in under a second without needing a MIDI device or a running player.

To see raw MIDI as the LPD8 sends it, use the standalone listener:

```
python3 midi_listen.py
```

A user service is the comfortable way to run it long-term. An example unit, assuming the repo is in `~/MidiController`:

```ini
# ~/.config/systemd/user/lpd8-mapper.service
[Unit]
Description=LPD8 desk controller

[Service]
ExecStart=/usr/bin/python3 %h/MidiController/lpd8_mapper.py
Restart=on-failure

[Install]
WantedBy=default.target
```

```
systemctl --user enable --now lpd8-mapper
```

---

## 🩺 Troubleshooting

**`LPD8 not found`.** Check the device shows up as a MIDI port:

```
python3 -c "import mido; print(mido.get_input_names())"
```

**VLC does nothing.** Confirm its HTTP interface is listening (swap in your password):

```
curl -u ":your-password" "http://127.0.0.1:8081/requests/status.json"
```

**Windows land on the wrong screen.** Window placement goes through KWin scripting, keyed on window class and output name. Check your output names with `xrandr --listmonitors`.

**Volume does nothing.**

```
pactl get-default-sink
```

**A mode light is missing.** Lights only render in PAD mode on the device. They're re-asserted for a few seconds after a switch and again on the next pad press.

---

## 📌 Known limitations

- Built around **KDE Plasma**: window placement and minimise/restore use KWin. Other desktops will need their own `kwin.py` equivalent.
- VLC frame-stepping is forward-only and works by simulating a key press, so the window needs focus.
- Keyboard injection via `pynput` is X11-friendly but unreliable on pure Wayland sessions.
- Some modes are deliberately left empty for you to fill.

---

## 📜 License

Released into the public domain under [The Unlicense](LICENSE).
