from PySide6.QtCore import Signal
from PySide6.QtWidgets import QHBoxLayout, QWidget

from dcc.ui.widgets.inputs import NoWheelSlider, NoWheelSpinBox


class SliderSpin(QWidget):
    valueChanged = Signal(int)

    def __init__(self, minimum: int, maximum: int, value: int = 0, suffix: str = "", parent=None):
        super().__init__(parent)
        self.slider = NoWheelSlider()
        self.slider.setRange(minimum, maximum)
        self.slider.setValue(value)

        self.spin = NoWheelSpinBox(minimum=minimum, maximum=maximum, value=value, suffix=suffix)

        self.slider.valueChanged.connect(self._from_slider)
        self.spin.valueChanged.connect(self._from_spin)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.slider, 1)
        layout.addWidget(self.spin)

    def _from_slider(self, v):
        self.spin.blockSignals(True)
        self.spin.setValue(v)
        self.spin.blockSignals(False)
        self.valueChanged.emit(v)

    def _from_spin(self, v):
        self.slider.blockSignals(True)
        self.slider.setValue(v)
        self.slider.blockSignals(False)
        self.valueChanged.emit(v)

    def value(self) -> int:
        return self.spin.value()

    def setValue(self, v: int):
        self.spin.setValue(v)
