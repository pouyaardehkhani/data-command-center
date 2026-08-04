from PySide6.QtWidgets import (
    QGroupBox, QLabel, QLineEdit, QScrollArea, QVBoxLayout, QWidget,
)

from dcc.ui.help_text import HELP

_CATEGORY_TITLES = {
    "video": "Video Converter",
    "audio": "Audio settings (shared by Video Converter & Audio Converter)",
    "subtitle": "Subtitles",
    "merger": "Video Merger",
    "splitter": "Splitter",
    "crop": "Crop",
    "frames": "Export Frames",
    "youtube": "YouTube Downloader",
    "mixer": "Audio Mixer",
    "joiner": "Audio Joiner",
    "picture": "Picture Converter",
    "gpu": "GPU acceleration",
}


class HelpPage(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)

        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText("Search help topics…")
        self.search_edit.textChanged.connect(self._filter)

        self._groups: list = []
        content = QWidget()
        content_layout = QVBoxLayout(content)

        by_category: dict = {}
        for key, text in HELP.items():
            category = key.split(".")[0]
            by_category.setdefault(category, []).append((key, text))

        for category, items in by_category.items():
            group = QGroupBox(_CATEGORY_TITLES.get(category, category.title()))
            group_layout = QVBoxLayout(group)
            rows = []
            for key, text in items:
                label = QLabel(f"<b>{key.split('.', 1)[-1].replace('_', ' ').title()}</b> — {text}")
                label.setWordWrap(True)
                group_layout.addWidget(label)
                rows.append((label, f"{key} {text}".lower()))
            content_layout.addWidget(group)
            self._groups.append((group, rows))

        content_layout.addStretch(1)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(content)

        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("<h2>Help</h2>"))
        layout.addWidget(QLabel(
            "Every setting across the app also has a small (?) icon next to it with the same "
            "explanation shown here, right where you need it."))
        layout.addWidget(self.search_edit)
        layout.addWidget(scroll)

    def _filter(self, text: str):
        text = text.strip().lower()
        for group, rows in self._groups:
            any_visible = False
            for label, haystack in rows:
                visible = text in haystack if text else True
                label.setVisible(visible)
                any_visible = any_visible or visible
            group.setVisible(any_visible)
