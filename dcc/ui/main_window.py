"""Main application window: icon sidebar, stacked feature pages, and a
bottom dock showing the shared sequential job queue."""
import qtawesome as qta
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QButtonGroup, QFrame, QHBoxLayout, QLabel, QMainWindow, QPushButton,
    QScrollArea, QSizePolicy, QStackedWidget, QToolButton, QVBoxLayout, QWidget,
)

from dcc import APP_NAME
from dcc.app_context import AppContext
from dcc.core import settings as app_settings
from dcc.ui.pages.audio.converter_page import AudioConverterPage
from dcc.ui.pages.audio.joiner_page import JoinerPage
from dcc.ui.pages.audio.mixer_page import MixerPage
from dcc.ui.pages.help_page import HelpPage
from dcc.ui.pages.picture.converter_page import PictureConverterPage
from dcc.ui.pages.settings_page import SettingsPage
from dcc.ui.pages.video.converter_page import VideoConverterPage
from dcc.ui.pages.video.crop_page import CropPage
from dcc.ui.pages.video.frame_export_page import FrameExportPage
from dcc.ui.pages.video.merger_page import MergerPage
from dcc.ui.pages.video.splitter_page import SplitterPage
from dcc.ui.pages.video.subtitle_page import SubtitlePage
from dcc.ui.pages.video.youtube_downloader_page import YoutubeDownloaderPage
from dcc.ui.widgets.queue_panel import QueuePanel

_NAV_SECTIONS = [
    ("VIDEO", "fa5s.film", [
        ("Converter", "fa5s.exchange-alt", VideoConverterPage),
        ("Add Subtitle", "fa5s.closed-captioning", SubtitlePage),
        ("Merger", "fa5s.object-group", MergerPage),
        ("Splitter", "fa5s.cut", SplitterPage),
        ("Crop", "fa5s.crop-alt", CropPage),
        ("Export Frames", "fa5s.images", FrameExportPage),
        ("YouTube Downloader", "fa5b.youtube", YoutubeDownloaderPage),
    ]),
    ("AUDIO", "fa5s.music", [
        ("Converter", "fa5s.exchange-alt", AudioConverterPage),
        ("Mixer", "fa5s.sliders-h", MixerPage),
        ("Joiner", "fa5s.link", JoinerPage),
    ]),
    ("PICTURE", "fa5s.image", [
        ("Converter", "fa5s.exchange-alt", PictureConverterPage),
    ]),
]


class MainWindow(QMainWindow):
    def __init__(self, ctx: AppContext):
        super().__init__()
        self.ctx = ctx
        self.setWindowTitle(APP_NAME)
        self.resize(1280, 860)

        self.stack = QStackedWidget()
        self.button_group = QButtonGroup(self)
        self.button_group.setExclusive(True)

        sidebar = self._build_sidebar()

        top_bar = self._build_top_bar()

        center = QWidget()
        center_layout = QVBoxLayout(center)
        center_layout.setContentsMargins(0, 0, 0, 0)
        center_layout.setSpacing(0)
        center_layout.addWidget(top_bar)
        center_layout.addWidget(self.stack, 1)
        center_layout.addWidget(QueuePanel(ctx.job_queue))

        root = QWidget()
        root_layout = QHBoxLayout(root)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)
        root_layout.addWidget(sidebar)
        root_layout.addWidget(center, 1)
        self.setCentralWidget(root)

        geometry = app_settings.get_geometry()
        if geometry:
            self.restoreGeometry(geometry)

    def _build_top_bar(self) -> QWidget:
        bar = QFrame()
        bar.setObjectName("TopBar")
        bar.setFixedHeight(52)
        layout = QHBoxLayout(bar)
        layout.setContentsMargins(20, 0, 20, 0)
        title = QLabel(APP_NAME)
        title.setObjectName("AppTitle")
        layout.addWidget(title)
        layout.addStretch(1)
        return bar

    def _build_sidebar(self) -> QWidget:
        sidebar = QFrame()
        sidebar.setObjectName("Sidebar")
        sidebar.setFixedWidth(240)

        content = QWidget()
        layout = QVBoxLayout(content)
        layout.setContentsMargins(10, 16, 10, 16)
        layout.setSpacing(4)

        brand = QLabel(f"  {APP_NAME}")
        brand.setStyleSheet("font-size: 15px; font-weight: 800; padding: 4px 6px 16px 6px;")
        layout.addWidget(brand)

        for section_name, section_icon, items in _NAV_SECTIONS:
            header = QLabel(f"  {section_name}")
            header.setStyleSheet("color: #7a8090; font-size: 11px; font-weight: 700; padding: 12px 6px 4px 6px;")
            layout.addWidget(header)
            for label, icon_name, page_cls in items:
                self._add_nav_button(layout, label, icon_name, page_cls)

        layout.addStretch(1)

        for label, icon_name, page_cls in (("Settings", "fa5s.cog", SettingsPage), ("Help", "fa5s.question-circle", HelpPage)):
            self._add_nav_button(layout, label, icon_name, page_cls, bottom=True)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(content)
        scroll.setFrameShape(QFrame.Shape.NoFrame)

        outer = QVBoxLayout(sidebar)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.addWidget(scroll)
        return sidebar

    def _add_nav_button(self, layout: QVBoxLayout, label: str, icon_name: str, page_cls, bottom: bool = False):
        btn = QToolButton()
        btn.setObjectName("SidebarButton")
        btn.setText(f"  {label}")
        btn.setIcon(qta.icon(icon_name, color="#9aa1ae"))
        btn.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextBesideIcon)
        btn.setCheckable(True)
        btn.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        btn.setMinimumHeight(34)

        if page_cls is HelpPage:
            page = HelpPage()
        else:
            page = page_cls(self.ctx)
        index = self.stack.addWidget(page)
        btn.clicked.connect(lambda: self.stack.setCurrentIndex(index))
        self.button_group.addButton(btn)
        layout.addWidget(btn)

        if self.stack.count() == 1:
            btn.setChecked(True)

    def closeEvent(self, event):
        app_settings.set_geometry(self.saveGeometry())
        super().closeEvent(event)
