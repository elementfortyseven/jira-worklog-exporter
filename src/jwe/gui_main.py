"""GUI entry point — creates QApplication and launches MainWindow."""

from __future__ import annotations

import sys


def main(lang: str | None = None) -> int:
    """Start the PySide6 GUI. Returns the process exit code."""
    from PySide6.QtWidgets import QApplication

    from jwe.gui.main_window import MainWindow

    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    window = MainWindow(initial_lang=lang)
    window.show()
    return app.exec()
