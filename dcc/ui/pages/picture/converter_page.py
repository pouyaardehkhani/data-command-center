import os

from PySide6.QtWidgets import (
    QHBoxLayout, QLabel, QMessageBox, QPushButton, QVBoxLayout, QWidget,
)

from dcc.app_context import AppContext
from dcc.core import command_builder as cb
from dcc.core.job_queue import Job
from dcc.core.options import ImageOptions
from dcc.core.probe import probe_safe
from dcc.ui.widgets.file_batch_list import FileBatchList
from dcc.ui.widgets.help_button import HelpButton
from dcc.ui.widgets.inputs import NoWheelComboBox, NoWheelSpinBox
from dcc.ui.widgets.output_bar import OutputBar
from dcc.ui.widgets.preset_bar import PresetBar
from dcc.ui.widgets.slider_spin import SliderSpin

IMAGE_FILTER = "Images (*.png *.jpg *.jpeg *.bmp *.webp *.tiff *.gif);;All files (*.*)"


class PictureConverterPage(QWidget):
    def __init__(self, ctx: AppContext, parent=None):
        super().__init__(parent)
        self.ctx = ctx

        self.file_list = FileBatchList(IMAGE_FILTER)
        self.format_combo = NoWheelComboBox()
        self.format_combo.addItems(cb.IMAGE_CONTAINER_CHOICES)

        self.width_spin = NoWheelSpinBox(minimum=0, maximum=16384, suffix=" px")
        self.height_spin = NoWheelSpinBox(minimum=0, maximum=16384, suffix=" px")
        self.quality_slider = SliderSpin(1, 100, 90, "%")

        self.output_bar = OutputBar()
        self.preset_bar = PresetBar("picture_converter", self._get_state, self._apply_state)

        add_btn = QPushButton("Add to Queue")
        add_btn.setObjectName("Primary")
        add_btn.clicked.connect(self._add_to_queue)

        fmt_row = QHBoxLayout()
        fmt_row.addWidget(QLabel("Output format:"))
        fmt_row.addWidget(self.format_combo)

        res_row = QHBoxLayout()
        res_row.setSpacing(10)
        res_row.addWidget(QLabel("Resolution:"))
        res_row.addWidget(HelpButton("picture.resolution"))
        res_row.addSpacing(10)
        res_row.addWidget(QLabel("W:")); res_row.addWidget(self.width_spin)
        res_row.addSpacing(20)
        res_row.addWidget(QLabel("H (0x0 = source):")); res_row.addWidget(self.height_spin)
        res_row.addStretch(1)

        quality_row = QHBoxLayout()
        quality_row.addWidget(QLabel("Quality (jpg/webp):"))
        quality_row.addWidget(self.quality_slider)

        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("<h2>Picture Converter</h2>"))
        layout.addWidget(self.file_list, 1)
        layout.addLayout(fmt_row)
        layout.addLayout(res_row)
        layout.addLayout(quality_row)
        layout.addWidget(self.output_bar)
        layout.addWidget(self.preset_bar)
        layout.addWidget(add_btn)

    def _get_state(self) -> ImageOptions:
        return ImageOptions(format=self.format_combo.currentText(), width=self.width_spin.value(),
                             height=self.height_spin.value(), quality=self.quality_slider.value())

    def _apply_state(self, data: dict):
        try:
            opts = ImageOptions(**data)
        except TypeError as e:
            QMessageBox.warning(self, "Preset", f"This preset is incompatible: {e}")
            return
        self.format_combo.setCurrentText(opts.format)
        self.width_spin.setValue(opts.width)
        self.height_spin.setValue(opts.height)
        self.quality_slider.setValue(opts.quality)

    def _add_to_queue(self):
        paths = self.file_list.paths()
        if not paths:
            QMessageBox.information(self, "Picture Converter", "Add at least one image first.")
            return
        template = self._get_state()
        for path in paths:
            info = probe_safe(path)
            if info is None:
                QMessageBox.warning(self, "Picture Converter", f"Could not read: {os.path.basename(path)}")
                continue
            output_path = self.output_bar.output_path_for(path, template.format)
            args = cb.build_image_convert_args(path, output_path, template)
            job = Job(label=f"Convert image: {os.path.basename(path)} → {template.format}",
                      args=args, duration_sec=0.0, kind="ffmpeg")
            self.ctx.job_queue.add(job)
