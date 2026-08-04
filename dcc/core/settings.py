"""Persistent app settings (theme, default GPU, output folder, window geometry)
backed by QSettings, stored per-user under the registry/ini on Windows."""
from __future__ import annotations

from PySide6.QtCore import QSettings

from dcc import APP_NAME, APP_ORG
from dcc.paths import default_output_dir


def _store() -> QSettings:
    return QSettings(APP_ORG, APP_NAME)


def get_theme() -> str:
    return _store().value("theme", "dark")


def set_theme(theme: str) -> None:
    _store().setValue("theme", theme)


def get_default_gpu() -> str:
    return _store().value("default_gpu", "")


def set_default_gpu(vendor: str) -> None:
    _store().setValue("default_gpu", vendor)


def get_output_dir() -> str:
    return _store().value("output_dir", str(default_output_dir()))


def set_output_dir(path: str) -> None:
    _store().setValue("output_dir", path)


def get_geometry():
    return _store().value("window_geometry")


def set_geometry(geometry) -> None:
    _store().setValue("window_geometry", geometry)


def get_use_cookies() -> bool:
    value = _store().value("ytdlp_use_cookies", False)
    return value in (True, "true", "1", 1)


def set_use_cookies(enabled: bool) -> None:
    _store().setValue("ytdlp_use_cookies", bool(enabled))


def get_cookies_path() -> str:
    return _store().value("ytdlp_cookies_path", "")


def set_cookies_path(path: str) -> None:
    _store().setValue("ytdlp_cookies_path", path)
