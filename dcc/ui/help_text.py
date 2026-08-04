"""Central help copy shown by HelpButton popovers and the Help page.
Keys are free-form ids referenced from the pages that use them."""

HELP = {
    # --- Video Converter: video track ---
    "video.encoder": "The video codec used to re-encode your file. Hardware (GPU) encoders are listed first and are much faster; software (CPU) encoders are usually a bit more efficient at the same file size but slower.",
    "video.gpu": "Choose which GPU should run hardware encoding. Detected automatically from your system. Choosing a GPU filters the encoder list to the codecs that GPU actually supports.",
    "video.rate_control": "Chooses which field below actually controls quality/size - only one is ever active. Auto: quality is estimated from the source file automatically, both fields below are disabled. CRF/CQ (manual): you set the quality target directly, bitrate is disabled. Bitrate (CBR/VBR): you set a target data rate directly, CRF/CQ is disabled.",
    "video.crf": "Constant Quality value. Lower = higher quality & bigger file. Only active in CRF/CQ (manual) mode.",
    "video.bitrate": "Target average data rate for the video stream. 'Default' uses the source file's own bitrate. Only active in Bitrate (CBR/VBR) mode.",
    "video.resolution": "Output frame size. 'Source' keeps the original resolution. Presets scale proportionally; use Custom for an exact width/height.",
    "video.fps": "Output frame rate. 'Source' keeps the original. Changing this can smooth or reduce motion and affects file size.",
    "video.aspect_ratio": "The width:height ratio of the output frame. 'Source' keeps the original ratio.",
    "video.keyframe_interval": "How often (in seconds) a full reference frame is inserted. Shorter intervals seek more precisely and stream more reliably, but increase file size.",
    "video.deinterlace": "Converts interlaced footage (common from TV capture/DVD) into progressive frames, removing combing artifacts.",
    "video.rotate": "Rotates the output frame by the chosen number of degrees.",
    "video.mirror_x": "Flips the video horizontally (left/right mirror).",
    "video.mirror_y": "Flips the video vertically (upside down).",
    "video.filter": "A one-click visual look applied to the whole video.",
    "video.fade_in": "Fades in from black over this many seconds at the start.",
    "video.fade_out": "Fades out to black over this many seconds at the end.",
    "video.anti_shake": "Reduces handheld camera shake using frame-to-frame stabilization. Can soften fast motion slightly.",
    "video.denoise": "Reduces sensor/grain noise. Good for low-light or old, noisy source footage.",
    "video.reverse": "Plays the clip backwards. Requires decoding the whole clip into memory, so it can be slow for long videos.",
    "video.sharpness": "Increases or decreases perceived detail/edge contrast. 0 leaves the source untouched.",
    "video.film_grain": "Adds synthetic film grain, from subtle (low) to heavy (high). 0 disables it.",
    "video.pixel_format": "The internal color sampling/bit depth ffmpeg encodes with (e.g. yuv420p = standard 8-bit, yuv420p10le = 10-bit). Auto-detected from the source; only change this if you know your target device/codec needs a specific format.",

    # --- Audio track (shared by Video Converter + Audio Converter) ---
    "audio.encoder": "The audio codec used to re-encode the audio track. 'Copy source' keeps the original audio untouched (fastest, no quality loss).",
    "audio.sample_rate": "Audio samples per second (Hz). 48000 is standard for video, 44100 for music. Higher isn't always better - it should match your source.",
    "audio.bitrate": "Audio data rate. Higher = better quality & bigger file. 'Default' lets the codec pick its own bitrate (usually ~128 kb/s). 128K-192K is typical for good quality speech/music.",
    "audio.channels": "Number of output audio channels: mono, stereo, 5.1 surround, etc. 'Source' keeps the original layout.",
    "audio.disable": "Removes audio entirely from the output.",
    "audio.volume": "Scales the audio loudness. 100% = unchanged, 200% = doubled (may clip/distort), 50% = half volume.",
    "audio.keep_all_streams": "Keeps every audio track from the source (e.g. multiple languages) instead of only the first one.",
    "audio.fade_in": "Fades audio in from silence over this many seconds.",
    "audio.fade_out": "Fades audio out to silence over this many seconds.",
    "audio.echo": "Adds an echo/reverb effect to the audio.",
    "audio.denoise": "Reduces background hiss/hum using noise reduction.",
    "audio.reverse": "Plays the audio backwards.",

    # --- Subtitle ---
    "subtitle.mode": "Soft = the subtitle stays a separate, toggleable track inside the file (no re-encode, works on mp4/mkv). Hard = the subtitle is permanently drawn into the video image (works everywhere, but can't be turned off and requires re-encoding).",

    # --- Merger / Splitter / Crop / Frames ---
    "merger.info": "Joins two or more videos, one after another, into a single output file, in the order shown in the list.",
    "splitter.info": "Extracts the video-only and audio-only tracks from a source file into two separate output files.",
    "crop.info": "Cuts out a rectangular region of the frame. X/Y is the top-left corner of the region, in pixels.",
    "frames.mode": "Interval: one frame every N seconds. Count: a fixed number of evenly-spaced frames. Range: every frame between a start and end time.",

    # --- YouTube downloader ---
    "youtube.url": "Paste a YouTube (or any yt-dlp supported site) video or playlist URL, then click Fetch Info.",
    "youtube.format": "Choose the video stream's quality/format. Video and audio quality are picked separately (as most sites publish them as separate video-only and audio-only streams at the highest qualities) - yt-dlp downloads both and merges them into one file automatically.",
    "youtube.audio_format": "Choose the audio stream's quality/format, merged together with the selected video stream. Disabled when the site only offers combined video+audio streams (the audio is already included then), or when 'Audio only (MP3)' is checked.",
    "youtube.audio_only": "Downloads and extracts just the audio track as an MP3, instead of the video.",
    "youtube.prefer_mp4": "When both quality dropdowns are left on 'Best available', prefers an MP4 video + M4A audio pair for maximum device/player compatibility, falling back to the best combination available if MP4/M4A isn't offered.",
    "youtube.archive": "Keeps a small 'downloaded.txt' record in the output folder so already-downloaded videos are skipped automatically next time - useful for re-running a playlist without re-downloading everything.",
    "youtube.playlist_items": "Only active when 'Download entire playlist' is checked. Limits which playlist entries to download, e.g. '5:20' for items 5 through 20, or '1,3,5-7' for a specific set. Leave blank to download all items.",
    "youtube.cookies": "Sends your browser's cookies (exported to a Netscape-format cookies.txt file) with every yt-dlp command, including Fetch Info - needed for age-restricted, members-only, or 'sign in to confirm you're not a bot' videos. Applies to both this and every download until switched off.",

    # --- Audio Mixer / Joiner ---
    "mixer.info": "Combines multiple audio files so they play simultaneously, blended into one track. Adjust each track's relative volume before mixing.",
    "joiner.info": "Joins multiple audio files one after another into a single continuous track.",

    # --- Picture ---
    "picture.resolution": "Resize the image. Leave at 0x0 (Source) to keep the original size.",

    # --- GPU / general ---
    "gpu.priority": "Data Command Center always prefers your GPU for encoding when a hardware encoder for the chosen codec is available - it's typically 5-20x faster than CPU encoding. CPU (software) codecs remain available as a distinctly-labeled fallback for maximum compatibility or quality.",
}


def help_for(key: str) -> str:
    return HELP.get(key, "No additional help is available for this setting yet.")
