"""A codec dropdown that always lists GPU (hardware) encoders first, under
their own header, with CPU (software) encoders grouped separately below -
per the product requirement that GPU codecs get distinct billing from CPU
codecs."""
from PySide6.QtCore import Qt
from PySide6.QtGui import QStandardItem, QStandardItemModel

from dcc.core.gpu import Capabilities, Encoder
from dcc.ui.widgets.inputs import NoWheelComboBox


class EncoderSelector(NoWheelComboBox):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._model = QStandardItemModel(self)
        self.setModel(self._model)
        self._encoders: list = []

    def populate(self, capabilities: Capabilities, gpu_vendor: str | None, codec_filter: str | None = None):
        self._model.clear()
        self._encoders = []

        encoders = capabilities.encoders_for_gpu(gpu_vendor)
        if codec_filter:
            encoders = [e for e in encoders if e.codec == codec_filter]

        hw = [e for e in encoders if e.hardware]
        sw = [e for e in encoders if not e.hardware]

        if hw:
            self._add_header(f"Hardware (GPU) - {gpu_vendor or 'auto'}")
            for e in hw:
                self._add_encoder(e)
        if sw:
            self._add_header("Software (CPU)")
            for e in sw:
                self._add_encoder(e)

        if not hw and not sw:
            self._add_header("No compatible encoders detected")

        # select the first real (non-header) entry
        for i in range(self._model.rowCount()):
            if self._model.item(i).isEnabled():
                self.setCurrentIndex(i)
                break

    def _add_header(self, text: str):
        item = QStandardItem(f"— {text} —")
        item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEnabled & ~Qt.ItemFlag.ItemIsSelectable)
        font = item.font()
        font.setBold(True)
        item.setFont(font)
        self._model.appendRow(item)

    def _add_encoder(self, encoder: Encoder):
        item = QStandardItem(f"    {encoder.label}")
        item.setData(encoder.name, Qt.ItemDataRole.UserRole)
        self._model.appendRow(item)
        self._encoders.append(encoder)

    def current_encoder_name(self) -> str:
        data = self.currentData(Qt.ItemDataRole.UserRole)
        return data or ""
