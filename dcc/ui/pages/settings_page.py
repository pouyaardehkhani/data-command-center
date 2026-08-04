from PySide6.QtWidgets import (
    QFormLayout, QGroupBox, QHBoxLayout, QLabel, QLineEdit,
    QFileDialog, QPushButton, QRadioButton, QVBoxLayout, QWidget,
)
from PySide6.QtWidgets import QApplication

from dcc.app_context import AppContext
from dcc.core import settings as app_settings
from dcc.ui.theme import apply_theme
from dcc.ui.widgets.inputs import NoWheelComboBox


class SettingsPage(QWidget):
    def __init__(self, ctx: AppContext, parent=None):
        super().__init__(parent)
        self.ctx = ctx

        theme_group = QGroupBox("Appearance")
        theme_layout = QVBoxLayout(theme_group)
        self.dark_radio = QRadioButton("Dark mode")
        self.light_radio = QRadioButton("Light mode")
        current_theme = app_settings.get_theme()
        self.dark_radio.setChecked(current_theme == "dark")
        self.light_radio.setChecked(current_theme != "dark")
        self.dark_radio.toggled.connect(self._on_theme_changed)
        theme_layout.addWidget(self.dark_radio)
        theme_layout.addWidget(self.light_radio)

        defaults_group = QGroupBox("Defaults")
        form = QFormLayout(defaults_group)

        self.gpu_combo = NoWheelComboBox()
        self.gpu_combo.addItem("Auto (best available)", "")
        for vendor in ctx.capabilities.vendor_names():
            self.gpu_combo.addItem(vendor, vendor)
        saved_gpu = app_settings.get_default_gpu()
        idx = self.gpu_combo.findData(saved_gpu)
        if idx >= 0:
            self.gpu_combo.setCurrentIndex(idx)
        self.gpu_combo.currentIndexChanged.connect(
            lambda: app_settings.set_default_gpu(self.gpu_combo.currentData()))
        form.addRow("Default GPU:", self.gpu_combo)

        self.output_edit = QLineEdit(app_settings.get_output_dir())
        browse_btn = QPushButton("Browse…")
        browse_btn.clicked.connect(self._browse_output)
        out_row = QHBoxLayout()
        out_row.addWidget(self.output_edit)
        out_row.addWidget(browse_btn)
        form.addRow("Default output folder:", _wrap(out_row))

        gpu_info_group = QGroupBox("Detected hardware")
        gpu_info_layout = QVBoxLayout(gpu_info_group)
        for gpu in ctx.capabilities.gpus:
            gpu_info_layout.addWidget(QLabel(f"• {gpu.vendor.value}: {gpu.name}"))
        hw = [e for e in ctx.capabilities.encoders if e.hardware]
        sw = [e for e in ctx.capabilities.encoders if not e.hardware]
        gpu_info_layout.addWidget(QLabel(f"<br><b>Hardware encoders ({len(hw)}):</b> " + ", ".join(e.name for e in hw) if hw else "No hardware encoders detected."))
        gpu_info_layout.addWidget(QLabel(f"<b>Software encoders ({len(sw)}):</b> " + ", ".join(e.name for e in sw)))

        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("<h2>Settings</h2>"))
        layout.addWidget(theme_group)
        layout.addWidget(defaults_group)
        layout.addWidget(gpu_info_group)
        layout.addStretch(1)

    def _on_theme_changed(self, checked: bool):
        theme = "dark" if checked else "light"
        app_settings.set_theme(theme)
        app = QApplication.instance()
        if app:
            apply_theme(app, theme)

    def _browse_output(self):
        folder = QFileDialog.getExistingDirectory(self, "Choose default output folder", self.output_edit.text())
        if folder:
            self.output_edit.setText(folder)
            app_settings.set_output_dir(folder)


def _wrap(layout: QHBoxLayout) -> QWidget:
    w = QWidget()
    layout.setContentsMargins(0, 0, 0, 0)
    w.setLayout(layout)
    return w
