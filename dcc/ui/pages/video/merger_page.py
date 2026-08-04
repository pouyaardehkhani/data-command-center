import os

from PySide6.QtWidgets import QHBoxLayout, QLabel, QMessageBox, QPushButton, QVBoxLayout, QWidget

from dcc.app_context import AppContext
from dcc.core import command_builder as cb
from dcc.core.job_queue import Job
from dcc.core.probe import probe_safe
from dcc.ui.widgets.file_batch_list import FileBatchList
from dcc.ui.widgets.help_button import HelpButton
from dcc.ui.widgets.inputs import NoWheelComboBox
from dcc.ui.widgets.output_bar import OutputBar

VIDEO_FILTER = "Video files (*.mp4 *.mkv *.avi *.mov *.webm *.flv *.wmv *.ts *.m4v);;All files (*.*)"


class MergerPage(QWidget):
    def __init__(self, ctx: AppContext, parent=None):
        super().__init__(parent)
        self.ctx = ctx

        self.file_list = FileBatchList(VIDEO_FILTER)
        self.container_combo = NoWheelComboBox()
        self.container_combo.addItems(cb.VIDEO_CONTAINER_CHOICES)
        self.output_bar = OutputBar()

        add_btn = QPushButton("Merge → Add to Queue")
        add_btn.setObjectName("Primary")
        add_btn.clicked.connect(self._add_to_queue)

        info_row = QHBoxLayout()
        info_row.addWidget(QLabel("Videos are joined in the order shown below (drag to reorder)."))
        info_row.addWidget(HelpButton("merger.info"))
        info_row.addStretch(1)

        out_row = QHBoxLayout()
        out_row.addWidget(QLabel("Output format:"))
        out_row.addWidget(self.container_combo)

        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("<h2>Video Merger</h2>"))
        layout.addLayout(info_row)
        layout.addWidget(self.file_list, 1)
        layout.addLayout(out_row)
        layout.addWidget(self.output_bar)
        layout.addWidget(add_btn)

    def _add_to_queue(self):
        paths = self.file_list.paths()
        if len(paths) < 2:
            QMessageBox.information(self, "Video Merger", "Add at least two videos to merge.")
            return

        total_duration = 0.0
        for p in paths:
            info = probe_safe(p)
            if info is None:
                QMessageBox.warning(self, "Video Merger", f"Could not read: {os.path.basename(p)}")
                return
            total_duration += info.duration

        container = self.container_combo.currentText()
        output_path = os.path.join(self.output_bar.output_dir(), f"merged.{container}")

        args = cb.build_merge_args(paths, output_path)
        job = Job(label=f"Merge {len(paths)} videos → {os.path.basename(output_path)}",
                  args=args, duration_sec=total_duration, kind="ffmpeg")
        self.ctx.job_queue.add(job)
