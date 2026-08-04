import os

from PySide6.QtWidgets import (
    QFileDialog, QFormLayout, QHBoxLayout, QLabel,
    QLineEdit, QMessageBox, QPushButton, QRadioButton, QVBoxLayout, QWidget,
)

from dcc.app_context import AppContext
from dcc.core import command_builder as cb
from dcc.core.job_queue import Job
from dcc.core.options import FrameExportOptions
from dcc.core.probe import probe_safe
from dcc.ui.widgets.help_button import HelpButton
from dcc.ui.widgets.inputs import DurationSpinBox, NoWheelComboBox, NoWheelSpinBox
from dcc.ui.widgets.output_bar import OutputBar
from dcc.ui.widgets.preset_bar import PresetBar


class FrameExportPage(QWidget):
    def __init__(self, ctx: AppContext, parent=None):
        super().__init__(parent)
        self.ctx = ctx
        self._duration = 0.0

        self.video_edit = QLineEdit()
        browse_btn = QPushButton("Browse…")
        browse_btn.clicked.connect(self._browse)

        self.interval_radio = QRadioButton("Every N seconds")
        self.count_radio = QRadioButton("Fixed number of frames")
        self.range_radio = QRadioButton("All frames in a time range")
        self.interval_radio.setChecked(True)

        self.interval_spin = DurationSpinBox(minimum=0.1, maximum=3600.0, value=1.0)
        self.count_spin = NoWheelSpinBox(minimum=1, maximum=10000, value=10)
        self.start_spin = DurationSpinBox(minimum=0.0, maximum=999999.0)
        self.end_spin = DurationSpinBox(minimum=0.0, maximum=999999.0)

        self.format_combo = NoWheelComboBox(); self.format_combo.addItems(["png", "jpg"])
        self.width_spin = NoWheelSpinBox(minimum=0, maximum=8192, suffix=" px")
        self.height_spin = NoWheelSpinBox(minimum=0, maximum=8192, suffix=" px")

        self.output_bar = OutputBar()
        self.preset_bar = PresetBar("frame_export", self._get_state, self._apply_state)
        add_btn = QPushButton("Export Frames → Add to Queue")
        add_btn.setObjectName("Primary")
        add_btn.clicked.connect(self._add_to_queue)

        info_row = QHBoxLayout()
        info_row.addWidget(QLabel("Extracts still frames from the video as image files."))
        info_row.addWidget(HelpButton("frames.mode"))
        info_row.addStretch(1)

        pick_row = QHBoxLayout()
        pick_row.addWidget(self.video_edit)
        pick_row.addWidget(browse_btn)

        form = QFormLayout()
        form.setHorizontalSpacing(12)
        form.setVerticalSpacing(10)
        form.addRow("Video file:", _wrap(pick_row))
        form.addRow(self.interval_radio, self.interval_spin)
        form.addRow(self.count_radio, self.count_spin)
        form.addRow(self.range_radio, QLabel(""))
        range_row = QHBoxLayout()
        range_row.setSpacing(10)
        range_row.addWidget(QLabel("Start:")); range_row.addWidget(self.start_spin)
        range_row.addSpacing(20)
        range_row.addWidget(QLabel("End:")); range_row.addWidget(self.end_spin)
        range_row.addStretch(1)
        form.addRow("Range:", _wrap(range_row))
        form.addRow("Image format:", self.format_combo)
        size_row = QHBoxLayout()
        size_row.setSpacing(10)
        size_row.addWidget(QLabel("W:")); size_row.addWidget(self.width_spin)
        size_row.addSpacing(20)
        size_row.addWidget(QLabel("H (0 = source):")); size_row.addWidget(self.height_spin)
        size_row.addStretch(1)
        form.addRow("Resize:", _wrap(size_row))

        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("<h2>Export Frames</h2>"))
        layout.addLayout(info_row)
        layout.addLayout(form)
        layout.addWidget(self.output_bar)
        layout.addWidget(self.preset_bar)
        layout.addWidget(add_btn)
        layout.addStretch(1)

    def _get_state(self) -> FrameExportOptions:
        mode = "interval" if self.interval_radio.isChecked() else "count" if self.count_radio.isChecked() else "range"
        return FrameExportOptions(mode=mode, interval_sec=self.interval_spin.value(),
                                   frame_count=self.count_spin.value(), start_sec=self.start_spin.value(),
                                   end_sec=self.end_spin.value(), image_format=self.format_combo.currentText(),
                                   width=self.width_spin.value(), height=self.height_spin.value())

    def _apply_state(self, data: dict):
        try:
            opts = FrameExportOptions(**data)
        except TypeError as e:
            QMessageBox.warning(self, "Preset", f"This preset is incompatible: {e}")
            return
        self.interval_radio.setChecked(opts.mode == "interval")
        self.count_radio.setChecked(opts.mode == "count")
        self.range_radio.setChecked(opts.mode == "range")
        self.interval_spin.setValue(opts.interval_sec)
        self.count_spin.setValue(opts.frame_count)
        self.start_spin.setValue(opts.start_sec)
        if opts.end_sec:
            self.end_spin.setValue(opts.end_sec)
        self.format_combo.setCurrentText(opts.image_format)
        self.width_spin.setValue(opts.width)
        self.height_spin.setValue(opts.height)

    def _browse(self):
        path, _ = QFileDialog.getOpenFileName(self, "Choose video", "", "Video files (*.*)")
        if not path:
            return
        self.video_edit.setText(path)
        info = probe_safe(path)
        if info:
            self._duration = info.duration
            self.end_spin.setValue(info.duration)

    def _add_to_queue(self):
        path = self.video_edit.text().strip()
        if not path:
            QMessageBox.information(self, "Export Frames", "Choose a video file first.")
            return
        info = probe_safe(path)
        if info is None:
            QMessageBox.warning(self, "Export Frames", "Could not read the video file.")
            return

        mode = "interval" if self.interval_radio.isChecked() else "count" if self.count_radio.isChecked() else "range"
        opts = FrameExportOptions(
            mode=mode, interval_sec=self.interval_spin.value(), frame_count=self.count_spin.value(),
            start_sec=self.start_spin.value(), end_sec=self.end_spin.value(),
            image_format=self.format_combo.currentText(),
            width=self.width_spin.value(), height=self.height_spin.value(),
        )
        out_dir = os.path.join(self.output_bar.output_dir(),
                                f"{os.path.splitext(os.path.basename(path))[0]}_frames")
        os.makedirs(out_dir, exist_ok=True)
        args = cb.build_frame_export_args(path, out_dir, opts)
        job = Job(label=f"Export frames: {os.path.basename(path)}", args=args,
                  duration_sec=info.duration if mode != "count" else 0.0, kind="ffmpeg")
        self.ctx.job_queue.add(job)


def _wrap(layout: QHBoxLayout) -> QWidget:
    w = QWidget()
    layout.setContentsMargins(0, 0, 0, 0)
    w.setLayout(layout)
    return w
