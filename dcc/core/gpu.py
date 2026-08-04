"""GPU + hardware encoder detection.

Builds a capability matrix: which GPUs are present, and which ffmpeg hardware
encoders are realistically usable for each vendor. GPU-backed encoders are
always surfaced ahead of, and visually grouped separately from, CPU (software)
encoders in the UI.
"""
from __future__ import annotations

import re
import subprocess
from dataclasses import dataclass, field
from enum import Enum

from dcc.paths import NO_WINDOW_FLAGS, ffmpeg_path


class Vendor(str, Enum):
    NVIDIA = "NVIDIA"
    AMD = "AMD"
    INTEL = "Intel"
    CPU = "CPU"


# ffmpeg encoder name -> (vendor, codec family, human label)
HW_ENCODER_MAP = {
    "h264_nvenc": (Vendor.NVIDIA, "h264", "H.264 (NVIDIA NVENC)"),
    "hevc_nvenc": (Vendor.NVIDIA, "hevc", "H.265/HEVC (NVIDIA NVENC)"),
    "av1_nvenc": (Vendor.NVIDIA, "av1", "AV1 (NVIDIA NVENC)"),
    "h264_amf": (Vendor.AMD, "h264", "H.264 (AMD AMF)"),
    "hevc_amf": (Vendor.AMD, "hevc", "H.265/HEVC (AMD AMF)"),
    "av1_amf": (Vendor.AMD, "av1", "AV1 (AMD AMF)"),
    "h264_qsv": (Vendor.INTEL, "h264", "H.264 (Intel Quick Sync)"),
    "hevc_qsv": (Vendor.INTEL, "hevc", "H.265/HEVC (Intel Quick Sync)"),
    "av1_qsv": (Vendor.INTEL, "av1", "AV1 (Intel Quick Sync)"),
    "vp9_qsv": (Vendor.INTEL, "vp9", "VP9 (Intel Quick Sync)"),
}

# Software fallbacks always offered under the CPU group.
CPU_ENCODER_MAP = {
    "libx264": ("h264", "H.264 (x264, CPU)"),
    "libx265": ("hevc", "H.265/HEVC (x265, CPU)"),
    "libvpx-vp9": ("vp9", "VP9 (libvpx, CPU)"),
    "libaom-av1": ("av1", "AV1 (libaom, CPU)"),
    "libsvtav1": ("av1", "AV1 (SVT-AV1, CPU)"),
}


@dataclass
class Encoder:
    name: str
    codec: str
    label: str
    hardware: bool
    vendor: str = "CPU"


@dataclass
class GpuDevice:
    vendor: Vendor
    name: str


@dataclass
class Capabilities:
    gpus: list = field(default_factory=list)
    encoders: list = field(default_factory=list)

    def encoders_for_gpu(self, gpu_name: str | None) -> list:
        """Hardware encoders for the selected GPU first, then CPU encoders."""
        hw = [e for e in self.encoders if e.hardware and (gpu_name is None or e.vendor == gpu_name)]
        cpu = [e for e in self.encoders if not e.hardware]
        return hw + cpu

    def vendor_names(self) -> list:
        seen, out = set(), []
        for g in self.gpus:
            if g.vendor.value not in seen:
                seen.add(g.vendor.value)
                out.append(g.vendor.value)
        return out


def _list_ffmpeg_encoders() -> set:
    try:
        result = subprocess.run(
            [ffmpeg_path(), "-hide_banner", "-encoders"],
            capture_output=True, text=True, creationflags=NO_WINDOW_FLAGS, timeout=15,
        )
    except Exception:
        return set()
    names = set()
    for line in result.stdout.splitlines():
        m = re.match(r"^\s*[VAS][F.][S.][X.][B.][D.]\s+(\S+)\s", line)
        if m:
            names.add(m.group(1))
    return names


def _detect_gpus_powershell() -> list:
    devices = []
    try:
        result = subprocess.run(
            ["powershell", "-NoProfile", "-Command",
             "Get-CimInstance Win32_VideoController | Select-Object -ExpandProperty Name"],
            capture_output=True, text=True, creationflags=NO_WINDOW_FLAGS, timeout=15,
        )
        for line in result.stdout.splitlines():
            name = line.strip()
            if not name:
                continue
            low = name.lower()
            if "nvidia" in low:
                vendor = Vendor.NVIDIA
            elif "amd" in low or "radeon" in low or "advanced micro" in low:
                vendor = Vendor.AMD
            elif "intel" in low:
                vendor = Vendor.INTEL
            else:
                continue
            devices.append(GpuDevice(vendor=vendor, name=name))
    except Exception:
        pass
    return devices


def _detect_gpus_nvidia_smi() -> list:
    devices = []
    try:
        result = subprocess.run(
            ["nvidia-smi", "--query-gpu=name", "--format=csv,noheader"],
            capture_output=True, text=True, creationflags=NO_WINDOW_FLAGS, timeout=10,
        )
        for line in result.stdout.splitlines():
            name = line.strip()
            if name:
                devices.append(GpuDevice(vendor=Vendor.NVIDIA, name=name))
    except Exception:
        pass
    return devices


def detect_gpus() -> list:
    devices = _detect_gpus_powershell()
    if not any(d.vendor == Vendor.NVIDIA for d in devices):
        devices.extend(_detect_gpus_nvidia_smi())
    # de-dup by (vendor, name)
    seen, out = set(), []
    for d in devices:
        key = (d.vendor, d.name)
        if key not in seen:
            seen.add(key)
            out.append(d)
    return out


def detect_capabilities() -> Capabilities:
    gpus = detect_gpus()
    present_vendors = {g.vendor for g in gpus}
    available = _list_ffmpeg_encoders()

    encoders = []
    for name, (vendor, codec, label) in HW_ENCODER_MAP.items():
        if name in available and vendor in present_vendors:
            encoders.append(Encoder(name=name, codec=codec, label=label, hardware=True, vendor=vendor.value))
    for name, (codec, label) in CPU_ENCODER_MAP.items():
        if name in available:
            encoders.append(Encoder(name=name, codec=codec, label=label, hardware=False, vendor="CPU"))

    if not gpus:
        gpus = [GpuDevice(vendor=Vendor.CPU, name="No dedicated GPU detected")]

    return Capabilities(gpus=gpus, encoders=encoders)
