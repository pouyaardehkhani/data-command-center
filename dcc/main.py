import sys

from PySide6.QtWidgets import QApplication

from dcc import APP_NAME
from dcc.app_context import build_context
from dcc.core import settings as app_settings
from dcc.ui.main_window import MainWindow
from dcc.ui.theme import apply_theme


def main():
    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    # Force Fusion: our custom QSS (combo/spin box subcontrol styling in
    # particular) was designed and tested against Fusion. Left on the native
    # Windows style ("windowsvista"), Qt's subcontrol hit-testing for things
    # like the combo-box dropdown arrow becomes unreliable when combined with
    # a custom stylesheet - this is what broke dropdown popups app-wide.
    app.setStyle("Fusion")
    apply_theme(app, app_settings.get_theme())

    ctx = build_context()
    window = MainWindow(ctx)
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
