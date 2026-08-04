"""Resolves paths to bundled binaries and user data folders, both in dev and
when frozen into a PyInstaller onedir build."""
import os
import sys
from pathlib import Path

from dcc import APP_ORG


def app_root() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys._MEIPASS)  # type: ignore[attr-defined]
    return Path(__file__).resolve().parent.parent


def bin_dir() -> Path:
    return app_root() / "bin"


def ffmpeg_path() -> str:
    return str(bin_dir() / "ffmpeg.exe")


def ffprobe_path() -> str:
    return str(bin_dir() / "ffprobe.exe")


def ytdlp_path() -> str:
    return str(bin_dir() / "yt-dlp.exe")


def user_data_dir() -> Path:
    base = os.environ.get("APPDATA", str(Path.home()))
    d = Path(base) / APP_ORG
    d.mkdir(parents=True, exist_ok=True)
    return d


def presets_dir() -> Path:
    d = user_data_dir() / "presets"
    d.mkdir(parents=True, exist_ok=True)
    return d


def default_output_dir() -> Path:
    d = Path.home() / "Videos" / "Data Command Center"
    d.mkdir(parents=True, exist_ok=True)
    return d


NO_WINDOW_FLAGS = 0x08000000 if sys.platform == "win32" else 0
