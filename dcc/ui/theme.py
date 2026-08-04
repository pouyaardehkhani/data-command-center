"""Dark/light theme QSS, hot-swappable at runtime without restarting the app."""
from __future__ import annotations

from PySide6.QtWidgets import QApplication

_DARK_VARS = {
    "bg": "#1b1f26", "bg_alt": "#20242c", "panel": "#242833",
    "panel_alt": "#2b2f3b", "border": "#333947", "text": "#e7e9ee",
    "text_dim": "#9aa1ae", "accent": "#4f8cff", "accent_hover": "#6a9fff",
    "accent_text": "#ffffff", "danger": "#e5555f", "success": "#3fc57c",
    "sidebar": "#171a20", "input_bg": "#2b2f3b",
}

_LIGHT_VARS = {
    "bg": "#f4f5f7", "bg_alt": "#ffffff", "panel": "#ffffff",
    "panel_alt": "#eef0f3", "border": "#dadde3", "text": "#20242c",
    "text_dim": "#5b6270", "accent": "#3167e8", "accent_hover": "#4d7bf0",
    "accent_text": "#ffffff", "danger": "#d0333c", "success": "#1f9d58",
    "sidebar": "#ffffff", "input_bg": "#ffffff",
}

_QSS_TEMPLATE = """
QWidget {{
    color: {text};
    font-family: "Segoe UI";
    font-size: 13px;
}}
QMainWindow, QDialog {{ background-color: {bg}; }}
QLabel, QCheckBox, QRadioButton, QGroupBox, QSplitter, QStackedWidget {{
    background-color: transparent;
}}
QScrollArea, QScrollArea > QWidget, QScrollArea > QWidget > QWidget {{
    background-color: transparent;
    border: none;
}}

#Sidebar {{
    background-color: {sidebar};
    border-right: 1px solid {border};
}}
#SidebarButton {{
    background-color: transparent;
    color: {text_dim};
    text-align: left;
    padding: 10px 16px;
    border: none;
    border-radius: 8px;
    font-size: 13px;
    font-weight: 600;
}}
#SidebarButton:hover {{ background-color: {panel_alt}; color: {text}; }}
#SidebarButton:checked {{ background-color: {accent}; color: {accent_text}; }}

#TopBar {{ background-color: {bg_alt}; border-bottom: 1px solid {border}; }}
#AppTitle {{ font-size: 15px; font-weight: 700; color: {text}; }}

QFrame#Card, QGroupBox {{
    background-color: {panel};
    border: 1px solid {border};
    border-radius: 10px;
}}
QGroupBox {{
    margin-top: 14px;
    padding: 14px 10px 10px 10px;
    font-weight: 600;
}}
QGroupBox::title {{
    subcontrol-origin: margin;
    left: 10px;
    padding: 0 6px;
    color: {text_dim};
}}

QPushButton {{
    background-color: {panel_alt};
    border: 1px solid {border};
    border-radius: 6px;
    padding: 6px 14px;
    color: {text};
}}
QPushButton:hover {{ background-color: {border}; }}
QPushButton#Primary {{
    background-color: {accent};
    color: {accent_text};
    border: none;
    font-weight: 600;
}}
QPushButton#Primary:hover {{ background-color: {accent_hover}; }}
QPushButton#Danger {{ background-color: {danger}; color: white; border: none; }}
QPushButton:disabled {{ color: {text_dim}; }}

QLineEdit, QSpinBox, QDoubleSpinBox, QComboBox, QTextEdit, QPlainTextEdit {{
    background-color: {input_bg};
    border: 1px solid {border};
    border-radius: 6px;
    padding: 4px 6px;
    min-height: 20px;
    color: {text};
}}
QSpinBox, QDoubleSpinBox {{
    padding-right: 2px;
}}
QAbstractSpinBox::up-button, QAbstractSpinBox::down-button {{
    width: 16px;
    border: none;
}}
QAbstractSpinBox::up-button {{ subcontrol-position: top right; }}
QAbstractSpinBox::down-button {{ subcontrol-position: bottom right; }}
QComboBox {{ padding-right: 22px; }}
QComboBox::drop-down {{
    width: 20px;
    border: none;
}}
QComboBox QAbstractItemView {{
    background-color: {panel};
    border: 1px solid {border};
    selection-background-color: {accent};
    color: {text};
    padding: 2px;
}}
QLineEdit:disabled, QSpinBox:disabled, QDoubleSpinBox:disabled, QComboBox:disabled {{
    color: {text_dim};
    background-color: {panel_alt};
}}
QListWidget, QTreeWidget {{
    background-color: {panel};
    border: 1px solid {border};
    border-radius: 8px;
}}
QListWidget::item:selected {{ background-color: {accent}; color: {accent_text}; }}

QCheckBox, QRadioButton {{ spacing: 8px; }}

QSlider::groove:horizontal {{
    height: 5px;
    background: {border};
    border-radius: 2px;
}}
QSlider::handle:horizontal {{
    background: {accent};
    width: 15px;
    margin: -6px 0;
    border-radius: 7px;
}}

QProgressBar {{
    background-color: {panel_alt};
    border: 1px solid {border};
    border-radius: 6px;
    text-align: center;
    color: {text};
}}
QProgressBar::chunk {{ background-color: {accent}; border-radius: 6px; }}

QTabWidget::pane {{ border: 1px solid {border}; border-radius: 8px; top: -1px; }}
QTabBar::tab {{
    background: transparent;
    padding: 8px 16px;
    color: {text_dim};
    border-bottom: 2px solid transparent;
}}
QTabBar::tab:selected {{ color: {text}; border-bottom: 2px solid {accent}; }}

QScrollBar:vertical {{ background: transparent; width: 10px; }}
QScrollBar::handle:vertical {{ background: {border}; border-radius: 5px; min-height: 24px; }}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0; }}

QToolTip {{
    background-color: {panel_alt};
    color: {text};
    border: 1px solid {border};
    padding: 6px;
}}

#Dock {{ background-color: {bg_alt}; border-top: 1px solid {border}; }}
"""


def qss_for(theme: str) -> str:
    vars_ = _DARK_VARS if theme == "dark" else _LIGHT_VARS
    return _QSS_TEMPLATE.format(**vars_)


def apply_theme(app: QApplication, theme: str) -> None:
    app.setStyleSheet(qss_for(theme))
