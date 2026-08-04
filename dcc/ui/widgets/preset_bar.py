"""Save/load/delete a settings dataclass as a named preset, reused by every
feature panel."""
import qtawesome as qta
from PySide6.QtWidgets import (
    QHBoxLayout, QInputDialog, QLabel, QMessageBox, QPushButton, QWidget,
)

from dcc.core import presets
from dcc.ui.widgets.inputs import NoWheelComboBox


class PresetBar(QWidget):
    def __init__(self, feature: str, get_state, apply_state, parent=None):
        """
        feature: preset folder name (e.g. "video_converter")
        get_state: callable() -> dataclass instance to save
        apply_state: callable(dict) -> None, applies a loaded preset back to the UI
        """
        super().__init__(parent)
        self._feature = feature
        self._get_state = get_state
        self._apply_state = apply_state

        self.combo = NoWheelComboBox()
        self.combo.setMinimumWidth(160)
        save_btn = QPushButton(qta.icon("fa5s.save"), " Save")
        load_btn = QPushButton(qta.icon("fa5s.folder-open"), " Load")
        delete_btn = QPushButton(qta.icon("fa5s.trash"), "")

        save_btn.clicked.connect(self._save)
        load_btn.clicked.connect(self._load)
        delete_btn.clicked.connect(self._delete)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(QLabel("Preset:"))
        layout.addWidget(self.combo)
        layout.addWidget(load_btn)
        layout.addWidget(save_btn)
        layout.addWidget(delete_btn)
        layout.addStretch(1)

        self.refresh()

    def refresh(self):
        current = self.combo.currentText()
        self.combo.clear()
        self.combo.addItems(presets.list_presets(self._feature))
        idx = self.combo.findText(current)
        if idx >= 0:
            self.combo.setCurrentIndex(idx)

    def _save(self):
        name, ok = QInputDialog.getText(self, "Save preset", "Preset name:")
        if not ok or not name.strip():
            return
        presets.save_preset(self._feature, name, self._get_state())
        self.refresh()
        self.combo.setCurrentText(name.strip())

    def _load(self):
        name = self.combo.currentText()
        if not name:
            return
        try:
            data = presets.load_preset(self._feature, name)
        except Exception as e:
            QMessageBox.warning(self, "Load preset", f"Could not load preset: {e}")
            return
        self._apply_state(data)

    def _delete(self):
        name = self.combo.currentText()
        if not name:
            return
        if QMessageBox.question(self, "Delete preset", f"Delete preset '{name}'?") != QMessageBox.StandardButton.Yes:
            return
        presets.delete_preset(self._feature, name)
        self.refresh()
