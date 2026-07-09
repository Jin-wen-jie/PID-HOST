import os
import subprocess
import sys
from pathlib import Path


def test_module_cli_prints_version():
    env = os.environ.copy()
    env["PYTHONPATH"] = str(Path("src").resolve())
    result = subprocess.run(
        [sys.executable, "-m", "pid_host", "--version"],
        check=True,
        capture_output=True,
        text=True,
        env=env,
    )

    assert "PID-HOST 0.1.0" in result.stdout


def test_main_window_constructs_in_offscreen_demo_mode():
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

    from PySide6.QtWidgets import QApplication

    from pid_host.ui.main_window import MainWindow

    app = QApplication.instance() or QApplication([])
    window = MainWindow(demo_mode=True)

    assert window.windowTitle() == "PID-HOST"
    window.close()
    app.processEvents()


def test_pid_parameter_step_buttons_increase_and_decrease_values():
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

    from PySide6.QtWidgets import QApplication

    from pid_host.ui.main_window import MainWindow

    app = QApplication.instance() or QApplication([])
    window = MainWindow(demo_mode=False)

    start = window.kp_spin.value()
    window.kp_increase_button.click()
    assert window.kp_spin.value() > start

    increased = window.kp_spin.value()
    window.kp_decrease_button.click()
    assert window.kp_spin.value() < increased

    window.close()
    app.processEvents()
