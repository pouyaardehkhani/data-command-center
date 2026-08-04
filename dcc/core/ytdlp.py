"""Wraps bin/yt-dlp.exe: metadata lookup (blocking, quick) and building the
download job args (executed through the shared sequential JobQueue)."""
from __future__ import annotations

import json
import subprocess
from dataclasses import dataclass, field

from dcc.paths import NO_WINDOW_FLAGS, ytdlp_path


def _format_size(num_bytes: int, is_approx: bool) -> str:
    if not num_bytes:
        return ""
    size = float(num_bytes)
    for unit in ("B", "KiB", "MiB", "GiB"):
        if size < 1024.0 or unit == "GiB":
            text = f"{size:.0f}{unit}" if unit == "B" else f"{size:.2f}{unit}"
            return f"~{text}" if is_approx else text
        size /= 1024.0
    return ""


@dataclass
class VideoFormat:
    format_id: str
    ext: str
    resolution: str
    fps: float
    vcodec: str
    acodec: str
    filesize_approx: int
    note: str = ""
    height: int = 0
    width: int = 0
    tbr: float = 0.0   # video (or overall) bitrate, kbps
    abr: float = 0.0   # audio bitrate, kbps
    filesize_is_approx: bool = False

    @property
    def is_audio_only(self) -> bool:
        return self.vcodec in ("", "none")

    @property
    def is_video_only(self) -> bool:
        return self.acodec in ("", "none") and not self.is_audio_only

    @property
    def size_label(self) -> str:
        return _format_size(self.filesize_approx, self.filesize_is_approx)

    @property
    def label(self) -> str:
        size = self.size_label
        size_part = f" - {size}" if size else ""
        if self.is_audio_only:
            bitrate = f" - {round(self.abr)}kbps" if self.abr else ""
            return f"{self.acodec} ({self.ext}){bitrate}{size_part} {self.note}".strip()
        kind = "video only" if self.is_video_only else "video+audio"
        bitrate = f" - {round(self.tbr)}kbps" if self.tbr else ""
        fps = f"{self.fps:g}fps " if self.fps else ""
        return f"{self.resolution} {fps}- {self.ext} ({kind}){bitrate}{size_part} {self.note}".strip()

    @property
    def video_sort_key(self):
        return (self.height, self.tbr)

    @property
    def audio_sort_key(self):
        return (self.abr,)


@dataclass
class VideoInfo:
    title: str = ""
    duration: float = 0.0
    uploader: str = ""
    thumbnail: str = ""
    webpage_url: str = ""
    is_playlist: bool = False
    playlist_count: int = 0
    formats: list = field(default_factory=list)


def fetch_info(url: str, timeout: int = 45, cookies_file: str = "") -> VideoInfo:
    args = [ytdlp_path(), "-J", "--no-warnings", "--flat-playlist"]
    if cookies_file:
        args += ["--cookies", cookies_file]
    args += [url]
    result = subprocess.run(
        args, capture_output=True, text=True, creationflags=NO_WINDOW_FLAGS, timeout=timeout
    )
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or "yt-dlp failed to fetch info")

    data = json.loads(result.stdout)

    if data.get("_type") == "playlist":
        entries = data.get("entries", [])
        return VideoInfo(
            title=data.get("title", url),
            is_playlist=True,
            playlist_count=len(entries),
            webpage_url=url,
        )

    formats = []
    for f in data.get("formats", []):
        exact_size = f.get("filesize") or 0
        approx_size = f.get("filesize_approx") or 0
        formats.append(VideoFormat(
            format_id=f.get("format_id", ""),
            ext=f.get("ext", ""),
            resolution=f.get("format_note") or (f"{f.get('width', '')}x{f.get('height', '')}" if f.get("width") else ""),
            fps=f.get("fps") or 0,
            vcodec=f.get("vcodec", "none") or "none",
            acodec=f.get("acodec", "none") or "none",
            filesize_approx=exact_size or approx_size,
            filesize_is_approx=not exact_size and bool(approx_size),
            note=f.get("format_note", "") or "",
            height=f.get("height") or 0,
            width=f.get("width") or 0,
            tbr=f.get("tbr") or f.get("vbr") or 0.0,
            abr=f.get("abr") or (f.get("tbr") or 0.0 if f.get("vcodec", "none") in ("", "none") else 0.0),
        ))

    return VideoInfo(
        title=data.get("title", url),
        duration=float(data.get("duration") or 0),
        uploader=data.get("uploader", ""),
        thumbnail=data.get("thumbnail", ""),
        webpage_url=data.get("webpage_url", url),
        formats=formats,
    )


def build_download_args(url: str, output_dir: str, format_selector: str,
                         audio_only: bool = False, embed_subs: bool = False,
                         playlist: bool = False, playlist_items: str = "",
                         use_archive: bool = False, cookies_file: str = "") -> list:
    args = [ytdlp_path(), "--newline", "--no-warnings", "-o", f"{output_dir}/%(title)s.%(ext)s"]

    if cookies_file:
        args += ["--cookies", cookies_file]

    if not playlist:
        args += ["--no-playlist"]
    elif playlist_items.strip():
        args += ["--playlist-items", playlist_items.strip()]

    if audio_only:
        args += ["-x", "--audio-format", "mp3"]
    else:
        args += ["-f", format_selector or "bv*+ba/b", "--merge-output-format", "mp4"]

    if embed_subs:
        args += ["--write-subs", "--embed-subs"]

    if use_archive:
        args += ["--download-archive", f"{output_dir}/downloaded.txt"]

    args += [url]
    return args


def update_ytdlp(timeout: int = 90) -> tuple:
    """Runs yt-dlp's self-updater (yt-dlp.exe -U). Returns (success, message)."""
    try:
        result = subprocess.run(
            [ytdlp_path(), "-U"], capture_output=True, text=True,
            creationflags=NO_WINDOW_FLAGS, timeout=timeout,
        )
        output = ((result.stdout or "") + (result.stderr or "")).strip()
        return result.returncode == 0, output or "yt-dlp did not report a result."
    except Exception as e:
        return False, str(e)
