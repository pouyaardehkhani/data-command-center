"""Shared input primitives used app-wide instead of raw Qt widgets, so
sizing and scroll-wheel behavior are fixed once, everywhere, not per-page.

Each widget only reacts to the mouse wheel once it already has focus (i.e.
the user deliberately clicked/tabbed into it). Otherwise the wheel event is
ignored and bubbles up to the enclosing QScrollArea, so scrolling the page
never silently changes a value.

Note: the wheel guard is implemented directly on each class rather than via
a shared mixin - PySide6/Shiboken's virtual-method dispatch for QWidget
subclasses does not reliably pick up overrides from a non-QObject mixin in
a multiple-inheritance chain, so a mixin here would silently do nothing.

All controls also get consistent minimum width/height so values and units
(e.g. "0.00 s") are never vertically or horizontally clipped.
"""
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QComboBox, QDoubleSpinBox, QHBoxLayout, QSlider, QSpinBox, QWidget

MIN_HEIGHT = 30
MIN_COMBO_WIDTH = 130
MIN_SPIN_WIDTH = 100
MIN_DURATION_WIDTH = 125


class NoWheelSpinBox(QSpinBox):
    def __init__(self, minimum=0, maximum=99999, value=0, suffix="", parent=None):
        super().__init__(parent)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.setRange(minimum, maximum)
        self.setValue(value)
        if suffix:
            self.setSuffix(suffix)
        self.setMinimumWidth(MIN_SPIN_WIDTH)
        self.setMinimumHeight(MIN_HEIGHT)
        self.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)

    def wheelEvent(self, event):
        if self.hasFocus():
            super().wheelEvent(event)
        else:
            event.ignore()


class NoWheelDoubleSpinBox(QDoubleSpinBox):
    def __init__(self, minimum=0.0, maximum=99999.0, value=0.0, decimals=2, suffix="", parent=None):
        super().__init__(parent)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.setDecimals(decimals)
        self.setRange(minimum, maximum)
        self.setValue(value)
        if suffix:
            self.setSuffix(suffix)
        self.setMinimumWidth(MIN_SPIN_WIDTH + 15)
        self.setMinimumHeight(MIN_HEIGHT)
        self.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)

    def wheelEvent(self, event):
        if self.hasFocus():
            super().wheelEvent(event)
        else:
            event.ignore()


class DurationSpinBox(NoWheelDoubleSpinBox):
    """A 0.00 s-style duration field, preconfigured so every page's fade/interval/
    start/end inputs are identical instead of each page re-deriving its own."""

    def __init__(self, minimum=0.0, maximum=30.0, value=0.0, parent=None):
        super().__init__(minimum=minimum, maximum=maximum, value=value, decimals=2, suffix=" s", parent=parent)
        self.setMinimumWidth(MIN_DURATION_WIDTH)


class NoWheelComboBox(QComboBox):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.setMinimumHeight(MIN_HEIGHT)
        self.setMinimumWidth(MIN_COMBO_WIDTH)

    def wheelEvent(self, event):
        if self.hasFocus():
            super().wheelEvent(event)
        else:
            event.ignore()


class NoWheelSlider(QSlider):
    def __init__(self, orientation=Qt.Orientation.Horizontal, parent=None):
        super().__init__(orientation, parent)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)

    def wheelEvent(self, event):
        if self.hasFocus():
            super().wheelEvent(event)
        else:
            event.ignore()


def combo_with_custom(combo: NoWheelComboBox, custom_widget: QWidget) -> QWidget:
    """Pairs a preset combo (whose item list ends in 'Custom') with a
    companion numeric field that's only enabled once 'Custom' is selected.
    This is the reliable, app-wide alternative to an *editable* QComboBox,
    which is unreliable to theme/click consistently across Qt widget styles."""
    custom_widget.setEnabled(False)
    combo.currentTextChanged.connect(lambda t: custom_widget.setEnabled(t == "Custom"))
    row = QHBoxLayout()
    row.setContentsMargins(0, 0, 0, 0)
    row.setSpacing(10)
    row.addWidget(combo, 1)
    row.addWidget(custom_widget)
    widget = QWidget()
    widget.setLayout(row)
    return widget
