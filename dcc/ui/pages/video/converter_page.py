"""Video Converter: the flagship page. Every option from the spec's video
and audio-track lists, all defaulted from each source file's own probed
values, with GPU-first encoder selection and batch (sequential) processing."""
import dataclasses
import os

from PySide6.QtWidgets import (
    QCheckBox, QFormLayout, QGroupBox, QHBoxLayout, QLabel, QLineEdit,
    QMessageBox, QPushButton, QScrollArea, QSplitter, QVBoxLayout, QWidget,
)

from dcc.app_context import AppContext
from dcc.core import command_builder as cb
from dcc.core.job_queue import Job
from dcc.core.options import AudioOptions, VideoOptions
from dcc.core.probe import probe_safe
from dcc.ui.widgets.encoder_selector import EncoderSelector
from dcc.ui.widgets.file_batch_list import FileBatchList
from dcc.ui.widgets.gpu_selector import GpuSelector
from dcc.ui.widgets.help_button import HelpButton
from dcc.ui.widgets.inputs import (
    DurationSpinBox, NoWheelComboBox, NoWheelDoubleSpinBox, NoWheelSpinBox, combo_with_custom,
)
from dcc.ui.widgets.output_bar import OutputBar
from dcc.ui.widgets.preset_bar import PresetBar
from dcc.ui.widgets.slider_spin import SliderSpin

VIDEO_FILTER = "Video files (*.mp4 *.mkv *.avi *.mov *.webm *.flv *.wmv *.ts *.m4v *.mpg *.mpeg);;All files (*.*)"

PIXEL_FORMATS = ["Auto (source)", "yuv420p", "yuv420p10le", "yuv422p", "yuv444p", "nv12", "p010le"]
CHANNEL_CHOICES = [("Source", 0), ("Mono", 1), ("Stereo", 2), ("5.1", 6), ("7.1", 8)]

# index -> (rate_control, crf enabled, bitrate enabled)
RATE_CONTROL_MODES = ["Auto (recommended)", "CRF / CQ (manual)", "Bitrate (CBR/VBR)"]


def _row(form: QFormLayout, label: str, widget: QWidget, help_key: str | None = None):
    if help_key:
        wrap = QHBoxLayout()
        wrap.setContentsMargins(0, 0, 0, 0)
        lbl = QLabel(label)
        wrap.addWidget(lbl)
        wrap.addWidget(HelpButton(help_key))
        wrap.addStretch(1)
        holder = QWidget()
        holder.setLayout(wrap)
        form.addRow(holder, widget)
    else:
        form.addRow(label, widget)


class VideoConverterPage(QWidget):
    def __init__(self, ctx: AppContext, parent=None):
        super().__init__(parent)
        self.ctx = ctx

        self.file_list = FileBatchList(VIDEO_FILTER)
        self.output_bar = OutputBar()
        self.container_combo = NoWheelComboBox()
        self.container_combo.addItems(cb.VIDEO_CONTAINER_CHOICES)

        self.gpu_selector = GpuSelector()
        self.gpu_selector.populate(ctx.capabilities)
        self.encoder_selector = EncoderSelector()
        self.gpu_selector.currentIndexChanged.connect(self._refresh_encoders)

        self._build_video_group()
        self._build_audio_group()
        self._refresh_encoders()

        self.preset_bar = PresetBar("video_converter", self._get_state, self._apply_state)

        add_btn = QPushButton("Add to Queue")
        add_btn.setObjectName("Primary")
        add_btn.clicked.connect(self._add_to_queue)

        left = QWidget()
        left_layout = QVBoxLayout(left)
        left_layout.addWidget(QLabel("<b>Input files (processed sequentially)</b>"))
        left_layout.addWidget(self.file_list, 1)
        out_row = QHBoxLayout()
        out_row.addWidget(QLabel("Output format:"))
        out_row.addWidget(self.container_combo)
        left_layout.addLayout(out_row)
        left_layout.addWidget(self.output_bar)
        left_layout.addWidget(QLabel("GPU:"))
        left_layout.addWidget(self.gpu_selector)
        left_layout.addWidget(self.preset_bar)
        left_layout.addWidget(add_btn)

        right_scroll = QScrollArea()
        right_scroll.setWidgetResizable(True)
        right_content = QWidget()
        right_layout = QVBoxLayout(right_content)
        right_layout.addWidget(self.video_group)
        right_layout.addWidget(self.audio_group)
        right_layout.addStretch(1)
        right_scroll.setWidget(right_content)

        splitter = QSplitter()
        splitter.addWidget(left)
        splitter.addWidget(right_scroll)
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 2)

        outer = QVBoxLayout(self)
        outer.addWidget(QLabel("<h2>Video Converter</h2>"))
        outer.addWidget(splitter)

    # ------------------------------------------------------------------
    def _build_video_group(self):
        self.video_group = QGroupBox("Video")
        form = QFormLayout(self.video_group)
        form.setHorizontalSpacing(12)
        form.setVerticalSpacing(10)

        _row(form, "Encoder:", self.encoder_selector, "video.encoder")

        self.rate_control_combo = NoWheelComboBox()
        self.rate_control_combo.addItems(RATE_CONTROL_MODES)
        _row(form, "Rate control:", self.rate_control_combo, "video.rate_control")

        self.crf_spin = NoWheelSpinBox(minimum=0, maximum=63, value=23)
        self.crf_spin.setEnabled(False)
        _row(form, "CRF / CQ:", self.crf_spin, "video.crf")

        self.bitrate_combo = NoWheelComboBox()
        self.bitrate_combo.addItems(cb.BITRATE_PRESET_LABELS + ["Custom"])
        self.bitrate_custom_spin = NoWheelSpinBox(minimum=1, maximum=100000, value=2000, suffix=" kb/s")
        self.bitrate_combo.setEnabled(False)
        self.bitrate_custom_spin.setEnabled(False)
        _row(form, "Bitrate:", combo_with_custom(self.bitrate_combo, self.bitrate_custom_spin), "video.bitrate")

        self.rate_control_combo.currentIndexChanged.connect(self._on_rate_control_changed)
        self._on_rate_control_changed(0)

        self.resolution_combo = NoWheelComboBox()
        self.resolution_combo.addItems(["Source"] + list(cb.RESOLUTION_PRESETS.keys()) + ["Custom"])
        self.width_spin = NoWheelSpinBox(minimum=0, maximum=8192)
        self.width_spin.setEnabled(False)
        self.height_spin = NoWheelSpinBox(minimum=0, maximum=8192)
        self.height_spin.setEnabled(False)
        self.resolution_combo.currentTextChanged.connect(
            lambda t: (self.width_spin.setEnabled(t == "Custom"), self.height_spin.setEnabled(t == "Custom")))
        res_row = QHBoxLayout()
        res_row.setSpacing(10)
        res_row.addWidget(self.resolution_combo, 1)
        res_row.addWidget(QLabel("W:")); res_row.addWidget(self.width_spin)
        res_row.addWidget(QLabel("H:")); res_row.addWidget(self.height_spin)
        res_widget = QWidget(); res_widget.setLayout(res_row)
        _row(form, "Resolution:", res_widget, "video.resolution")

        self.fps_combo = NoWheelComboBox()
        self.fps_combo.addItems(["Source"] + [str(f) for f in cb.FPS_PRESETS] + ["Custom"])
        self.fps_custom_spin = NoWheelDoubleSpinBox(minimum=1.0, maximum=1000.0, value=30.0, decimals=3)
        _row(form, "FPS:", combo_with_custom(self.fps_combo, self.fps_custom_spin), "video.fps")

        self.aspect_combo = NoWheelComboBox()
        self.aspect_combo.addItems(["Source", "16:9", "4:3", "1:1", "9:16", "Custom"])
        self.aspect_custom_edit = QLineEdit()
        self.aspect_custom_edit.setPlaceholderText("W:H e.g. 21:9")
        self.aspect_custom_edit.setMinimumWidth(120)
        self.aspect_custom_edit.setEnabled(False)
        self.aspect_combo.currentTextChanged.connect(lambda t: self.aspect_custom_edit.setEnabled(t == "Custom"))
        ar_row = QHBoxLayout()
        ar_row.setSpacing(10)
        ar_row.addWidget(self.aspect_combo); ar_row.addWidget(self.aspect_custom_edit)
        ar_widget = QWidget(); ar_widget.setLayout(ar_row)
        _row(form, "Aspect ratio:", ar_widget, "video.aspect_ratio")

        self.keyframe_spin = DurationSpinBox(minimum=0.5, maximum=20.0, value=2.0)
        _row(form, "Key frame interval:", self.keyframe_spin, "video.keyframe_interval")

        self.deinterlace_check = QCheckBox("Deinterlace")
        _row(form, "", self.deinterlace_check, "video.deinterlace")

        self.rotate_combo = NoWheelComboBox()
        self.rotate_combo.addItems(["0°", "90°", "180°", "270°"])
        _row(form, "Rotate:", self.rotate_combo, "video.rotate")

        self.mirror_x_check = QCheckBox("Mirror horizontally (X)")
        _row(form, "", self.mirror_x_check, "video.mirror_x")
        self.mirror_y_check = QCheckBox("Mirror vertically (Y)")
        _row(form, "", self.mirror_y_check, "video.mirror_y")

        self.filter_combo = NoWheelComboBox()
        self.filter_combo.addItems(cb.FILTER_PRESET_CHOICES)
        _row(form, "Filter:", self.filter_combo, "video.filter")

        self.fade_in_spin = DurationSpinBox(maximum=30.0)
        _row(form, "Fade in:", self.fade_in_spin, "video.fade_in")
        self.fade_out_spin = DurationSpinBox(maximum=30.0)
        _row(form, "Fade out:", self.fade_out_spin, "video.fade_out")

        self.anti_shake_check = QCheckBox("Anti-shake (stabilize)")
        _row(form, "", self.anti_shake_check, "video.anti_shake")
        self.denoise_check = QCheckBox("Denoise")
        _row(form, "", self.denoise_check, "video.denoise")
        self.reverse_check = QCheckBox("Reverse")
        _row(form, "", self.reverse_check, "video.reverse")

        self.sharpness_slider = SliderSpin(-5, 5, 0)
        _row(form, "Sharpness:", self.sharpness_slider, "video.sharpness")
        self.film_grain_slider = SliderSpin(0, 50, 0)
        _row(form, "Film grain:", self.film_grain_slider, "video.film_grain")

        self.pixel_format_combo = NoWheelComboBox()
        self.pixel_format_combo.addItems(PIXEL_FORMATS)
        _row(form, "Pixel format:", self.pixel_format_combo, "video.pixel_format")

    def _build_audio_group(self):
        self.audio_group = QGroupBox("Audio")
        form = QFormLayout(self.audio_group)
        form.setHorizontalSpacing(12)
        form.setVerticalSpacing(10)

        self.audio_encoder_combo = NoWheelComboBox()
        for key, label in cb.AUDIO_ENCODER_CHOICES.items():
            self.audio_encoder_combo.addItem(label, key)
        _row(form, "Audio encode:", self.audio_encoder_combo, "audio.encoder")

        self.sample_rate_combo = NoWheelComboBox()
        self.sample_rate_combo.addItems(["Source"] + [str(v) for v in cb.SAMPLE_RATE_PRESETS] + ["Custom"])
        self.sample_rate_custom_spin = NoWheelSpinBox(minimum=1000, maximum=192000, value=48000, suffix=" Hz")
        _row(form, "Sample rate (Hz):",
             combo_with_custom(self.sample_rate_combo, self.sample_rate_custom_spin), "audio.sample_rate")

        self.audio_bitrate_combo = NoWheelComboBox()
        self.audio_bitrate_combo.addItems(cb.BITRATE_PRESET_LABELS + ["Custom"])
        self.audio_bitrate_custom_spin = NoWheelSpinBox(minimum=1, maximum=100000, value=192, suffix=" kb/s")
        _row(form, "Bitrate:",
             combo_with_custom(self.audio_bitrate_combo, self.audio_bitrate_custom_spin), "audio.bitrate")

        self.channels_combo = NoWheelComboBox()
        for label, _val in CHANNEL_CHOICES:
            self.channels_combo.addItem(label)
        _row(form, "Channels:", self.channels_combo, "audio.channels")

        self.disable_audio_check = QCheckBox("Disable audio")
        _row(form, "", self.disable_audio_check, "audio.disable")

        self.volume_slider = SliderSpin(0, 500, 100, "%")
        _row(form, "Volume:", self.volume_slider, "audio.volume")

        self.keep_streams_check = QCheckBox("Keep all source audio streams")
        _row(form, "", self.keep_streams_check, "audio.keep_all_streams")

        self.audio_fade_in_spin = DurationSpinBox(maximum=30.0)
        _row(form, "Fade in:", self.audio_fade_in_spin, "audio.fade_in")
        self.audio_fade_out_spin = DurationSpinBox(maximum=30.0)
        _row(form, "Fade out:", self.audio_fade_out_spin, "audio.fade_out")

        self.echo_check = QCheckBox("Echo")
        _row(form, "", self.echo_check, "audio.echo")
        self.audio_denoise_check = QCheckBox("Denoise")
        _row(form, "", self.audio_denoise_check, "audio.denoise")
        self.audio_reverse_check = QCheckBox("Reverse")
        _row(form, "", self.audio_reverse_check, "audio.reverse")

    # ------------------------------------------------------------------
    def _on_rate_control_changed(self, index: int):
        self.crf_spin.setEnabled(index == 1)
        self.bitrate_combo.setEnabled(index == 2)
        if index != 2:
            self.bitrate_custom_spin.setEnabled(False)
        else:
            self.bitrate_custom_spin.setEnabled(self.bitrate_combo.currentText() == "Custom")

    def _refresh_encoders(self):
        vendor = self.gpu_selector.current_vendor()
        self.encoder_selector.populate(self.ctx.capabilities, vendor)

    def _int_or_zero(self, text: str) -> int:
        text = text.strip()
        if not text or text.lower() == "source":
            return 0
        try:
            return int(float(text))
        except ValueError:
            return 0

    def _float_or_zero(self, text: str) -> float:
        text = text.strip()
        if not text or text.lower() == "source":
            return 0.0
        try:
            return float(text)
        except ValueError:
            return 0.0

    def _fps_value(self) -> float:
        text = self.fps_combo.currentText()
        if text == "Source":
            return 0.0
        if text == "Custom":
            return self.fps_custom_spin.value()
        try:
            return float(text)
        except ValueError:
            return 0.0

    def _set_fps_combo(self, fps: float):
        if not fps:
            self.fps_combo.setCurrentText("Source")
            return
        for f in cb.FPS_PRESETS:
            if abs(f - fps) < 1e-6:
                self.fps_combo.setCurrentText(str(f))
                return
        self.fps_combo.setCurrentText("Custom")
        self.fps_custom_spin.setValue(fps)

    def _bitrate_value(self, combo: NoWheelComboBox, spin: NoWheelSpinBox) -> int:
        text = combo.currentText()
        if text == "Custom":
            return spin.value()
        return cb.parse_bitrate_label(text)

    def _set_bitrate_combo(self, combo: NoWheelComboBox, spin: NoWheelSpinBox, kbps: int):
        if kbps <= 0:
            combo.setCurrentText("Default")
            return
        label = cb.format_bitrate_kbps(kbps)
        if label in cb.BITRATE_PRESET_LABELS:
            combo.setCurrentText(label)
        else:
            combo.setCurrentText("Custom")
            spin.setValue(kbps)

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

    def _collect_video_options(self) -> VideoOptions:
        mode = self.rate_control_combo.currentIndex()
        rate_control = "bitrate" if mode == 2 else "crf"
        crf_value = self.crf_spin.value() if mode == 1 else 0
        bitrate_value = self._bitrate_value(self.bitrate_combo, self.bitrate_custom_spin) if mode == 2 else 0

        audio = AudioOptions(
            encoder=self.audio_encoder_combo.currentData(),
            sample_rate=self._sample_rate_value(),
            bitrate_kbps=self._bitrate_value(self.audio_bitrate_combo, self.audio_bitrate_custom_spin),
            channels=CHANNEL_CHOICES[self.channels_combo.currentIndex()][1],
            disable_audio=self.disable_audio_check.isChecked(),
            volume_percent=self.volume_slider.value(),
            keep_all_streams=self.keep_streams_check.isChecked(),
            fade_in_sec=self.audio_fade_in_spin.value(),
            fade_out_sec=self.audio_fade_out_spin.value(),
            echo=self.echo_check.isChecked(),
            denoise=self.audio_denoise_check.isChecked(),
            reverse=self.audio_reverse_check.isChecked(),
        )
        pix_fmt = self.pixel_format_combo.currentText()
        pix_fmt = "" if pix_fmt.startswith("Auto") else pix_fmt

        return VideoOptions(
            encoder=self.encoder_selector.current_encoder_name(),
            gpu_vendor=self.gpu_selector.current_vendor(),
            rate_control=rate_control,
            crf=crf_value,
            bitrate_kbps=bitrate_value,
            resolution_preset=self.resolution_combo.currentText(),
            width=self.width_spin.value(),
            height=self.height_spin.value(),
            fps=self._fps_value(),
            aspect_ratio=self.aspect_combo.currentText(),
            aspect_custom=self.aspect_custom_edit.text(),
            keyframe_interval_sec=self.keyframe_spin.value(),
            deinterlace=self.deinterlace_check.isChecked(),
            rotate_deg=int(self.rotate_combo.currentText().rstrip("°")),
            mirror_x=self.mirror_x_check.isChecked(),
            mirror_y=self.mirror_y_check.isChecked(),
            filter_preset=self.filter_combo.currentText(),
            fade_in_sec=self.fade_in_spin.value(),
            fade_out_sec=self.fade_out_spin.value(),
            anti_shake=self.anti_shake_check.isChecked(),
            denoise=self.denoise_check.isChecked(),
            reverse=self.reverse_check.isChecked(),
            sharpness=self.sharpness_slider.value(),
            film_grain=self.film_grain_slider.value(),
            pixel_format=pix_fmt,
            audio=audio,
        )

    def _get_state(self) -> VideoOptions:
        return self._collect_video_options()

    def _apply_state(self, data: dict):
        try:
            audio_data = data.pop("audio", {})
            opts = VideoOptions(**data)
            opts.audio = AudioOptions(**audio_data)
        except TypeError as e:
            QMessageBox.warning(self, "Preset", f"This preset is incompatible: {e}")
            return

        if opts.rate_control == "bitrate":
            mode_index = 2
        elif opts.crf > 0:
            mode_index = 1
        else:
            mode_index = 0
        self.rate_control_combo.setCurrentIndex(mode_index)
        self.crf_spin.setValue(opts.crf if opts.crf > 0 else 23)
        self._set_bitrate_combo(self.bitrate_combo, self.bitrate_custom_spin, opts.bitrate_kbps)
        self._on_rate_control_changed(mode_index)

        self.resolution_combo.setCurrentText(opts.resolution_preset)
        self.width_spin.setValue(opts.width)
        self.height_spin.setValue(opts.height)
        self._set_fps_combo(opts.fps)
        self.aspect_combo.setCurrentText(opts.aspect_ratio)
        self.aspect_custom_edit.setText(opts.aspect_custom)
        self.keyframe_spin.setValue(opts.keyframe_interval_sec)
        self.deinterlace_check.setChecked(opts.deinterlace)
        self.rotate_combo.setCurrentText(f"{opts.rotate_deg}°")
        self.mirror_x_check.setChecked(opts.mirror_x)
        self.mirror_y_check.setChecked(opts.mirror_y)
        self.filter_combo.setCurrentText(opts.filter_preset)
        self.fade_in_spin.setValue(opts.fade_in_sec)
        self.fade_out_spin.setValue(opts.fade_out_sec)
        self.anti_shake_check.setChecked(opts.anti_shake)
        self.denoise_check.setChecked(opts.denoise)
        self.reverse_check.setChecked(opts.reverse)
        self.sharpness_slider.setValue(opts.sharpness)
        self.film_grain_slider.setValue(opts.film_grain)
        self.pixel_format_combo.setCurrentText(opts.pixel_format or "Auto (source)")

        audio = opts.audio
        idx = self.audio_encoder_combo.findData(audio.encoder)
        if idx >= 0:
            self.audio_encoder_combo.setCurrentIndex(idx)
        self._set_sample_rate_combo(audio.sample_rate)
        self._set_bitrate_combo(self.audio_bitrate_combo, self.audio_bitrate_custom_spin, audio.bitrate_kbps)
        for i, (_label, val) in enumerate(CHANNEL_CHOICES):
            if val == audio.channels:
                self.channels_combo.setCurrentIndex(i)
                break
        self.disable_audio_check.setChecked(audio.disable_audio)
        self.volume_slider.setValue(audio.volume_percent)
        self.keep_streams_check.setChecked(audio.keep_all_streams)
        self.audio_fade_in_spin.setValue(audio.fade_in_sec)
        self.audio_fade_out_spin.setValue(audio.fade_out_sec)
        self.echo_check.setChecked(audio.echo)
        self.audio_denoise_check.setChecked(audio.denoise)
        self.audio_reverse_check.setChecked(audio.reverse)

    # ------------------------------------------------------------------
    def _add_to_queue(self):
        paths = self.file_list.paths()
        if not paths:
            QMessageBox.information(self, "Video Converter", "Add at least one input file first.")
            return
        if not self.encoder_selector.current_encoder_name():
            QMessageBox.warning(self, "Video Converter", "No compatible video encoder is selected.")
            return

        opts_template = self._collect_video_options()
        container = self.container_combo.currentText()

        for path in paths:
            info = probe_safe(path)
            if info is None:
                QMessageBox.warning(self, "Video Converter", f"Could not read: {os.path.basename(path)}")
                continue
            opts = dataclasses.replace(opts_template, audio=dataclasses.replace(opts_template.audio))
            output_path = self.output_bar.output_path_for(path, container)
            args = cb.build_video_convert_args(path, output_path, info, opts)
            job = Job(label=f"Convert: {os.path.basename(path)} → {container}",
                      args=args, duration_sec=info.duration, kind="ffmpeg")
            self.ctx.job_queue.add(job)
