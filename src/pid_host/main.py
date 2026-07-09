from __future__ import annotations

import argparse
import os
import sys

from PySide6.QtWidgets import QApplication

from . import __version__
from .ui.main_window import MainWindow


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="PID-HOST desktop PID tuning application.")
    parser.add_argument("--demo", action="store_true", help="start with simulated SP/PV/OUT data")
    parser.add_argument("--version", action="store_true", help="print version and exit")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.version:
        print(f"PID-HOST {__version__}")
        return 0

    os.environ.setdefault("QT_ENABLE_HIGHDPI_SCALING", "1")
    app = QApplication(sys.argv[:1])
    window = MainWindow(demo_mode=args.demo)
    window.resize(1280, 780)
    window.show()
    return app.exec()
