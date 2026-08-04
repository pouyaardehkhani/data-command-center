"""Settings dataclasses shared by the UI pages, the command builder, and the
preset system (these are exactly what gets serialized to a preset JSON file)."""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class AudioOptions:
    encoder: str = "aac"          # aac, libmp3lame, ac3, flac, libopus, pcm_s16le, copy
    sample_rate: int = 0          # 0 = source
    bitrate_kbps: int = 0         # 0 = source/auto
    channels: int = 0             # 0 = source, 1=mono, 2=stereo, 6=5.1, 8=7.1
    disable_audio: bool = False
    volume_percent: int = 100
    keep_all_streams: bool = False
    fade_in_sec: float = 0.0
    fade_out_sec: float = 0.0
    echo: bool = False
    denoise: bool = False
    reverse: bool = False


@dataclass
class VideoOptions:
    encoder: str = ""              # e.g. libx264 / h264_nvenc, resolved by the UI from Capabilities
    gpu_vendor: str = ""           # "", "NVIDIA", "AMD", "Intel", "CPU"
    rate_control: str = "crf"      # "crf" | "bitrate"
    crf: int = 0                   # 0 = auto-estimated
    bitrate_kbps: int = 0          # used when rate_control == "bitrate"; predefined or custom
    resolution_preset: str = "Source"  # Source/4K/1080p/720p/480p/360p/Custom
    width: int = 0                 # used when resolution_preset == "Custom" (0 = source)
    height: int = 0
    fps: float = 0.0               # 0 = source
    aspect_ratio: str = "Source"   # Source/16:9/4:3/1:1/9:16/Custom
    aspect_custom: str = ""        # "W:H" when aspect_ratio == "Custom"
    keyframe_interval_sec: float = 2.0
    deinterlace: bool = False
    rotate_deg: int = 0            # 0/90/180/270
    mirror_x: bool = False
    mirror_y: bool = False
    filter_preset: str = "None"    # None/Grayscale/Sepia/Vintage/Sharpen/Blur/Vignette
    fade_in_sec: float = 0.0
    fade_out_sec: float = 0.0
    anti_shake: bool = False
    denoise: bool = False
    reverse: bool = False
    sharpness: int = 0             # -5..5
    film_grain: int = 0            # 0..50
    pixel_format: str = ""         # "" = source/auto

    audio: AudioOptions = field(default_factory=AudioOptions)


@dataclass
class SubtitleOptions:
    mode: str = "soft"              # "soft" (mux) | "hard" (burn-in)
    font_size: int = 24
    font_color: str = "white"


@dataclass
class CropOptions:
    x: int = 0
    y: int = 0
    width: int = 0
    height: int = 0
    encoder: str = "libx264"


@dataclass
class FrameExportOptions:
    mode: str = "interval"          # "interval" | "count" | "range"
    interval_sec: float = 1.0
    frame_count: int = 10
    start_sec: float = 0.0
    end_sec: float = 0.0
    image_format: str = "png"       # png | jpg
    width: int = 0                  # 0 = source
    height: int = 0


@dataclass
class ImageOptions:
    format: str = "png"
    width: int = 0                  # 0 = source
    height: int = 0
    quality: int = 90               # jpg/webp quality 1-100
