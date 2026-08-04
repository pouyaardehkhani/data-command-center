"""Estimates a sensible CRF/CQ starting point from the source file's own
bitrate, since an already-encoded file doesn't store the CRF it was made
with. The result is always shown as an editable 'Auto (estimated)' value.

Method: bits-per-pixel-per-frame (bpp) = bitrate / (width * height * fps).
Higher bpp (a high quality / lightly compressed source) maps to a lower
(higher quality) CRF; lower bpp maps to a higher CRF. Each codec family has
its own CRF/CQ scale, so the bpp bands are re-mapped per family below.
"""
from __future__ import annotations

from dcc.core.probe import MediaInfo

# (min_bpp, crf_for_x264-like_0_51_scale)
_BPP_BANDS = [
    (0.20, 18),
    (0.12, 20),
    (0.08, 23),
    (0.05, 26),
    (0.03, 29),
    (0.0, 32),
]

# Rescale the reference 0-51 (x264/x265) CRF into other codecs' native ranges.
_CODEC_RANGES = {
    "h264": (0, 51, 18, 28),      # libx264 crf
    "hevc": (0, 51, 20, 30),      # libx265 crf (slightly higher for equiv quality)
    "vp9": (0, 63, 24, 40),       # libvpx-vp9 crf
    "av1": (0, 63, 24, 40),       # libaom/svt-av1 crf
}

# NVENC/QSV/AMF use "CQ" on roughly a 0-51 scale similar to CRF.
_HW_CQ_RANGE = (0, 51, 19, 29)


def _bpp_to_reference_crf(bpp: float) -> int:
    for min_bpp, crf in _BPP_BANDS:
        if bpp >= min_bpp:
            return crf
    return 32


def estimate_crf(info: MediaInfo, codec: str, hardware: bool) -> int:
    """Returns a suggested CRF (software) or CQ (hardware) value for `codec`."""
    v = info.primary_video
    if not v or not v.width or not v.height:
        return 23 if not hardware else 23

    fps = v.fps or 30.0
    bitrate = v.bit_rate or info.format_bit_rate or 0
    if not bitrate:
        # No bitrate reported (e.g. some containers) - fall back to a
        # resolution-tiered default rather than a bpp computation.
        pixels = v.width * v.height
        if pixels >= 3840 * 2160:
            ref = 24
        elif pixels >= 1920 * 1080:
            ref = 22
        else:
            ref = 20
    else:
        bpp = bitrate / (v.width * v.height * fps)
        ref = _bpp_to_reference_crf(bpp)

    if hardware:
        lo_ref, hi_ref, lo, hi = _HW_CQ_RANGE
    else:
        lo_ref, hi_ref, lo, hi = _CODEC_RANGES.get(codec, _CODEC_RANGES["h264"])

    # linearly project the 0-51 reference crf into this codec/mode's practical range
    frac = ref / 32.0  # 32 is the worst band above
    frac = max(0.0, min(1.0, frac))
    value = lo + frac * (hi - lo)
    return int(round(value))
