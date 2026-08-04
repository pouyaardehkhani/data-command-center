import os

from PySide6.QtWidgets import QFileDialog, QHBoxLayout, QLabel, QLineEdit, QPushButton, QWidget

from dcc.core import settings as app_settings


class OutputBar(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.path_edit = QLineEdit(app_settings.get_output_dir())
        browse_btn = QPushButton("Browse…")
        browse_btn.clicked.connect(self._browse)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(QLabel("Output folder:"))
        layout.addWidget(self.path_edit, 1)
        layout.addWidget(browse_btn)

    def _browse(self):
        folder = QFileDialog.getExistingDirectory(self, "Choose output folder", self.path_edit.text())
        if folder:
            self.path_edit.setText(folder)
            app_settings.set_output_dir(folder)

    def output_dir(self) -> str:
        path = self.path_edit.text().strip() or app_settings.get_output_dir()
        os.makedirs(path, exist_ok=True)
        return path

    def output_path_for(self, input_path: str, extension: str) -> str:
        base = os.path.splitext(os.path.basename(input_path))[0]
        out_dir = self.output_dir()
        candidate = os.path.join(out_dir, f"{base}.{extension}")
        if os.path.abspath(candidate) == os.path.abspath(input_path):
            candidate = os.path.join(out_dir, f"{base}_converted.{extension}")
        return candidate
