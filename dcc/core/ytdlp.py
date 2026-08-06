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


def _parse_formats(raw_formats: list) -> list:
    formats = []
    for f in raw_formats:
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
    return formats


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

    return VideoInfo(
        title=data.get("title", url),
        duration=float(data.get("duration") or 0),
        uploader=data.get("uploader", ""),
        thumbnail=data.get("thumbnail", ""),
        webpage_url=data.get("webpage_url", url),
        formats=_parse_formats(data.get("formats", [])),
    )


def fetch_playlist_common_formats(url: str, cookies_file: str = "", timeout: int = 3600,
                                   on_progress=None) -> tuple:
    """Fetches full per-video metadata for every item in the playlist (same one-by-one
    extraction `yt-dlp -F` does) and intersects each video's format_ids, so the caller
    can offer only the qualities available on every video in the playlist. This makes
    one network request per video - it's slow for large playlists, so it should be run
    off the UI thread; on_progress(videos_checked, current_title) is called after each one.

    Returns (common_formats, video_count) where common_formats is a list of
    representative VideoFormat objects (taken from the first video) for every
    format_id shared by all videos.
    """
    args = [ytdlp_path(), "-j", "--no-warnings", "--yes-playlist", "--ignore-errors"]
    if cookies_file:
        args += ["--cookies", cookies_file]
    args += [url]

    proc = subprocess.Popen(
        args, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
        creationflags=NO_WINDOW_FLAGS, bufsize=1,
    )

    common_ids = None
    representative = {}
    count = 0
    try:
        for line in proc.stdout:
            line = line.strip()
            if not line:
                continue
            try:
                data = json.loads(line)
            except json.JSONDecodeError:
                continue
            count += 1
            entry_formats = [f for f in _parse_formats(data.get("formats", [])) if f.ext != "mhtml"]
            entry_ids = {f.format_id for f in entry_formats}
            if common_ids is None:
                common_ids = entry_ids
                representative = {f.format_id: f for f in entry_formats}
            else:
                common_ids &= entry_ids
            if on_progress:
                on_progress(count, data.get("title", ""))
    finally:
        stderr_text = proc.stderr.read()
        try:
            proc.wait(timeout=timeout)
        except subprocess.TimeoutExpired:
            proc.kill()
            raise RuntimeError("Timed out checking playlist formats")

    if count == 0:
        raise RuntimeError(stderr_text.strip() or "yt-dlp failed to fetch playlist formats")

    common_formats = [representative[fid] for fid in (common_ids or set())]
    return common_formats, count


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
