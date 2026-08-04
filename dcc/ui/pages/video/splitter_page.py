import os

from PySide6.QtWidgets import (
    QFileDialog, QHBoxLayout, QLabel, QLineEdit, QMessageBox, QPushButton, QVBoxLayout, QWidget,
)

from dcc.app_context import AppContext
from dcc.core import command_builder as cb
from dcc.core.job_queue import Job
from dcc.core.probe import probe_safe
from dcc.ui.widgets.help_button import HelpButton
from dcc.ui.widgets.output_bar import OutputBar

_AUDIO_EXT_BY_CODEC = {
    "aac": "m4a", "mp3": "mp3", "ac3": "ac3", "opus": "opus",
    "flac": "flac", "pcm_s16le": "wav", "vorbis": "ogg",
}


class SplitterPage(QWidget):
    def __init__(self, ctx: AppContext, parent=None):
        super().__init__(parent)
        self.ctx = ctx

        self.video_edit = QLineEdit()
        browse_btn = QPushButton("Browse…")
        browse_btn.clicked.connect(self._browse)
        self.output_bar = OutputBar()

        add_btn = QPushButton("Split → Add to Queue")
        add_btn.setObjectName("Primary")
        add_btn.clicked.connect(self._add_to_queue)

        info_row = QHBoxLayout()
        info_row.addWidget(QLabel("Extracts the video-only and audio-only tracks into two separate files."))
        info_row.addWidget(HelpButton("splitter.info"))
        info_row.addStretch(1)

        pick_row = QHBoxLayout()
        pick_row.addWidget(self.video_edit)
        pick_row.addWidget(browse_btn)

        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("<h2>Splitter</h2>"))
        layout.addLayout(info_row)
        layout.addWidget(QLabel("Video file:"))
        layout.addLayout(pick_row)
        layout.addWidget(self.output_bar)
        layout.addWidget(add_btn)
        layout.addStretch(1)

    def _browse(self):
        path, _ = QFileDialog.getOpenFileName(self, "Choose video", "", "Video files (*.*)")
        if path:
            self.video_edit.setText(path)

    def _add_to_queue(self):
        path = self.video_edit.text().strip()
        if not path:
            QMessageBox.information(self, "Splitter", "Choose a video file first.")
            return
        info = probe_safe(path)
        if info is None or not info.primary_video or not info.primary_audio:
            QMessageBox.warning(self, "Splitter", "The file must contain both a video and an audio track.")
            return

        base = os.path.splitext(os.path.basename(path))[0]
        out_dir = self.output_bar.output_dir()
        video_ext = os.path.splitext(path)[1].lstrip(".") or "mp4"
        audio_ext = _AUDIO_EXT_BY_CODEC.get(info.primary_audio.codec_name, "mka")

        video_out = os.path.join(out_dir, f"{base}_video.{video_ext}")
        audio_out = os.path.join(out_dir, f"{base}_audio.{audio_ext}")

        args = cb.build_split_args(path, video_out, audio_out)
        job = Job(label=f"Split: {os.path.basename(path)}", args=args,
                  duration_sec=info.duration, kind="ffmpeg")
        self.ctx.job_queue.add(job)
