# Data Command Center

A Format Factory–style media toolbox for Windows: convert, edit, and download video, audio, and images with GPU-accelerated encoding, batch processing, presets, and a dark/light UI — all built on **ffmpeg** and **yt-dlp**.

## Features

### Video
- **Converter** — batch conversion to any container/codec, processed sequentially. Full control over encoder, rate control (Auto / CRF-CQ / Bitrate), resolution (14 presets incl. 8K, 21:9 ultrawide, vertical/square), FPS, aspect ratio, keyframe interval, deinterlace, rotate, mirror, filters, fade in/out, anti-shake, denoise, reverse, sharpness, film grain, and pixel format — plus a matching audio-track panel (encoder, sample rate, bitrate, channels, volume, fades, echo, denoise, reverse, stream selection).
- **Add Subtitle** — soft-mux (toggleable track) or hard-burn (rendered into the picture).
- **Merger** — joins multiple videos into one file.
- **Splitter** — extracts the video-only and audio-only tracks from a file.
- **Crop** — cut a rectangular region out of the frame.
- **Export Frames** — pull stills out of a video by interval, count, or time range.
- **YouTube Downloader** — powered by `yt-dlp.exe`: independent video/audio quality pickers (with file size shown per option) that yt-dlp merges automatically, MP4 preference, playlist support with item ranges, a download archive to skip re-downloads, cookie-file auth for restricted videos, and a one-click yt-dlp self-updater.

### Audio
- **Converter** — encoder, sample rate, bitrate, channels, volume, fades, echo, denoise, reverse, multi-stream handling.
- **Mixer** — blends multiple tracks together with per-track volume.
- **Joiner** — concatenates multiple tracks into one.

### Picture
- **Converter** — format conversion with resolution control.

### Platform
- **GPU-first encoding** — auto-detects every GPU in the system (NVIDIA/AMD/Intel) and lists its hardware encoders (NVENC/AMF/QuickSync) ahead of, and visually distinct from, CPU encoders.
- **Presets** — save/load/delete named setting profiles on every feature page.
- **Contextual help** — a (?) icon next to every setting, plus a searchable Help page.
- **Dark / light theme**, switchable at runtime.
- **Sequential job queue** — batches process one file at a time with live progress, cancel, and clear.

## Requirements

- Windows 10/11
- `bin/yt-dlp.exe` is included in this repo. `bin/ffmpeg.exe` and `bin/ffprobe.exe` are **not** (they're ~211MB each, over GitHub's 100MB file limit) — see Setup below.

## Setup

1. Download a Windows ffmpeg build that includes `ffprobe.exe` — e.g. the ["full" build from gyan.dev](https://www.gyan.dev/ffmpeg/builds/) (this project was built/tested against that one).
2. Copy `ffmpeg.exe` and `ffprobe.exe` from its `bin/` folder into this repo's `bin/` folder, alongside the already-included `yt-dlp.exe`.

```powershell
python -m venv .venv
.venv\Scripts\pip install -r requirements.txt
.venv\Scripts\python -m dcc.main
```

## Building the distributable

```powershell
.\build.ps1
```

This runs PyInstaller (see `DataCommandCenter.spec`) and produces a onedir build at:

```
dist\Data Command Center\DataCommandCenter.exe
```

That folder is the whole installed program — copy it anywhere (e.g. `Program Files`) to "install" it.

## Project structure

```
dcc/
  core/                   # engine: no UI code, all pure/testable
    probe.py              # ffprobe wrapper -> MediaInfo (source defaults)
    gpu.py                # GPU + hardware encoder detection
    crf_heuristic.py       # auto CRF/CQ estimation from source bitrate
    command_builder.py     # UI options -> ffmpeg argument lists
    job_queue.py           # sequential ffmpeg/yt-dlp process runner
    ytdlp.py               # yt-dlp wrapper (info fetch, download args)
    options.py             # settings dataclasses (also the preset schema)
    presets.py             # save/load/delete presets
    settings.py            # persistent app settings (QSettings)
  ui/
    main_window.py         # sidebar nav + stacked pages + job queue dock
    theme.py                # dark/light QSS
    help_text.py            # copy shown by (?) buttons and the Help page
    widgets/                 # shared, reusable controls (see below)
    pages/
      video/                  # Converter, Subtitle, Merger, Splitter, Crop,
                               # Frame Export, YouTube Downloader
      audio/                  # Converter, Mixer, Joiner
      picture/                # Converter
      settings_page.py, help_page.py
  main.py                   # entry point
bin/                          # bundled ffmpeg.exe, ffprobe.exe, yt-dlp.exe
run_app.py                    # PyInstaller entry point
DataCommandCenter.spec        # PyInstaller build spec
build.ps1                     # build script
```

`dcc/ui/widgets/` holds the shared input primitives every page is built from — `NoWheelComboBox`/`NoWheelSpinBox`/`NoWheelDoubleSpinBox`/`NoWheelSlider` (consistent sizing, and scroll-wheel only changes a value once it's focused), `DurationSpinBox`, `EncoderSelector`/`GpuSelector` (GPU-first grouping), `FileBatchList`, `PresetBar`, `HelpButton`, `OutputBar`, and `QueuePanel`. New pages should compose from these rather than raw Qt widgets, so fixes and consistency apply app-wide.

## Tech stack

- **PySide6** (Qt6) for the UI, styled with custom QSS (dark/light)
- **qtawesome** for icons
- **ffmpeg / ffprobe** for all media processing
- **yt-dlp** for video downloading
- **PyInstaller** for packaging

## License & acknowledgments

This project's own code has no license file yet — add one (MIT/Apache-2.0/etc.) before distributing publicly.

Bundled third-party binaries keep their own licenses:
- `ffmpeg.exe` / `ffprobe.exe` — GPL-licensed (build info and license text included at `bin/FFMPEG_LICENSE.txt`); redistributing them means this project must comply with the GPL for those binaries.
- `yt-dlp.exe` — [Unlicense](https://github.com/yt-dlp/yt-dlp/blob/master/LICENSE).
- PySide6/Qt — LGPL v3.
- qtawesome — includes Font Awesome and other icon sets under their respective open licenses.

## Known limitations

- No custom app icon yet (uses PyInstaller's default).
- AMD AMF encoder arguments follow ffmpeg's documented flags but are untested on real AMD hardware.
