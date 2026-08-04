import os

from PySide6.QtWidgets import (
    QFileDialog, QFormLayout, QHBoxLayout, QLabel, QLineEdit, QMessageBox,
    QPushButton, QVBoxLayout, QWidget,
)

from dcc.app_context import AppContext
from dcc.core import command_builder as cb
from dcc.core.job_queue import Job
from dcc.core.options import CropOptions
from dcc.core.probe import probe_safe
from dcc.ui.widgets.encoder_selector import EncoderSelector
from dcc.ui.widgets.gpu_selector import GpuSelector
from dcc.ui.widgets.help_button import HelpButton
from dcc.ui.widgets.inputs import NoWheelSpinBox
from dcc.ui.widgets.output_bar import OutputBar
from dcc.ui.widgets.preset_bar import PresetBar


class CropPage(QWidget):
    def __init__(self, ctx: AppContext, parent=None):
        super().__init__(parent)
        self.ctx = ctx
        self._info = None

        self.video_edit = QLineEdit()
        browse_btn = QPushButton("Browse…")
        browse_btn.clicked.connect(self._browse)

        self.x_spin = NoWheelSpinBox(minimum=0, maximum=16384, suffix=" px")
        self.y_spin = NoWheelSpinBox(minimum=0, maximum=16384, suffix=" px")
        self.w_spin = NoWheelSpinBox(minimum=1, maximum=16384, value=640, suffix=" px")
        self.h_spin = NoWheelSpinBox(minimum=1, maximum=16384, value=360, suffix=" px")

        self.gpu_selector = GpuSelector()
        self.gpu_selector.populate(ctx.capabilities)
        self.encoder_selector = EncoderSelector()
        self.gpu_selector.currentIndexChanged.connect(
            lambda: self.encoder_selector.populate(ctx.capabilities, self.gpu_selector.current_vendor()))
        self.encoder_selector.populate(ctx.capabilities, self.gpu_selector.current_vendor())

        self.output_bar = OutputBar()
        self.preset_bar = PresetBar("crop", self._get_state, self._apply_state)
        add_btn = QPushButton("Crop → Add to Queue")
        add_btn.setObjectName("Primary")
        add_btn.clicked.connect(self._add_to_queue)

        info_row = QHBoxLayout()
        info_row.addWidget(QLabel("Crops a rectangular region out of the frame."))
        info_row.addWidget(HelpButton("crop.info"))
        info_row.addStretch(1)

        pick_row = QHBoxLayout()
        pick_row.addWidget(self.video_edit)
        pick_row.addWidget(browse_btn)

        form = QFormLayout()
        form.setHorizontalSpacing(12)
        form.setVerticalSpacing(10)
        form.addRow("Video file:", _wrap(pick_row))
        form.addRow("X:", self.x_spin)
        form.addRow("Y:", self.y_spin)
        form.addRow("Width:", self.w_spin)
        form.addRow("Height:", self.h_spin)
        form.addRow("GPU:", self.gpu_selector)
        form.addRow("Encoder:", self.encoder_selector)

        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("<h2>Crop</h2>"))
        layout.addLayout(info_row)
        layout.addLayout(form)
        layout.addWidget(self.output_bar)
        layout.addWidget(self.preset_bar)
        layout.addWidget(add_btn)
        layout.addStretch(1)

    def _get_state(self) -> CropOptions:
        return CropOptions(x=self.x_spin.value(), y=self.y_spin.value(),
                            width=self.w_spin.value(), height=self.h_spin.value(),
                            encoder=self.encoder_selector.current_encoder_name() or "libx264")

    def _apply_state(self, data: dict):
        try:
            opts = CropOptions(**data)
        except TypeError as e:
            QMessageBox.warning(self, "Preset", f"This preset is incompatible: {e}")
            return
        self.x_spin.setValue(opts.x)
        self.y_spin.setValue(opts.y)
        self.w_spin.setValue(opts.width)
        self.h_spin.setValue(opts.height)

    def _browse(self):
        path, _ = QFileDialog.getOpenFileName(self, "Choose video", "", "Video files (*.*)")
        if not path:
            return
        self.video_edit.setText(path)
        info = probe_safe(path)
        if info and info.primary_video:
            self._info = info
            self.w_spin.setMaximum(info.primary_video.width)
            self.h_spin.setMaximum(info.primary_video.height)
            self.x_spin.setMaximum(info.primary_video.width)
            self.y_spin.setMaximum(info.primary_video.height)
            self.w_spin.setValue(info.primary_video.width)
            self.h_spin.setValue(info.primary_video.height)

    def _add_to_queue(self):
        path = self.video_edit.text().strip()
        if not path:
            QMessageBox.information(self, "Crop", "Choose a video file first.")
            return
        info = self._info or probe_safe(path)
        if info is None:
            QMessageBox.warning(self, "Crop", "Could not read the video file.")
            return
        encoder = self.encoder_selector.current_encoder_name() or "libx264"

        opts = CropOptions(x=self.x_spin.value(), y=self.y_spin.value(),
                            width=self.w_spin.value(), height=self.h_spin.value(), encoder=encoder)
        ext = os.path.splitext(path)[1].lstrip(".") or "mp4"
        output_path = os.path.join(self.output_bar.output_dir(),
                                    f"{os.path.splitext(os.path.basename(path))[0]}_cropped.{ext}")
        args = cb.build_crop_args(path, output_path, info, opts)
        job = Job(label=f"Crop: {os.path.basename(path)}", args=args,
                  duration_sec=info.duration, kind="ffmpeg")
        self.ctx.job_queue.add(job)


def _wrap(layout: QHBoxLayout) -> QWidget:
    w = QWidget()
    layout.setContentsMargins(0, 0, 0, 0)
    w.setLayout(layout)
    return w
