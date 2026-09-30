from pathlib import Path

HOME = Path.home()

MPV_SOCKET_PATH = "/tmp/mpvsocket"
MPV_PLAYLIST = str(HOME / "Documents" / "audio.m3u")

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