import os

from PySide6.QtWidgets import QHBoxLayout, QLabel, QMessageBox, QPushButton, QVBoxLayout, QWidget

from dcc.app_context import AppContext
from dcc.core import command_builder as cb
from dcc.core.job_queue import Job
from dcc.core.probe import probe_safe
from dcc.ui.pages.audio.converter_page import AUDIO_FILTER
from dcc.ui.widgets.file_batch_list import FileBatchList
from dcc.ui.widgets.help_button import HelpButton
from dcc.ui.widgets.inputs import NoWheelComboBox
from dcc.ui.widgets.output_bar import OutputBar


class JoinerPage(QWidget):
    def __init__(self, ctx: AppContext, parent=None):
        super().__init__(parent)
        self.ctx = ctx

        self.file_list = FileBatchList(AUDIO_FILTER)
        self.container_combo = NoWheelComboBox()
        self.container_combo.addItems(cb.AUDIO_CONTAINER_CHOICES)
        self.output_bar = OutputBar()

        add_btn = QPushButton("Join → Add to Queue")
        add_btn.setObjectName("Primary")
        add_btn.clicked.connect(self._add_to_queue)

        info_row = QHBoxLayout()
        info_row.addWidget(QLabel("Joins tracks one after another, in the order shown (drag to reorder)."))
        info_row.addWidget(HelpButton("joiner.info"))
        info_row.addStretch(1)

        out_row = QHBoxLayout()
        out_row.addWidget(QLabel("Output format:")); out_row.addWidget(self.container_combo)

        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("<h2>Audio Joiner</h2>"))
        layout.addLayout(info_row)
        layout.addWidget(self.file_list, 1)
        layout.addLayout(out_row)
        layout.addWidget(self.output_bar)
        layout.addWidget(add_btn)

    def _add_to_queue(self):
        paths = self.file_list.paths()
        if len(paths) < 2:
            QMessageBox.information(self, "Audio Joiner", "Add at least two audio files to join.")
            return
        total_duration = 0.0
        for p in paths:
            info = probe_safe(p)
            if info is None:
                QMessageBox.warning(self, "Audio Joiner", f"Could not read: {os.path.basename(p)}")
                return
            total_duration += info.duration

        container = self.container_combo.currentText()
        output_path = os.path.join(self.output_bar.output_dir(), f"joined.{container}")
        args = cb.build_audio_join_args(paths, output_path)
        job = Job(label=f"Join {len(paths)} tracks → {os.path.basename(output_path)}",
                  args=args, duration_sec=total_duration, kind="ffmpeg")
        self.ctx.job_queue.add(job)
