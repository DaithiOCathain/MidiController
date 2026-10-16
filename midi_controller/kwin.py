import itertools
import json
import os
import re
import subprocess
import tempfile
import time

_n = itertools.count()
_DEST = ["gdbus", "call", "--session", "--dest", "org.kde.KWin"]
PLACEMENT_NAME = "lpd8-placement"

_PLACEMENT_JS = """
function key(w) {
  const c = String(w.resourceClass).toLowerCase();
  return Object.keys(RULES).find(k => c.includes(k));
}
function place(w) {
  const k = key(w);
  if (!k) return;
  w.desktops = [];                       // all desktops
  const out = workspace.screens.find(o => o.name === RULES[k]);
  if (!out) return;                      // output off: leave it, re-place on return
  w.fullScreen = false;
  workspace.sendClientToScreen(w, out);
  w.fullScreen = true;
}
workspace.windowList().forEach(place);
workspace.windowAdded.connect(place);
workspace.screensChanged.connect(() => workspace.windowList().forEach(place));
"""

_SHOW_JS = """
for (const w of workspace.windowList()) {
  if (!String(w.resourceClass).toLowerCase().includes(CLS)) continue;
  w.minimized = false;
  workspace.activeWindow = w;
}
"""

_HIDE_JS = """
for (const w of workspace.windowList()) {
  if (String(w.resourceClass).toLowerCase().includes(CLS)) w.minimized = true;
}
"""


def _gdbus(obj, method, *args):
    return subprocess.run(
        [*_DEST, "--object-path", obj, "--method", method, *args],
        capture_output=True, text=True, timeout=3, check=False,
    )


def _load_and_run(name, js):
    with tempfile.NamedTemporaryFile("w", suffix=".js", delete=False) as f:
        f.write(js)
        path = f.name
    try:
        r = _gdbus("/Scripting", "org.kde.kwin.Scripting.loadScript", path, name)
        m = re.search(r"\d+", r.stdout)
        if r.returncode or not m:
            print(f"kwin: loadScript failed: {r.stderr.strip()}")
            return False
        sid = m.group()
        for obj in (f"/Scripting/Script{sid}", f"/{sid}"):  # Plasma 6 / Plasma 5 paths
            if _gdbus(obj, "org.kde.kwin.Script.run").returncode == 0:
                return True
        print("kwin: Script.run failed on both object paths")
        return False
    finally:
        os.unlink(path)


def _oneshot(js, **params):
    header = "".join(f"const {k} = {json.dumps(v)};\n" for k, v in params.items())
    name = f"lpd8-{os.getpid()}-{next(_n)}"
    if _load_and_run(name, header + js):
        time.sleep(0.2)
        _gdbus("/Scripting", "org.kde.kwin.Scripting.unloadScript", name)


def install_placement(rules):
    """rules: {"mpv": "DVI-I-1", "vlc": "DVI-I-1"} — class substring -> output name."""
    _gdbus("/Scripting", "org.kde.kwin.Scripting.unloadScript", PLACEMENT_NAME)
    _load_and_run(PLACEMENT_NAME, f"const RULES = {json.dumps(rules)};\n" + _PLACEMENT_JS)


def show(cls):
    _oneshot(_SHOW_JS, CLS=cls)


def hide(cls):
    _oneshot(_HIDE_JS, CLS=cls)