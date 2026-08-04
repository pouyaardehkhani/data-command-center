import qtawesome as qta
from PySide6.QtCore import QPoint, Qt
from PySide6.QtWidgets import QToolButton, QToolTip

from dcc.ui.help_text import help_for


class HelpButton(QToolButton):
    """A small '?' icon that shows contextual help on hover or click."""

    def __init__(self, key: str, parent=None):
        super().__init__(parent)
        self._text = help_for(key)
        self.setIcon(qta.icon("fa5s.question-circle", color="#9aa1ae"))
        self.setToolTip(self._text)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setAutoRaise(True)
        self.setFixedSize(20, 20)
        self.clicked.connect(self._show_popup)

    def _show_popup(self):
        QToolTip.showText(self.mapToGlobal(QPoint(0, self.height())), self._text, self)
