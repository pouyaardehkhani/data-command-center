"""ffprobe wrapper: reads a media file's real characteristics so every UI
field can default to 'the values of the file itself' instead of a guess."""
from __future__ import annotations

import json
import subprocess
from dataclasses import dataclass, field

from dcc.paths import NO_WINDOW_FLAGS, ffprobe_path


@dataclass
class StreamInfo:
    index: int
    codec_type: str  # "video" | "audio" | "subtitle"
    codec_name: str = ""
    width: int = 0
    height: int = 0
    fps: float = 0.0
    pix_fmt: str = ""
    bit_rate: int = 0
    sample_rate: int = 0
    channels: int = 0
    channel_layout: str = ""
    language: str = ""


@dataclass
class MediaInfo:
    path: str
    duration: float = 0.0
    format_name: str = ""
    format_bit_rate: int = 0
    streams: list = field(default_factory=list)

    @property
    def video_streams(self) -> list:
        return [s for s in self.streams if s.codec_type == "video"]

    @property
    def audio_streams(self) -> list:
        return [s for s in self.streams if s.codec_type == "audio"]

    @property
    def subtitle_streams(self) -> list:
        return [s for s in self.streams if s.codec_type == "subtitle"]

    @property
    def primary_video(self) -> StreamInfo | None:
        vs = self.video_streams
        return vs[0] if vs else None

    @property
    def primary_audio(self) -> StreamInfo | None:
        a = self.audio_streams
        return a[0] if a else None

    @property
    def is_image(self) -> bool:
        # single-frame "video" stream, no duration -> treat as still image
        return bool(self.video_streams) and not self.audio_streams and self.duration <= 0.04


def _parse_fps(rate_str: str) -> float:
    try:
        if "/" in rate_str:
            num, den = rate_str.split("/")
            den_f = float(den)
            return float(num) / den_f if den_f else 0.0
        return float(rate_str)
    except (ValueError, ZeroDivisionError):
        return 0.0


def probe(path: str) -> MediaInfo:
    args = [
        ffprobe_path(),
        "-v", "quiet",
        "-print_format", "json",
        "-show_format",
        "-show_streams",
        path,
    ]
    result = subprocess.run(
        args, capture_output=True, text=True, creationflags=NO_WINDOW_FLAGS, timeout=30
    )
    data = json.loads(result.stdout or "{}")

    fmt = data.get("format", {})
    info = MediaInfo(
        path=path,
        duration=float(fmt.get("duration", 0.0) or 0.0),
        format_name=fmt.get("format_name", ""),
        format_bit_rate=int(fmt.get("bit_rate", 0) or 0),
    )

    for s in data.get("streams", []):
        stream = StreamInfo(
            index=s.get("index", 0),
            codec_type=s.get("codec_type", ""),
            codec_name=s.get("codec_name", ""),
            width=s.get("width", 0) or 0,
            height=s.get("height", 0) or 0,
            fps=_parse_fps(s.get("avg_frame_rate", "0/0") or s.get("r_frame_rate", "0/0")),
            pix_fmt=s.get("pix_fmt", ""),
            bit_rate=int(s.get("bit_rate", 0) or 0),
            sample_rate=int(s.get("sample_rate", 0) or 0),
            channels=s.get("channels", 0) or 0,
            channel_layout=s.get("channel_layout", ""),
            language=(s.get("tags", {}) or {}).get("language", ""),
        )
        info.streams.append(stream)

    return info


def probe_safe(path: str) -> MediaInfo | None:
    try:
        return probe(path)
    except Exception:
        return None
