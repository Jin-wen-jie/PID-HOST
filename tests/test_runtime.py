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

    assert window.pid_step_spin.value() == 0.02
    assert window.sp_step_spin.value() == 1.0
    window.pid_step_increase_button.click()
    assert window.pid_step_spin.value() == 0.03
    window.pid_step_decrease_button.click()
    assert window.pid_step_spin.value() == 0.02

    start = window.kp_spin.value()
    window.kp_increase_button.click()
    assert window.kp_spin.value() == start + 0.02

    increased = window.kp_spin.value()
    window.kp_decrease_button.click()
    assert window.kp_spin.value() < increased
    assert window.kp_spin.value() == start

    row_layout = window.kp_spin.parentWidget().layout()
    assert row_layout.itemAt(0).widget() is window.kp_spin
    assert row_layout.itemAt(1).widget() is window.kp_decrease_button
    assert row_layout.itemAt(2).widget() is window.kp_increase_button

    sp_start = window.sp_spin.value()
    window.sp_increase_button.click()
    assert window.sp_spin.value() == sp_start + 1.0

    window.sp_step_decrease_button.click()
    assert window.sp_step_spin.value() == 0.9
    assert window.kp_spin.singleStep() == 0.02
    sp_after_step_change = window.sp_spin.value()
    window.sp_increase_button.click()
    assert window.sp_spin.value() == sp_after_step_change + 0.9

    pid_step_layout = window.pid_step_spin.parentWidget().layout()
    assert pid_step_layout.itemAt(0).widget() is window.pid_step_spin
    assert pid_step_layout.itemAt(1).widget() is window.pid_step_decrease_button
    assert pid_step_layout.itemAt(2).widget() is window.pid_step_increase_button

    sp_step_layout = window.sp_step_spin.parentWidget().layout()
    assert sp_step_layout.itemAt(0).widget() is window.sp_step_spin
    assert sp_step_layout.itemAt(1).widget() is window.sp_step_decrease_button
    assert sp_step_layout.itemAt(2).widget() is window.sp_step_increase_button

    window.close()
    app.processEvents()
