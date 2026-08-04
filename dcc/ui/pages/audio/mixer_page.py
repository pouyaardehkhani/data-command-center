import os

from PySide6.QtWidgets import (
    QHBoxLayout, QLabel, QMessageBox, QPushButton, QVBoxLayout, QWidget,
)

from dcc.app_context import AppContext
from dcc.core import command_builder as cb
from dcc.core.job_queue import Job
from dcc.core.probe import probe_safe
from dcc.ui.pages.audio.converter_page import AUDIO_FILTER
from dcc.ui.widgets.file_batch_list import FileBatchList
from dcc.ui.widgets.help_button import HelpButton
from dcc.ui.widgets.inputs import NoWheelComboBox
from dcc.ui.widgets.output_bar import OutputBar
from dcc.ui.widgets.slider_spin import SliderSpin


class MixerPage(QWidget):
    def __init__(self, ctx: AppContext, parent=None):
        super().__init__(parent)
        self.ctx = ctx
        self._volume_sliders: dict = {}

        self.file_list = FileBatchList(AUDIO_FILTER)
        self.file_list.changed.connect(self._rebuild_volume_rows)

        self.volume_container = QVBoxLayout()

        self.container_combo = NoWheelComboBox()
        self.container_combo.addItems(cb.AUDIO_CONTAINER_CHOICES)
        self.output_bar = OutputBar()

        add_btn = QPushButton("Mix → Add to Queue")
        add_btn.setObjectName("Primary")
        add_btn.clicked.connect(self._add_to_queue)

        info_row = QHBoxLayout()
        info_row.addWidget(QLabel("Blends all tracks together into one, playing simultaneously."))
        info_row.addWidget(HelpButton("mixer.info"))
        info_row.addStretch(1)

        out_row = QHBoxLayout()
        out_row.addWidget(QLabel("Output format:")); out_row.addWidget(self.container_combo)

        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("<h2>Audio Mixer</h2>"))
        layout.addLayout(info_row)
        layout.addWidget(self.file_list, 1)
        layout.addWidget(QLabel("<b>Per-track volume</b>"))
        layout.addLayout(self.volume_container)
        layout.addLayout(out_row)
        layout.addWidget(self.output_bar)
        layout.addWidget(add_btn)

    def _rebuild_volume_rows(self):
        while self.volume_container.count():
            item = self.volume_container.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        old = self._volume_sliders
        self._volume_sliders = {}
        for path in self.file_list.paths():
            slider = SliderSpin(0, 200, int(old.get(path, 100)), "%")
            self._volume_sliders[path] = slider
            row = QHBoxLayout()
            label = QLabel(os.path.basename(path))
            label.setMinimumWidth(200)
            row.addWidget(label)
            row.addWidget(slider)
            wrap = QWidget()
            wrap.setLayout(row)
            self.volume_container.addWidget(wrap)

    def _add_to_queue(self):
        paths = self.file_list.paths()
        if len(paths) < 2:
            QMessageBox.information(self, "Audio Mixer", "Add at least two audio files to mix.")
            return
        for p in paths:
            if probe_safe(p) is None:
                QMessageBox.warning(self, "Audio Mixer", f"Could not read: {os.path.basename(p)}")
                return

        volumes = [self._volume_sliders[p].value() if p in self._volume_sliders else 100 for p in paths]
        container = self.container_combo.currentText()
        output_path = os.path.join(self.output_bar.output_dir(), f"mixed.{container}")
        args = cb.build_audio_mix_args(paths, volumes, output_path)
        job = Job(label=f"Mix {len(paths)} tracks → {os.path.basename(output_path)}",
                  args=args, duration_sec=0.0, kind="ffmpeg")
        self.ctx.job_queue.add(job)
