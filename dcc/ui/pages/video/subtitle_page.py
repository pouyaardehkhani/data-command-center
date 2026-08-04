import os

from PySide6.QtWidgets import (
    QFileDialog, QFormLayout, QGroupBox, QHBoxLayout, QLabel,
    QLineEdit, QMessageBox, QPushButton, QRadioButton, QVBoxLayout, QWidget,
)

from dcc.app_context import AppContext
from dcc.core import command_builder as cb
from dcc.core.job_queue import Job
from dcc.core.options import SubtitleOptions
from dcc.core.probe import probe_safe
from dcc.ui.widgets.help_button import HelpButton
from dcc.ui.widgets.inputs import NoWheelComboBox, NoWheelSpinBox
from dcc.ui.widgets.output_bar import OutputBar
from dcc.ui.widgets.preset_bar import PresetBar

SUBTITLE_FILTER = "Subtitles (*.srt *.ass *.ssa *.vtt);;All files (*.*)"


class SubtitlePage(QWidget):
    def __init__(self, ctx: AppContext, parent=None):
        super().__init__(parent)
        self.ctx = ctx

        self.video_edit = QLineEdit()
        video_btn = QPushButton("Browse…")
        video_btn.clicked.connect(self._browse_video)

        self.sub_edit = QLineEdit()
        sub_btn = QPushButton("Browse…")
        sub_btn.clicked.connect(self._browse_sub)

        self.soft_radio = QRadioButton("Soft (mux as toggleable track)")
        self.hard_radio = QRadioButton("Hard (burn into picture)")
        self.soft_radio.setChecked(True)

        self.font_size_spin = NoWheelSpinBox(minimum=8, maximum=96, value=24)
        self.font_color_combo = NoWheelComboBox(); self.font_color_combo.addItems(["white", "yellow", "black", "red"])

        self.container_combo = NoWheelComboBox()
        self.container_combo.addItems(cb.VIDEO_CONTAINER_CHOICES)
        self.output_bar = OutputBar()

        self.preset_bar = PresetBar("subtitle", self._get_state, self._apply_state)

        add_btn = QPushButton("Add to Queue")
        add_btn.setObjectName("Primary")
        add_btn.clicked.connect(self._add_to_queue)

        form = QFormLayout()
        video_row = QHBoxLayout(); video_row.addWidget(self.video_edit); video_row.addWidget(video_btn)
        form.addRow("Video file:", _wrap(video_row))
        sub_row = QHBoxLayout(); sub_row.addWidget(self.sub_edit); sub_row.addWidget(sub_btn)
        form.addRow("Subtitle file:", _wrap(sub_row))

        mode_group = QGroupBox("Mode")
        mode_layout = QVBoxLayout(mode_group)
        mode_header = QHBoxLayout()
        mode_header.addWidget(HelpButton("subtitle.mode"))
        mode_header.addStretch(1)
        mode_layout.addLayout(mode_header)
        mode_layout.addWidget(self.soft_radio)
        mode_layout.addWidget(self.hard_radio)
        style_row = QHBoxLayout()
        style_row.addWidget(QLabel("Font size:")); style_row.addWidget(self.font_size_spin)
        style_row.addWidget(QLabel("Color:")); style_row.addWidget(self.font_color_combo)
        mode_layout.addLayout(style_row)

        out_row = QHBoxLayout()
        out_row.addWidget(QLabel("Output format:")); out_row.addWidget(self.container_combo)

        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("<h2>Add Subtitle</h2>"))
        layout.addLayout(form)
        layout.addWidget(mode_group)
        layout.addLayout(out_row)
        layout.addWidget(self.output_bar)
        layout.addWidget(self.preset_bar)
        layout.addWidget(add_btn)
        layout.addStretch(1)

    def _get_state(self) -> SubtitleOptions:
        return SubtitleOptions(mode="hard" if self.hard_radio.isChecked() else "soft",
                                font_size=self.font_size_spin.value(),
                                font_color=self.font_color_combo.currentText())

    def _apply_state(self, data: dict):
        try:
            opts = SubtitleOptions(**data)
        except TypeError as e:
            QMessageBox.warning(self, "Preset", f"This preset is incompatible: {e}")
            return
        self.hard_radio.setChecked(opts.mode == "hard")
        self.soft_radio.setChecked(opts.mode == "soft")
        self.font_size_spin.setValue(opts.font_size)
        self.font_color_combo.setCurrentText(opts.font_color)

    def _browse_video(self):
        path, _ = QFileDialog.getOpenFileName(self, "Choose video", "", "Video files (*.*)")
        if path:
            self.video_edit.setText(path)

    def _browse_sub(self):
        path, _ = QFileDialog.getOpenFileName(self, "Choose subtitle", "", SUBTITLE_FILTER)
        if path:
            self.sub_edit.setText(path)

    def _add_to_queue(self):
        video_path = self.video_edit.text().strip()
        sub_path = self.sub_edit.text().strip()
        if not video_path or not sub_path:
            QMessageBox.information(self, "Add Subtitle", "Choose both a video and a subtitle file.")
            return
        info = probe_safe(video_path)
        if info is None:
            QMessageBox.warning(self, "Add Subtitle", "Could not read the video file.")
            return

        opts = SubtitleOptions(
            mode="hard" if self.hard_radio.isChecked() else "soft",
            font_size=self.font_size_spin.value(),
            font_color=self.font_color_combo.currentText(),
        )
        container = self.container_combo.currentText()
        output_path = self.output_bar.output_path_for(video_path, container)
        args = cb.build_subtitle_args(video_path, sub_path, output_path, opts)
        job = Job(label=f"Add subtitle: {os.path.basename(video_path)}", args=args,
                  duration_sec=info.duration, kind="ffmpeg")
        self.ctx.job_queue.add(job)


def _wrap(layout: QHBoxLayout) -> QWidget:
    w = QWidget()
    layout.setContentsMargins(0, 0, 0, 0)
    w.setLayout(layout)
    return w
