import dataclasses
import os

from PySide6.QtWidgets import (
    QCheckBox, QFormLayout, QGroupBox, QHBoxLayout,
    QLabel, QMessageBox, QPushButton, QScrollArea, QSplitter, QVBoxLayout, QWidget,
)

from dcc.app_context import AppContext
from dcc.core import command_builder as cb
from dcc.core.job_queue import Job
from dcc.core.options import AudioOptions
from dcc.core.probe import probe_safe
from dcc.ui.widgets.file_batch_list import FileBatchList
from dcc.ui.widgets.help_button import HelpButton
from dcc.ui.widgets.inputs import DurationSpinBox, NoWheelComboBox, NoWheelSpinBox, combo_with_custom
from dcc.ui.widgets.output_bar import OutputBar
from dcc.ui.widgets.preset_bar import PresetBar
from dcc.ui.widgets.slider_spin import SliderSpin

AUDIO_FILTER = "Audio files (*.mp3 *.wav *.flac *.aac *.ogg *.m4a *.wma *.opus);;All files (*.*)"
CHANNEL_CHOICES = [("Source", 0), ("Mono", 1), ("Stereo", 2), ("5.1", 6), ("7.1", 8)]


def _row(form: QFormLayout, label: str, widget: QWidget, help_key: str):
    wrap = QHBoxLayout()
    wrap.setContentsMargins(0, 0, 0, 0)
    wrap.addWidget(QLabel(label))
    wrap.addWidget(HelpButton(help_key))
    wrap.addStretch(1)
    holder = QWidget()
    holder.setLayout(wrap)
    form.addRow(holder, widget)


class AudioConverterPage(QWidget):
    def __init__(self, ctx: AppContext, parent=None):
        super().__init__(parent)
        self.ctx = ctx

        self.file_list = FileBatchList(AUDIO_FILTER)
        self.container_combo = NoWheelComboBox()
        self.container_combo.addItems(cb.AUDIO_CONTAINER_CHOICES)
        self.output_bar = OutputBar()

        self._build_form()
        self.preset_bar = PresetBar("audio_converter", self._get_state, self._apply_state)

        add_btn = QPushButton("Add to Queue")
        add_btn.setObjectName("Primary")
        add_btn.clicked.connect(self._add_to_queue)

        left = QWidget()
        left_layout = QVBoxLayout(left)
        left_layout.addWidget(QLabel("<b>Input files (processed sequentially)</b>"))
        left_layout.addWidget(self.file_list, 1)
        out_row = QHBoxLayout()
        out_row.addWidget(QLabel("Output format:")); out_row.addWidget(self.container_combo)
        left_layout.addLayout(out_row)
        left_layout.addWidget(self.output_bar)
        left_layout.addWidget(self.preset_bar)
        left_layout.addWidget(add_btn)

        right_scroll = QScrollArea()
        right_scroll.setWidgetResizable(True)
        right_scroll.setWidget(self.group)

        splitter = QSplitter()
        splitter.addWidget(left)
        splitter.addWidget(right_scroll)
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 1)

        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("<h2>Audio Converter</h2>"))
        layout.addWidget(splitter)

    def _build_form(self):
        self.group = QGroupBox("Audio settings")
        form = QFormLayout(self.group)
        form.setHorizontalSpacing(12)
        form.setVerticalSpacing(10)

        self.encoder_combo = NoWheelComboBox()
        for key, label in cb.AUDIO_ENCODER_CHOICES.items():
            self.encoder_combo.addItem(label, key)
        _row(form, "Audio encode:", self.encoder_combo, "audio.encoder")

        self.sample_rate_combo = NoWheelComboBox()
        self.sample_rate_combo.addItems(["Source"] + [str(v) for v in cb.SAMPLE_RATE_PRESETS] + ["Custom"])
        self.sample_rate_custom_spin = NoWheelSpinBox(minimum=1000, maximum=192000, value=48000, suffix=" Hz")
        _row(form, "Sample rate (Hz):",
             combo_with_custom(self.sample_rate_combo, self.sample_rate_custom_spin), "audio.sample_rate")

        self.bitrate_combo = NoWheelComboBox()
        self.bitrate_combo.addItems(cb.BITRATE_PRESET_LABELS + ["Custom"])
        self.bitrate_custom_spin = NoWheelSpinBox(minimum=1, maximum=100000, value=192, suffix=" kb/s")
        _row(form, "Bitrate:", combo_with_custom(self.bitrate_combo, self.bitrate_custom_spin), "audio.bitrate")

        self.channels_combo = NoWheelComboBox()
        for label, _v in CHANNEL_CHOICES:
            self.channels_combo.addItem(label)
        _row(form, "Channels:", self.channels_combo, "audio.channels")

        self.disable_check = QCheckBox("Disable audio")
        _row(form, "", self.disable_check, "audio.disable")

        self.volume_slider = SliderSpin(0, 500, 100, "%")
        _row(form, "Volume:", self.volume_slider, "audio.volume")

        self.keep_streams_check = QCheckBox("Keep all source audio streams")
        _row(form, "", self.keep_streams_check, "audio.keep_all_streams")

        self.fade_in_spin = DurationSpinBox(maximum=30.0)
        _row(form, "Fade in:", self.fade_in_spin, "audio.fade_in")
        self.fade_out_spin = DurationSpinBox(maximum=30.0)
        _row(form, "Fade out:", self.fade_out_spin, "audio.fade_out")

        self.echo_check = QCheckBox("Echo")
        _row(form, "", self.echo_check, "audio.echo")
        self.denoise_check = QCheckBox("Denoise")
        _row(form, "", self.denoise_check, "audio.denoise")
        self.reverse_check = QCheckBox("Reverse")
        _row(form, "", self.reverse_check, "audio.reverse")

    def _sample_rate_value(self) -> int:
        text = self.sample_rate_combo.currentText()
        if text == "Source":
            return 0
        if text == "Custom":
            return self.sample_rate_custom_spin.value()
        try:
            return int(text)
        except ValueError:
            return 0

    def _set_sample_rate_combo(self, hz: int):
        if not hz:
            self.sample_rate_combo.setCurrentText("Source")
            return
        text = str(hz)
        if text in [str(v) for v in cb.SAMPLE_RATE_PRESETS]:
            self.sample_rate_combo.setCurrentText(text)
        else:
            self.sample_rate_combo.setCurrentText("Custom")
            self.sample_rate_custom_spin.setValue(hz)

    def _bitrate_value(self) -> int:
        text = self.bitrate_combo.currentText()
        if text == "Custom":
            return self.bitrate_custom_spin.value()
        return cb.parse_bitrate_label(text)

    def _set_bitrate_combo(self, kbps: int):
        if kbps <= 0:
            self.bitrate_combo.setCurrentText("Default")
            return
        label = cb.format_bitrate_kbps(kbps)
        if label in cb.BITRATE_PRESET_LABELS:
            self.bitrate_combo.setCurrentText(label)
        else:
            self.bitrate_combo.setCurrentText("Custom")
            self.bitrate_custom_spin.setValue(kbps)

    def _collect(self) -> AudioOptions:
        return AudioOptions(
            encoder=self.encoder_combo.currentData(),
            sample_rate=self._sample_rate_value(),
            bitrate_kbps=self._bitrate_value(),
            channels=CHANNEL_CHOICES[self.channels_combo.currentIndex()][1],
            disable_audio=self.disable_check.isChecked(),
            volume_percent=self.volume_slider.value(),
            keep_all_streams=self.keep_streams_check.isChecked(),
            fade_in_sec=self.fade_in_spin.value(),
            fade_out_sec=self.fade_out_spin.value(),
            echo=self.echo_check.isChecked(),
            denoise=self.denoise_check.isChecked(),
            reverse=self.reverse_check.isChecked(),
        )

    def _get_state(self) -> AudioOptions:
        return self._collect()

    def _apply_state(self, data: dict):
        try:
            opts = AudioOptions(**data)
        except TypeError as e:
            QMessageBox.warning(self, "Preset", f"This preset is incompatible: {e}")
            return
        idx = self.encoder_combo.findData(opts.encoder)
        if idx >= 0:
            self.encoder_combo.setCurrentIndex(idx)
        self._set_sample_rate_combo(opts.sample_rate)
        self._set_bitrate_combo(opts.bitrate_kbps)
        for i, (_l, v) in enumerate(CHANNEL_CHOICES):
            if v == opts.channels:
                self.channels_combo.setCurrentIndex(i)
                break
        self.disable_check.setChecked(opts.disable_audio)
        self.volume_slider.setValue(opts.volume_percent)
        self.keep_streams_check.setChecked(opts.keep_all_streams)
        self.fade_in_spin.setValue(opts.fade_in_sec)
        self.fade_out_spin.setValue(opts.fade_out_sec)
        self.echo_check.setChecked(opts.echo)
        self.denoise_check.setChecked(opts.denoise)
        self.reverse_check.setChecked(opts.reverse)

    def _add_to_queue(self):
        paths = self.file_list.paths()
        if not paths:
            QMessageBox.information(self, "Audio Converter", "Add at least one input file first.")
            return
        template = self._collect()
        container = self.container_combo.currentText()
        for path in paths:
            info = probe_safe(path)
            if info is None:
                QMessageBox.warning(self, "Audio Converter", f"Could not read: {os.path.basename(path)}")
                continue
            opts = dataclasses.replace(template)
            output_path = self.output_bar.output_path_for(path, container)
            args = cb.build_audio_convert_args(path, output_path, info, opts)
            job = Job(label=f"Convert audio: {os.path.basename(path)} → {container}",
                      args=args, duration_sec=info.duration, kind="ffmpeg")
            self.ctx.job_queue.add(job)
