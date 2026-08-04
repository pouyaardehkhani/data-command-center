"""Translates the UI option dataclasses into ffmpeg/yt-dlp argument lists.
Every function here is a pure function: (paths, MediaInfo, options) -> list[str].
No process spawning happens in this module - that's job_queue's job.
"""
from __future__ import annotations

from dcc.core.crf_heuristic import estimate_crf
from dcc.core.options import (
    AudioOptions, CropOptions, FrameExportOptions, ImageOptions,
    SubtitleOptions, VideoOptions,
)
from dcc.core.probe import MediaInfo
from dcc.paths import ffmpeg_path

RESOLUTION_PRESETS = {
    "8K UHD (7680×4320)": (7680, 4320),
    "4K UHD (3840×2160)": (3840, 2160),
    "4K DCI (4096×2160)": (4096, 2160),
    "1440p QHD (2560×1440)": (2560, 1440),
    "1080p Full HD (1920×1080)": (1920, 1080),
    "720p HD (1280×720)": (1280, 720),
    "480p SD (854×480)": (854, 480),
    "480p (4:3) (640×480)": (640, 480),
    "360p (640×360)": (640, 360),
    "240p (426×240)": (426, 240),
    "UWQHD 21:9 (3440×1440)": (3440, 1440),
    "UWHD 21:9 (2560×1080)": (2560, 1080),
    "Vertical 1080×1920 (1080×1920)": (1080, 1920),
    "Square 1080×1080 (1080×1080)": (1080, 1080),
}

FPS_PRESETS = [23.976, 24, 25, 29.97, 30, 48, 50, 59.94, 60, 120]

# One standardized bitrate preset list, used everywhere a bitrate preset is
# offered (video bitrate, audio bitrate). "Default" always means "use the
# source file's own bitrate" for video, or "let the codec pick" for audio.
BITRATE_PRESET_LABELS = [
    "Default", "256K", "384K", "512K", "768K",
    "1M", "1.5M", "2M", "5M", "10M", "15M", "20M",
]

SAMPLE_RATE_PRESETS = [8000, 16000, 22050, 32000, 44100, 48000, 96000]


def parse_bitrate_label(text: str) -> int:
    """'256K' -> 256, '1.5M' -> 1500, 'Default'/'Source'/'' -> 0 (auto)."""
    text = (text or "").strip()
    if not text or text.lower() in ("default", "source", "auto"):
        return 0
    upper = text.upper()
    try:
        if upper.endswith("M"):
            return int(round(float(upper[:-1]) * 1000))
        if upper.endswith("K"):
            return int(round(float(upper[:-1])))
        return int(round(float(upper)))
    except ValueError:
        return 0


def format_bitrate_kbps(kbps: int) -> str:
    """Reverse of parse_bitrate_label, for restoring presets into the combo."""
    if kbps <= 0:
        return "Default"
    for label in BITRATE_PRESET_LABELS[1:]:
        if parse_bitrate_label(label) == kbps:
            return label
    return str(kbps)

FILTER_PRESET_CHOICES = ["None", "Grayscale", "Sepia", "Vintage", "Sharpen", "Blur", "Vignette"]

AUDIO_ENCODER_CHOICES = {
    "aac": "AAC",
    "libmp3lame": "MP3",
    "ac3": "Dolby AC3",
    "flac": "FLAC (lossless)",
    "libopus": "Opus",
    "pcm_s16le": "PCM (uncompressed, WAV)",
    "copy": "Copy source (no re-encode)",
}

VIDEO_CONTAINER_CHOICES = ["mp4", "mkv", "avi", "mov", "webm", "flv", "ts", "wmv"]
AUDIO_CONTAINER_CHOICES = ["mp3", "aac", "flac", "wav", "ogg", "m4a", "wma"]
IMAGE_CONTAINER_CHOICES = ["png", "jpg", "webp", "bmp", "tiff", "gif"]


def _fmt(v: float) -> str:
    return f"{v:g}"


# ---------------------------------------------------------------------------
# Filter chain builders
# ---------------------------------------------------------------------------

def _rotate_filter(deg: int) -> str | None:
    return {90: "transpose=1", 180: "hflip,vflip", 270: "transpose=2"}.get(deg)


def _color_filter(preset: str) -> str | None:
    return {
        "Grayscale": "hue=s=0",
        "Sepia": "colorchannelmixer=.393:.769:.189:0:.349:.686:.168:0:.272:.534:.131",
        "Vintage": "curves=vintage,vignette=PI/5",
        "Sharpen": "unsharp=5:5:1.2:5:5:0.0",
        "Blur": "gblur=sigma=3",
        "Vignette": "vignette=PI/5",
    }.get(preset)


def _unsharp_for_sharpness(sharpness: int) -> str | None:
    if sharpness == 0:
        return None
    amount = max(-2.0, min(2.0, sharpness * 0.4))
    return f"unsharp=5:5:{amount:.2f}:5:5:0.0"


def build_video_filters(opts: VideoOptions, info: MediaInfo, crop: CropOptions | None = None) -> str:
    chain: list[str] = []

    if opts.reverse:
        chain.append("reverse")
    if opts.anti_shake:
        chain.append("deshake")
    if opts.deinterlace:
        chain.append("yadif")
    if crop and crop.width and crop.height:
        chain.append(f"crop={crop.width}:{crop.height}:{crop.x}:{crop.y}")

    width, height = _resolve_resolution(opts, info)
    if width and height:
        chain.append(f"scale={width}:{height}")
        chain.append("setsar=1")

    dar = _resolve_aspect_ratio(opts)
    if dar:
        chain.append(f"setdar={dar}")

    if opts.fps:
        chain.append(f"fps={_fmt(opts.fps)}")

    rot = _rotate_filter(opts.rotate_deg)
    if rot:
        chain.append(rot)
    if opts.mirror_x:
        chain.append("hflip")
    if opts.mirror_y:
        chain.append("vflip")

    if opts.denoise:
        chain.append("hqdn3d")

    unsharp = _unsharp_for_sharpness(opts.sharpness)
    if unsharp:
        chain.append(unsharp)

    color = _color_filter(opts.filter_preset)
    if color:
        chain.append(color)

    if opts.film_grain > 0:
        strength = min(50, opts.film_grain)
        chain.append(f"noise=alls={strength}:allf=t+u")

    if opts.fade_in_sec > 0:
        chain.append(f"fade=t=in:st=0:d={_fmt(opts.fade_in_sec)}")
    if opts.fade_out_sec > 0 and info.duration > 0:
        start = max(0.0, info.duration - opts.fade_out_sec)
        chain.append(f"fade=t=out:st={_fmt(start)}:d={_fmt(opts.fade_out_sec)}")

    return ",".join(chain)


def build_audio_filters(opts: AudioOptions, duration: float) -> str:
    chain: list[str] = []
    if opts.reverse:
        chain.append("areverse")
    if opts.denoise:
        chain.append("afftdn")
    if opts.echo:
        chain.append("aecho=0.8:0.9:1000:0.3")
    if opts.volume_percent != 100:
        chain.append(f"volume={opts.volume_percent / 100.0:.2f}")
    if opts.fade_in_sec > 0:
        chain.append(f"afade=t=in:st=0:d={_fmt(opts.fade_in_sec)}")
    if opts.fade_out_sec > 0 and duration > 0:
        start = max(0.0, duration - opts.fade_out_sec)
        chain.append(f"afade=t=out:st={_fmt(start)}:d={_fmt(opts.fade_out_sec)}")
    return ",".join(chain)


def _resolve_aspect_ratio(opts: VideoOptions) -> str | None:
    if opts.aspect_ratio == "Source":
        return None
    ratio = opts.aspect_custom if opts.aspect_ratio == "Custom" else opts.aspect_ratio
    ratio = (ratio or "").replace("x", ":").strip()
    if ":" not in ratio:
        return None
    return ratio


def _resolve_resolution(opts: VideoOptions, info: MediaInfo) -> tuple:
    if opts.resolution_preset == "Source":
        return 0, 0
    if opts.resolution_preset == "Custom":
        return opts.width, opts.height
    return RESOLUTION_PRESETS.get(opts.resolution_preset, (0, 0))


# ---------------------------------------------------------------------------
# Rate control / codec args
# ---------------------------------------------------------------------------

def video_codec_args(opts: VideoOptions, info: MediaInfo) -> list:
    if not opts.encoder:
        return []
    args = ["-c:v", opts.encoder]
    hardware = opts.encoder.endswith(("_nvenc", "_amf", "_qsv"))

    if opts.rate_control == "bitrate":
        bitrate = opts.bitrate_kbps if opts.bitrate_kbps > 0 else _source_bitrate_kbps(info)
        args += ["-b:v", f"{bitrate}k"]
        if opts.encoder.endswith("_nvenc"):
            args += ["-rc:v", "vbr"]
    else:
        crf = opts.crf if opts.crf > 0 else estimate_crf(info, _codec_family(opts.encoder), hardware)
        if opts.encoder.endswith("_nvenc"):
            args += ["-rc:v", "vbr", "-cq:v", str(crf), "-b:v", "0"]
        elif opts.encoder.endswith("_qsv"):
            args += ["-global_quality:v", str(crf)]
        elif opts.encoder.endswith("_amf"):
            args += ["-rc", "cqp", "-qp_i", str(crf), "-qp_p", str(crf), "-qp_b", str(crf)]
        else:
            args += ["-crf", str(crf)]

    if opts.keyframe_interval_sec > 0:
        fps = opts.fps or (info.primary_video.fps if info.primary_video else 30) or 30
        gop = max(1, round(fps * opts.keyframe_interval_sec))
        args += ["-g", str(gop)]
        if not hardware:
            args += ["-sc_threshold", "0"]

    pix_fmt = opts.pixel_format or (info.primary_video.pix_fmt if info.primary_video else "")
    if pix_fmt:
        args += ["-pix_fmt", pix_fmt]

    return args


def _source_bitrate_kbps(info: MediaInfo) -> int:
    v = info.primary_video
    raw = (v.bit_rate if v and v.bit_rate else 0) or info.format_bit_rate or 0
    return max(1, raw // 1000) if raw else 2000


def _codec_family(encoder: str) -> str:
    if "264" in encoder:
        return "h264"
    if "265" in encoder or "hevc" in encoder:
        return "hevc"
    if "vp9" in encoder:
        return "vp9"
    if "av1" in encoder:
        return "av1"
    return "h264"


def audio_codec_args(opts: AudioOptions) -> list:
    if opts.disable_audio:
        return ["-an"]
    args = ["-c:a", opts.encoder]
    if opts.encoder != "copy":
        if opts.bitrate_kbps > 0 and opts.encoder != "pcm_s16le" and opts.encoder != "flac":
            args += ["-b:a", f"{opts.bitrate_kbps}k"]
        if opts.sample_rate > 0:
            args += ["-ar", str(opts.sample_rate)]
        if opts.channels > 0:
            args += ["-ac", str(opts.channels)]
    return args


def stream_map_args(opts: AudioOptions, has_video: bool) -> list:
    args = []
    if has_video:
        args += ["-map", "0:v:0"]
    if not opts.disable_audio:
        args += ["-map", "0:a" if opts.keep_all_streams else "0:a:0?"]
    return args


# ---------------------------------------------------------------------------
# Feature command builders
# ---------------------------------------------------------------------------

def build_video_convert_args(input_path: str, output_path: str, info: MediaInfo, opts: VideoOptions) -> list:
    args = [ffmpeg_path(), "-y", "-i", input_path]

    vf = build_video_filters(opts, info)
    af = build_audio_filters(opts.audio, info.duration)

    args += stream_map_args(opts.audio, has_video=True)
    if vf:
        args += ["-vf", vf]
    args += video_codec_args(opts, info)
    if af:
        args += ["-af", af]
    args += audio_codec_args(opts.audio)

    args += ["-progress", "pipe:1", "-nostats", output_path]
    return args


def build_audio_convert_args(input_path: str, output_path: str, info: MediaInfo, opts: AudioOptions) -> list:
    args = [ffmpeg_path(), "-y", "-i", input_path, "-vn"]
    af = build_audio_filters(opts, info.duration)
    if af:
        args += ["-af", af]
    args += audio_codec_args(opts)
    if opts.keep_all_streams:
        args += ["-map", "0:a"]
    args += ["-progress", "pipe:1", "-nostats", output_path]
    return args


def build_subtitle_args(video_path: str, subtitle_path: str, output_path: str, opts: SubtitleOptions) -> list:
    args = [ffmpeg_path(), "-y", "-i", video_path]
    if opts.mode == "hard":
        escaped = subtitle_path.replace("\\", "/").replace(":", "\\:")
        style = f"FontSize={opts.font_size},PrimaryColour=&H{_color_to_ass_hex(opts.font_color)}&"
        args += ["-vf", f"subtitles='{escaped}':force_style='{style}'"]
        args += ["-c:a", "copy"]
    else:
        args += ["-i", subtitle_path, "-map", "0", "-map", "1", "-c", "copy", "-c:s", "mov_text"]
    args += ["-progress", "pipe:1", "-nostats", output_path]
    return args


def _color_to_ass_hex(name: str) -> str:
    table = {"white": "FFFFFF", "black": "000000", "yellow": "00FFFF", "red": "0000FF"}
    return table.get(name.lower(), "FFFFFF")


def build_merge_args(input_paths: list, output_path: str) -> list:
    args = [ffmpeg_path(), "-y"]
    for p in input_paths:
        args += ["-i", p]
    n = len(input_paths)
    filter_inputs = "".join(f"[{i}:v:0][{i}:a:0]" for i in range(n))
    args += ["-filter_complex", f"{filter_inputs}concat=n={n}:v=1:a=1[outv][outa]",
              "-map", "[outv]", "-map", "[outa]"]
    args += ["-progress", "pipe:1", "-nostats", output_path]
    return args


def build_split_args(input_path: str, video_output: str, audio_output: str) -> list:
    return [
        ffmpeg_path(), "-y", "-i", input_path,
        "-map", "0:v:0", "-c", "copy", video_output,
        "-map", "0:a:0", "-c", "copy", audio_output,
        "-progress", "pipe:1", "-nostats",
    ]


def build_crop_args(input_path: str, output_path: str, info: MediaInfo, crop: CropOptions) -> list:
    args = [ffmpeg_path(), "-y", "-i", input_path]
    vf = f"crop={crop.width}:{crop.height}:{crop.x}:{crop.y}"
    args += ["-vf", vf, "-c:v", crop.encoder]
    hardware = crop.encoder.endswith(("_nvenc", "_amf", "_qsv"))
    crf = estimate_crf(info, _codec_family(crop.encoder), hardware)
    args += ["-crf", str(crf)] if not hardware else ["-cq:v", str(crf)]
    args += ["-c:a", "copy", "-progress", "pipe:1", "-nostats", output_path]
    return args


def build_frame_export_args(input_path: str, output_dir: str, opts: FrameExportOptions) -> list:
    pattern = f"{output_dir}/frame_%04d.{opts.image_format}"
    args = [ffmpeg_path(), "-y"]

    if opts.mode == "range" and opts.end_sec > opts.start_sec:
        args += ["-ss", _fmt(opts.start_sec), "-to", _fmt(opts.end_sec)]
    elif opts.mode == "interval" and opts.start_sec:
        args += ["-ss", _fmt(opts.start_sec)]

    args += ["-i", input_path]

    vf_parts = []
    if opts.mode == "interval" and opts.interval_sec > 0:
        vf_parts.append(f"fps=1/{_fmt(opts.interval_sec)}")
    if opts.width and opts.height:
        vf_parts.append(f"scale={opts.width}:{opts.height}")
    if vf_parts:
        args += ["-vf", ",".join(vf_parts)]

    if opts.mode == "count" and opts.frame_count > 0:
        args += ["-frames:v", str(opts.frame_count)]

    if opts.image_format == "jpg":
        args += ["-q:v", "2"]

    args += ["-progress", "pipe:1", "-nostats", pattern]
    return args


def build_image_convert_args(input_path: str, output_path: str, opts: ImageOptions) -> list:
    args = [ffmpeg_path(), "-y", "-i", input_path]
    if opts.width and opts.height:
        args += ["-vf", f"scale={opts.width}:{opts.height}"]
    if opts.format in ("jpg", "jpeg", "webp"):
        args += ["-q:v", str(max(2, round((100 - opts.quality) / 3)))]
    args += [output_path]
    return args


def build_audio_mix_args(input_paths: list, volumes_percent: list, output_path: str) -> list:
    args = [ffmpeg_path(), "-y"]
    for p in input_paths:
        args += ["-i", p]
    n = len(input_paths)
    streams = []
    for i, vol in enumerate(volumes_percent):
        streams.append(f"[{i}:a]volume={vol / 100.0:.2f}[a{i}]")
    joined_inputs = "".join(f"[a{i}]" for i in range(n))
    filter_complex = ";".join(streams) + f";{joined_inputs}amix=inputs={n}:duration=longest[out]"
    args += ["-filter_complex", filter_complex, "-map", "[out]"]
    args += ["-progress", "pipe:1", "-nostats", output_path]
    return args


def build_audio_join_args(input_paths: list, output_path: str) -> list:
    args = [ffmpeg_path(), "-y"]
    for p in input_paths:
        args += ["-i", p]
    n = len(input_paths)
    filter_inputs = "".join(f"[{i}:a:0]" for i in range(n))
    args += ["-filter_complex", f"{filter_inputs}concat=n={n}:v=0:a=1[out]", "-map", "[out]"]
    args += ["-progress", "pipe:1", "-nostats", output_path]
    return args
