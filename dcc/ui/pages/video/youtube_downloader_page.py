from PySide6.QtCore import QThread, Signal
from PySide6.QtWidgets import (
    QCheckBox, QFileDialog, QHBoxLayout, QLabel, QLineEdit, QMessageBox,
    QPushButton, QVBoxLayout, QWidget,
)

from dcc.app_context import AppContext
from dcc.core import settings as app_settings
from dcc.core import ytdlp
from dcc.core.job_queue import Job
from dcc.ui.widgets.help_button import HelpButton
from dcc.ui.widgets.inputs import NoWheelComboBox
from dcc.ui.widgets.output_bar import OutputBar


class _FetchThread(QThread):
    done = Signal(object, str)

    def __init__(self, url: str, cookies_file: str = "", parent=None):
        super().__init__(parent)
        self._url = url
        self._cookies_file = cookies_file

    def run(self):
        try:
            info = ytdlp.fetch_info(self._url, cookies_file=self._cookies_file)
            self.done.emit(info, "")
        except Exception as e:
            self.done.emit(None, str(e))


class _UpdateThread(QThread):
    done = Signal(bool, str)

    def run(self):
        success, message = ytdlp.update_ytdlp()
        self.done.emit(success, message)


def _short_message(text: str, limit: int = 160) -> str:
    """Keeps long yt-dlp error output from stretching the page wider than the
    window - the full text is still available via tooltip."""
    text = (text or "").strip().splitlines()[0] if text else ""
    if len(text) > limit:
        text = text[:limit].rstrip() + "…"
    return text


class YoutubeDownloaderPage(QWidget):
    def __init__(self, ctx: AppContext, parent=None):
        super().__init__(parent)
        self.ctx = ctx
        self._info = None
        self._thread = None
        self._update_thread = None

        self.url_edit = QLineEdit()
        self.url_edit.setPlaceholderText("https://www.youtube.com/watch?v=… (also works for playlist URLs)")
        fetch_btn = QPushButton("Fetch Info")
        fetch_btn.clicked.connect(self._fetch)

        update_btn = QPushButton("Check for yt-dlp Update")
        update_btn.clicked.connect(self._check_for_update)

        self.title_label = QLabel("—")
        self.title_label.setWordWrap(True)
        self.meta_label = QLabel("")
        self.meta_label.setWordWrap(True)

        self._has_separate_audio = False

        self.video_format_combo = NoWheelComboBox()
        self.audio_format_combo = NoWheelComboBox()
        self.audio_format_combo.addItem("Included in video stream", "")
        self.audio_format_combo.setEnabled(False)

        self.audio_only_check = QCheckBox("Audio only (MP3)")
        self.audio_only_check.toggled.connect(self._on_audio_only_toggled)
        self.prefer_mp4_check = QCheckBox("Prefer MP4 + M4A (best compatibility)")
        self.playlist_check = QCheckBox("Download entire playlist")
        self.playlist_check.toggled.connect(lambda checked: self.playlist_items_edit.setEnabled(checked))
        self.embed_subs_check = QCheckBox("Download & embed subtitles (if available)")
        self.archive_check = QCheckBox("Skip already-downloaded items (archive)")

        self.playlist_items_edit = QLineEdit()
        self.playlist_items_edit.setPlaceholderText("e.g. 5:20 or 1,3,5-7 (blank = all)")
        self.playlist_items_edit.setEnabled(False)

        self.use_cookies_check = QCheckBox("Use cookie file")
        self.use_cookies_check.setChecked(app_settings.get_use_cookies())
        self.use_cookies_check.toggled.connect(self._on_use_cookies_toggled)

        self.cookies_path_edit = QLineEdit(app_settings.get_cookies_path())
        self.cookies_path_edit.setPlaceholderText("Path to cookies.txt (Netscape format)")
        self.cookies_path_edit.setEnabled(self.use_cookies_check.isChecked())
        self.cookies_path_edit.textChanged.connect(app_settings.set_cookies_path)

        cookies_browse_btn = QPushButton("Browse…")
        cookies_browse_btn.setEnabled(self.use_cookies_check.isChecked())
        cookies_browse_btn.clicked.connect(self._browse_cookies_file)
        self._cookies_browse_btn = cookies_browse_btn

        self.output_bar = OutputBar()
        download_btn = QPushButton("Download → Add to Queue")
        download_btn.setObjectName("Primary")
        download_btn.clicked.connect(self._download)

        url_row = QHBoxLayout()
        url_row.addWidget(QLabel("URL:"))
        url_row.addWidget(self.url_edit, 1)
        url_row.addWidget(HelpButton("youtube.url"))
        url_row.addWidget(fetch_btn)
        url_row.addWidget(update_btn)

        video_fmt_row = QHBoxLayout()
        video_fmt_row.addWidget(QLabel("Video quality:"))
        video_fmt_row.addWidget(self.video_format_combo, 1)
        video_fmt_row.addWidget(HelpButton("youtube.format"))

        audio_fmt_row = QHBoxLayout()
        audio_fmt_row.addWidget(QLabel("Audio quality:"))
        audio_fmt_row.addWidget(self.audio_format_combo, 1)
        audio_fmt_row.addWidget(HelpButton("youtube.audio_format"))

        opts_row = QHBoxLayout()
        opts_row.addWidget(self.audio_only_check)
        opts_row.addWidget(HelpButton("youtube.audio_only"))
        opts_row.addWidget(self.prefer_mp4_check)
        opts_row.addWidget(HelpButton("youtube.prefer_mp4"))
        opts_row.addWidget(self.archive_check)
        opts_row.addWidget(HelpButton("youtube.archive"))
        opts_row.addStretch(1)

        playlist_row = QHBoxLayout()
        playlist_row.addWidget(self.playlist_check)
        playlist_row.addWidget(self.embed_subs_check)
        playlist_row.addWidget(QLabel("Playlist items:"))
        playlist_row.addWidget(self.playlist_items_edit)
        playlist_row.addWidget(HelpButton("youtube.playlist_items"))
        playlist_row.addStretch(1)

        cookies_row = QHBoxLayout()
        cookies_row.addWidget(self.use_cookies_check)
        cookies_row.addWidget(HelpButton("youtube.cookies"))
        cookies_row.addWidget(self.cookies_path_edit, 1)
        cookies_row.addWidget(self._cookies_browse_btn)

        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("<h2>YouTube Downloader</h2>"))
        layout.addLayout(url_row)
        layout.addWidget(self.title_label)
        layout.addWidget(self.meta_label)
        layout.addLayout(video_fmt_row)
        layout.addLayout(audio_fmt_row)
        layout.addLayout(opts_row)
        layout.addLayout(playlist_row)
        layout.addLayout(cookies_row)
        layout.addWidget(self.output_bar)
        layout.addWidget(download_btn)
        layout.addStretch(1)

    def _on_audio_only_toggled(self, checked: bool):
        self.video_format_combo.setEnabled(not checked)
        self.audio_format_combo.setEnabled(not checked and self._has_separate_audio)

    def _on_use_cookies_toggled(self, checked: bool):
        app_settings.set_use_cookies(checked)
        self.cookies_path_edit.setEnabled(checked)
        self._cookies_browse_btn.setEnabled(checked)

    def _browse_cookies_file(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Choose cookies file", self.cookies_path_edit.text(), "Text files (*.txt);;All files (*.*)")
        if path:
            self.cookies_path_edit.setText(path)

    def _cookies_file(self) -> str:
        if self.use_cookies_check.isChecked():
            return self.cookies_path_edit.text().strip()
        return ""

    def _fetch(self):
        url = self.url_edit.text().strip()
        if not url:
            QMessageBox.information(self, "YouTube Downloader", "Paste a URL first.")
            return
        self.title_label.setText("Fetching info…")
        self.meta_label.setText("")
        self._thread = _FetchThread(url, self._cookies_file(), self)
        self._thread.done.connect(self._on_fetched)
        self._thread.start()

    def _on_fetched(self, info, error: str):
        if error or info is None:
            self.title_label.setText("Failed to fetch info.")
            self.meta_label.setText(_short_message(error))
            self.meta_label.setToolTip(error)
            return

        self._info = info
        self.meta_label.setToolTip("")
        if info.is_playlist:
            self.title_label.setText(f"Playlist: {info.title}")
            self.meta_label.setText(f"{info.playlist_count} videos")
            self.playlist_check.setChecked(True)
            return

        self.title_label.setText(info.title)
        mins = int(info.duration // 60)
        secs = int(info.duration % 60)
        self.meta_label.setText(f"{info.uploader} · {mins}:{secs:02d}")

        usable = [f for f in info.formats if f.ext not in ("mhtml",)]
        video_only = sorted((f for f in usable if f.is_video_only), key=lambda f: f.video_sort_key, reverse=True)
        audio_only = sorted((f for f in usable if f.is_audio_only), key=lambda f: f.audio_sort_key, reverse=True)
        combined = [f for f in usable if not f.is_video_only and not f.is_audio_only]

        self.video_format_combo.clear()
        self.video_format_combo.addItem("Best available", "bestvideo")
        for f in video_only:
            self.video_format_combo.addItem(f.label, f.format_id)
        if not video_only:
            # This source doesn't offer separate video-only streams - fall back
            # to combined video+audio formats (each already includes its own audio).
            for f in sorted(combined, key=lambda f: f.video_sort_key, reverse=True):
                self.video_format_combo.addItem(f"{f.label} (includes audio)", f.format_id)

        self._has_separate_audio = bool(audio_only)
        self.audio_format_combo.clear()
        if audio_only:
            self.audio_format_combo.addItem("Best available", "bestaudio")
            for f in audio_only:
                self.audio_format_combo.addItem(f.label, f.format_id)
            self.audio_format_combo.setEnabled(True)
        else:
            self.audio_format_combo.addItem("Included in video stream", "")
            self.audio_format_combo.setEnabled(False)

    def _build_format_selector(self) -> str:
        if self.video_format_combo.count() == 0:
            # nothing fetched yet - build_download_args' own "bv*+ba/b" default kicks in
            return ""

        video_id = self.video_format_combo.currentData() or "bestvideo"
        audio_enabled = self._has_separate_audio and self.audio_format_combo.isEnabled()
        audio_id = (self.audio_format_combo.currentData() or "bestaudio") if audio_enabled else ""

        both_best = video_id == "bestvideo" and (not audio_enabled or audio_id == "bestaudio")
        if both_best:
            if self.prefer_mp4_check.isChecked():
                return "bv*[ext=mp4]+ba[ext=m4a]/b[ext=mp4]/bv*+ba/b"
            return "bv*+ba/b"

        if audio_enabled:
            return f"{video_id}+{audio_id}"
        return video_id

    def _download(self):
        url = self.url_edit.text().strip()
        if not url:
            QMessageBox.information(self, "YouTube Downloader", "Paste a URL first.")
            return

        audio_only = self.audio_only_check.isChecked()
        format_selector = "" if audio_only else self._build_format_selector()

        args = ytdlp.build_download_args(
            url, self.output_bar.output_dir(), format_selector,
            audio_only=audio_only, embed_subs=self.embed_subs_check.isChecked(),
            playlist=self.playlist_check.isChecked(),
            playlist_items=self.playlist_items_edit.text(),
            use_archive=self.archive_check.isChecked(),
            cookies_file=self._cookies_file(),
        )
        label = f"YouTube download: {self._info.title if self._info and not self._info.is_playlist else url}"
        job = Job(label=label, args=args, duration_sec=0.0, kind="ytdlp")
        self.ctx.job_queue.add(job)

    def _check_for_update(self):
        self._update_thread = _UpdateThread(self)
        self._update_thread.done.connect(self._on_update_done)
        self._update_thread.start()
        QMessageBox.information(self, "yt-dlp Update", "Checking for updates in the background - "
                                                        "you'll get a message when it's done.")

    def _on_update_done(self, success: bool, message: str):
        title = "yt-dlp Update" if success else "yt-dlp Update Failed"
        QMessageBox.information(self, title, message)
