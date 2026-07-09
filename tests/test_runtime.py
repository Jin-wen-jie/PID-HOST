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


def test_main_window_switches_between_independent_motor_channels():
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

    from PySide6.QtWidgets import QApplication

    from pid_host.ui.main_window import MainWindow

    app = QApplication.instance() or QApplication([])
    window = MainWindow(demo_mode=False)
    sent: list[tuple[str, dict[str, object]]] = []
    window._send_command = lambda message_type, **fields: sent.append((message_type, fields))

    assert window.channel_combo.currentData() == 0
    window.kp_spin.setValue(1.2)
    window.ki_spin.setValue(0.05)
    window.kd_spin.setValue(0.01)
    window.sp_spin.setValue(50.0)

    window.channel_combo.setCurrentIndex(1)
    assert window.channel_combo.currentData() == 1
    assert window.kp_spin.value() == 1.0
    assert window.ki_spin.value() == 0.0
    assert window.kd_spin.value() == 0.0
    assert window.sp_spin.value() == 50.0

    window.kp_spin.setValue(0.8)
    window.ki_spin.setValue(0.03)
    window.kd_spin.setValue(0.02)
    window.sp_spin.setValue(80.0)
    window.send_pid()
    window.send_sp()

    assert sent == [
        ("set_pid", {"ch": 1, "kp": 0.8, "ki": 0.03, "kd": 0.02}),
        ("set_sp", {"ch": 1, "sp": 80.0}),
    ]

    window.channel_combo.setCurrentIndex(0)
    assert window.kp_spin.value() == 1.2
    assert window.ki_spin.value() == 0.05
    assert window.kd_spin.value() == 0.01
    assert window.sp_spin.value() == 50.0

    window.close()
    app.processEvents()


def test_main_window_filters_latest_values_and_plot_by_selected_motor_channel():
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

    from PySide6.QtWidgets import QApplication

    from pid_host.data import TelemetrySample
    from pid_host.ui.main_window import MainWindow

    app = QApplication.instance() or QApplication([])
    window = MainWindow(demo_mode=False)

    window.add_telemetry(
        TelemetrySample("2026-07-09T10:00:00.000", device_time_ms=1000, ch=0, sp=50.0, pv=48.0, out=30.0)
    )
    window.add_telemetry(
        TelemetrySample("2026-07-09T10:00:00.100", device_time_ms=1100, ch=1, sp=80.0, pv=75.0, out=45.0)
    )

    assert window.current_sp_label.text() == "50"
    assert window.current_pv_label.text() == "48"
    assert window.current_out_label.text() == "30"

    window.channel_combo.setCurrentIndex(1)
    assert window.current_sp_label.text() == "80"
    assert window.current_pv_label.text() == "75"
    assert window.current_out_label.text() == "45"

    window.refresh_plot()
    x, y = window.curve_sp.getData()
    assert list(x) == [1.1]
    assert list(y) == [80.0]

    window.close()
    app.processEvents()
