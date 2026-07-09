from __future__ import annotations

from datetime import datetime
from pathlib import Path

import pyqtgraph as pg
from PySide6.QtCore import QTimer
from PySide6.QtWidgets import (
    QAbstractSpinBox,
    QCheckBox,
    QComboBox,
    QDoubleSpinBox,
    QFileDialog,
    QFormLayout,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QSizePolicy,
    QTextEdit,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from ..config import AppConfig
from ..data import CsvRecorder, TelemetryBuffer, TelemetrySample
from ..protocol import (
    AckMessage,
    CommandTracker,
    ErrorMessage,
    HelloMessage,
    ProtocolError,
    TelemetryMessage,
    encode_command,
    parse_incoming,
    validate_pid_values,
    validate_setpoint,
    validate_stream_rate,
)
from ..serial_link import SerialWorker
from ..simulator import DemoGenerator


class MainWindow(QMainWindow):
    def __init__(self, demo_mode: bool = False) -> None:
        super().__init__()
        self.setWindowTitle("PID-HOST")
        self.demo_mode = demo_mode
        self.config_path = Path("pid_host_config.json")
        self.buffer = TelemetryBuffer(window_seconds=60.0)
        self.recorder = CsvRecorder()
        self.tracker = CommandTracker(timeout_ms=1000)
        self.generator = DemoGenerator()
        self.serial_worker: SerialWorker | None = None
        self.paused = False

        self._build_ui()
        self._apply_style()
        self._connect_signals()
        self.refresh_ports()
        self._load_default_config()

        self.plot_timer = QTimer(self)
        self.plot_timer.setInterval(100)
        self.plot_timer.timeout.connect(self.refresh_plot)
        self.plot_timer.start()

        self.demo_timer = QTimer(self)
        self.demo_timer.setInterval(50)
        self.demo_timer.timeout.connect(self._tick_demo)
        if self.demo_mode:
            self.demo_checkbox.setChecked(True)

    def _build_ui(self) -> None:
        root = QWidget()
        self.setCentralWidget(root)
        outer = QVBoxLayout(root)
        outer.setContentsMargins(12, 10, 12, 10)
        outer.setSpacing(8)

        outer.addLayout(self._build_toolbar())

        body = QHBoxLayout()
        body.setSpacing(10)
        outer.addLayout(body, stretch=1)

        sidebar = self._build_sidebar()
        body.addWidget(sidebar)

        plot_panel = QWidget()
        plot_layout = QVBoxLayout(plot_panel)
        plot_layout.setContentsMargins(0, 0, 0, 0)
        self.plot = pg.PlotWidget()
        self.plot.setBackground("#f8fafc")
        self.plot.showGrid(x=True, y=True, alpha=0.28)
        self.plot.addLegend(offset=(8, 8))
        self.plot.setLabel("bottom", "device time", units="s")
        self.plot.setLabel("left", "value")
        self.curve_sp = self.plot.plot(pen=pg.mkPen("#2563eb", width=2), name="SP")
        self.curve_pv = self.plot.plot(pen=pg.mkPen("#16a34a", width=2), name="PV")
        self.curve_out = self.plot.plot(pen=pg.mkPen("#dc2626", width=2), name="OUT")
        plot_layout.addWidget(self.plot)
        body.addWidget(plot_panel, stretch=1)

        self.log_view = QTextEdit()
        self.log_view.setReadOnly(True)
        self.log_view.setFixedHeight(140)
        outer.addWidget(self.log_view)

    def _build_toolbar(self) -> QHBoxLayout:
        layout = QHBoxLayout()
        layout.setSpacing(8)
        self.port_combo = QComboBox()
        self.port_combo.setMinimumWidth(150)
        self.refresh_button = QPushButton("刷新串口")
        self.baud_combo = QComboBox()
        self.baud_combo.addItems(["9600", "19200", "38400", "57600", "115200", "230400"])
        self.baud_combo.setCurrentText("115200")
        self.connect_button = QPushButton("连接")
        self.demo_checkbox = QCheckBox("模拟模式")
        self.status_label = QLabel("未连接")
        self.device_label = QLabel("设备：-")
        self.record_button = QPushButton("开始录制")
        self.save_config_button = QPushButton("保存参数")
        self.load_config_button = QPushButton("加载参数")

        for widget in (
            self.port_combo,
            self.refresh_button,
            self.baud_combo,
            self.connect_button,
            self.demo_checkbox,
            self.status_label,
            self.device_label,
            self.record_button,
            self.save_config_button,
            self.load_config_button,
        ):
            layout.addWidget(widget)
        layout.addStretch(1)
        return layout

    def _build_sidebar(self) -> QWidget:
        panel = QFrame()
        panel.setObjectName("sidebar")
        panel.setFixedWidth(250)
        panel.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Expanding)
        layout = QVBoxLayout(panel)
        layout.setSpacing(10)

        form = QFormLayout()
        step_row, self.step_spin, self.step_decrease_button, self.step_increase_button = self._step_control()
        kp_row, self.kp_spin, self.kp_decrease_button, self.kp_increase_button = self._parameter_control(1.0)
        ki_row, self.ki_spin, self.ki_decrease_button, self.ki_increase_button = self._parameter_control(0.0)
        kd_row, self.kd_spin, self.kd_decrease_button, self.kd_increase_button = self._parameter_control(0.0)
        sp_row, self.sp_spin, self.sp_decrease_button, self.sp_increase_button = self._parameter_control(50.0)
        form.addRow("步长", step_row)
        form.addRow("Kp", kp_row)
        form.addRow("Ki", ki_row)
        form.addRow("Kd", kd_row)
        form.addRow("SP", sp_row)
        layout.addLayout(form)

        self.send_pid_button = QPushButton("发送 PID")
        self.send_sp_button = QPushButton("发送目标值")
        layout.addWidget(self.send_pid_button)
        layout.addWidget(self.send_sp_button)

        values = QGridLayout()
        self.current_sp_label = QLabel("-")
        self.current_pv_label = QLabel("-")
        self.current_out_label = QLabel("-")
        values.addWidget(QLabel("SP"), 0, 0)
        values.addWidget(self.current_sp_label, 0, 1)
        values.addWidget(QLabel("PV"), 1, 0)
        values.addWidget(self.current_pv_label, 1, 1)
        values.addWidget(QLabel("OUT"), 2, 0)
        values.addWidget(self.current_out_label, 2, 1)
        layout.addLayout(values)

        self.pause_button = QPushButton("暂停曲线")
        self.clear_button = QPushButton("清空曲线")
        self.raw_checkbox = QCheckBox("显示原始帧")
        layout.addWidget(self.pause_button)
        layout.addWidget(self.clear_button)
        layout.addWidget(self.raw_checkbox)
        layout.addStretch(1)
        return panel

    def _double_spin(self, value: float) -> QDoubleSpinBox:
        spin = QDoubleSpinBox()
        spin.setDecimals(4)
        spin.setRange(-1_000_000.0, 1_000_000.0)
        spin.setValue(value)
        spin.setSingleStep(self.step_spin.value())
        spin.setButtonSymbols(QAbstractSpinBox.ButtonSymbols.NoButtons)
        return spin

    def _step_spin(self) -> QDoubleSpinBox:
        spin = QDoubleSpinBox()
        spin.setDecimals(4)
        spin.setRange(0.0001, 1000.0)
        spin.setValue(0.02)
        spin.setSingleStep(0.01)
        spin.setButtonSymbols(QAbstractSpinBox.ButtonSymbols.NoButtons)
        spin.valueChanged.connect(self._update_parameter_step)
        return spin

    def _step_control(self) -> tuple[QWidget, QDoubleSpinBox, QToolButton, QToolButton]:
        row = QWidget()
        layout = QHBoxLayout(row)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)

        spin = self._step_spin()
        decrease = self._step_button("-", "减少步长")
        increase = self._step_button("+", "增加步长")
        decrease.clicked.connect(lambda _checked=False, target=spin: target.stepDown())
        increase.clicked.connect(lambda _checked=False, target=spin: target.stepUp())
        layout.addWidget(spin, stretch=1)
        layout.addWidget(decrease)
        layout.addWidget(increase)
        return row, spin, decrease, increase

    def _parameter_control(self, value: float) -> tuple[QWidget, QDoubleSpinBox, QToolButton, QToolButton]:
        row = QWidget()
        layout = QHBoxLayout(row)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)

        spin = self._double_spin(value)
        decrease = self._step_button("-", "减少参数")
        increase = self._step_button("+", "增加参数")
        decrease.clicked.connect(lambda _checked=False, target=spin: target.stepDown())
        increase.clicked.connect(lambda _checked=False, target=spin: target.stepUp())
        layout.addWidget(spin, stretch=1)
        layout.addWidget(decrease)
        layout.addWidget(increase)
        return row, spin, decrease, increase

    def _step_button(self, text: str, tooltip: str) -> QToolButton:
        button = QToolButton()
        button.setObjectName("paramStepButton")
        button.setText(text)
        button.setToolTip(tooltip)
        button.setAutoRepeat(True)
        button.setFixedWidth(28)
        return button

    def _update_parameter_step(self, step: float) -> None:
        for spin in (
            getattr(self, "kp_spin", None),
            getattr(self, "ki_spin", None),
            getattr(self, "kd_spin", None),
            getattr(self, "sp_spin", None),
        ):
            if spin is not None:
                spin.setSingleStep(step)

    def _apply_style(self) -> None:
        self.setStyleSheet(
            """
            QMainWindow, QWidget { background: #eef2f7; color: #172033; font-size: 13px; }
            QPushButton { background: #ffffff; border: 1px solid #b9c2cf; border-radius: 4px; padding: 6px 10px; }
            QPushButton:hover { border-color: #2563eb; }
            QPushButton:disabled { color: #8a94a6; background: #edf1f5; }
            QToolButton#paramStepButton { background: #ffffff; border: 1px solid #b9c2cf; border-radius: 4px; padding: 4px; font-weight: 700; }
            QToolButton#paramStepButton:hover { border-color: #2563eb; color: #0f5132; }
            QToolButton#paramStepButton:pressed { background: #dbeafe; }
            QComboBox, QDoubleSpinBox { background: #ffffff; border: 1px solid #b9c2cf; border-radius: 4px; padding: 4px; }
            QFrame#sidebar { background: #f8fafc; border: 1px solid #cbd5e1; border-radius: 6px; }
            QTextEdit { background: #101827; color: #d5e1f5; border: 1px solid #263247; border-radius: 4px; font-family: Consolas, monospace; }
            QLabel { background: transparent; }
            """
        )

    def _connect_signals(self) -> None:
        self.refresh_button.clicked.connect(self.refresh_ports)
        self.connect_button.clicked.connect(self.toggle_connection)
        self.record_button.clicked.connect(self.toggle_recording)
        self.save_config_button.clicked.connect(self.save_config)
        self.load_config_button.clicked.connect(self.load_config)
        self.send_pid_button.clicked.connect(self.send_pid)
        self.send_sp_button.clicked.connect(self.send_sp)
        self.pause_button.clicked.connect(self.toggle_pause)
        self.clear_button.clicked.connect(self.clear_plot)
        self.demo_checkbox.toggled.connect(self._set_demo_mode)

    def refresh_ports(self) -> None:
        current = self.port_combo.currentText()
        self.port_combo.clear()
        try:
            from serial.tools import list_ports

            ports = [port.device for port in list_ports.comports()]
        except Exception:
            ports = []
        self.port_combo.addItems(ports)
        if current:
            index = self.port_combo.findText(current)
            if index >= 0:
                self.port_combo.setCurrentIndex(index)

    def toggle_connection(self) -> None:
        if self.serial_worker is not None:
            self.disconnect_serial()
            return
        if self.demo_checkbox.isChecked():
            self.start_demo()
            return
        port = self.port_combo.currentText().strip()
        if not port:
            self._show_error("没有可用串口")
            return
        self.serial_worker = SerialWorker(port, int(self.baud_combo.currentText()))
        self.serial_worker.connected.connect(self._on_serial_connected)
        self.serial_worker.disconnected.connect(self._on_serial_disconnected)
        self.serial_worker.error.connect(self._on_serial_error)
        self.serial_worker.line_received.connect(self._on_line_received)
        self.serial_worker.raw_tx.connect(lambda line: self._log_raw("TX", line))
        self.serial_worker.start()

    def disconnect_serial(self) -> None:
        worker = self.serial_worker
        self.serial_worker = None
        if worker is not None:
            worker.stop()
            worker.wait(1000)
        self.status_label.setText("未连接")
        self.connect_button.setText("连接")
        self.recorder.stop()
        self.record_button.setText("开始录制")

    def _on_serial_connected(self, port: str) -> None:
        self.status_label.setText(f"已连接 {port}")
        self.connect_button.setText("断开")
        self.log("串口已连接")
        self._send_command("hello")

    def _on_serial_disconnected(self) -> None:
        self.serial_worker = None
        self.status_label.setText("未连接")
        self.connect_button.setText("连接")
        if self.recorder.is_recording:
            self.recorder.stop()
            self.record_button.setText("开始录制")
        self.log("串口已断开")

    def _on_serial_error(self, message: str) -> None:
        self.log(f"串口错误：{message}")

    def _on_line_received(self, line: str) -> None:
        self._log_raw("RX", line.rstrip("\r\n"))
        try:
            message = parse_incoming(line)
        except ProtocolError as exc:
            self.log(f"协议错误：{exc.code} {exc.message}")
            return
        if isinstance(message, TelemetryMessage):
            self.add_telemetry(
                TelemetrySample(
                    pc_time=datetime.now().isoformat(timespec="milliseconds"),
                    device_time_ms=message.t,
                    ch=message.ch,
                    sp=message.sp,
                    pv=message.pv,
                    out=message.out,
                )
            )
        elif isinstance(message, HelloMessage):
            self.tracker.handle_response(AckMessage(seq=message.seq))
            self.device_label.setText(f"设备：{message.device} / fw {message.fw} / proto {message.proto}")
            self.log("握手成功")
            self._send_command("stream", enabled=True, rate_hz=20)
        elif isinstance(message, AckMessage):
            command = self.tracker.handle_response(message)
            self.log(f"ACK：{command or message.seq}")
        elif isinstance(message, ErrorMessage):
            command = self.tracker.handle_response(message)
            self.log(f"ERR：{command or message.seq} {message.code} {message.message}")

    def _send_command(self, message_type: str, **fields: object) -> None:
        now_ms = int(datetime.now().timestamp() * 1000)
        try:
            seq = self.tracker.start(message_type, now_ms=now_ms)
        except ProtocolError as exc:
            self.log(f"命令未发送：{exc.message}")
            return
        line = encode_command(message_type, seq=seq, **fields)
        if self.serial_worker is not None:
            self.serial_worker.send_line(line)
        elif self.demo_checkbox.isChecked():
            self._handle_demo_command(message_type, seq, fields)
        else:
            self.log("命令未发送：未连接")
            self.tracker.handle_response(ErrorMessage(seq=seq, code="busy", message="not connected"))
            return
        self.log(f"发送：{line.strip()}")

    def _handle_demo_command(self, message_type: str, seq: int, fields: dict[str, object]) -> None:
        if message_type == "set_sp":
            self.generator.set_sp(float(fields["sp"]))
        self.tracker.handle_response(AckMessage(seq=seq))
        self.log(f"模拟 ACK：{message_type}")

    def send_pid(self) -> None:
        kp, ki, kd = self.kp_spin.value(), self.ki_spin.value(), self.kd_spin.value()
        try:
            validate_pid_values(ch=0, kp=kp, ki=ki, kd=kd)
        except ProtocolError as exc:
            self._show_error(exc.message)
            return
        self._send_command("set_pid", ch=0, kp=kp, ki=ki, kd=kd)

    def send_sp(self) -> None:
        sp = self.sp_spin.value()
        try:
            validate_setpoint(ch=0, sp=sp)
        except ProtocolError as exc:
            self._show_error(exc.message)
            return
        self._send_command("set_sp", ch=0, sp=sp)

    def start_demo(self) -> None:
        self.demo_mode = True
        self.status_label.setText("模拟模式")
        self.connect_button.setText("模拟中")
        if not self.demo_timer.isActive():
            self.demo_timer.start()
        self.log("模拟数据模式已启动")

    def _set_demo_mode(self, enabled: bool) -> None:
        if enabled:
            self.disconnect_serial()
            self.start_demo()
        else:
            self.demo_mode = False
            self.demo_timer.stop()
            self.status_label.setText("未连接")
            self.connect_button.setText("连接")
            self.log("模拟数据模式已停止")

    def _tick_demo(self) -> None:
        self.add_telemetry(self.generator.next_sample())

    def add_telemetry(self, sample: TelemetrySample) -> None:
        self.buffer.add(sample)
        self.current_sp_label.setText(f"{sample.sp:.4g}")
        self.current_pv_label.setText(f"{sample.pv:.4g}")
        self.current_out_label.setText(f"{sample.out:.4g}")
        if self.recorder.is_recording:
            self.recorder.write(sample)

    def refresh_plot(self) -> None:
        timed_out = self.tracker.check_timeout(int(datetime.now().timestamp() * 1000))
        if timed_out:
            self.log(f"命令超时：{timed_out}")
        if self.paused:
            return
        x, sp, pv, out = self.buffer.series()
        self.curve_sp.setData(x, sp)
        self.curve_pv.setData(x, pv)
        self.curve_out.setData(x, out)

    def toggle_pause(self) -> None:
        self.paused = not self.paused
        self.pause_button.setText("继续曲线" if self.paused else "暂停曲线")

    def clear_plot(self) -> None:
        self.buffer.clear()
        self.refresh_plot()
        self.log("曲线已清空")

    def toggle_recording(self) -> None:
        if self.recorder.is_recording:
            self.recorder.stop()
            self.record_button.setText("开始录制")
            self.log("CSV 录制已停止")
            return
        default = Path("recordings") / f"pid_log_{datetime.now():%Y%m%d_%H%M%S}.csv"
        path, _ = QFileDialog.getSaveFileName(self, "保存 CSV", str(default), "CSV files (*.csv)")
        if not path:
            return
        self.recorder.start(path)
        self.record_button.setText("停止录制")
        self.log(f"CSV 录制开始：{path}")

    def save_config(self) -> None:
        config = self._current_config()
        path, _ = QFileDialog.getSaveFileName(self, "保存参数配置", str(self.config_path), "JSON files (*.json)")
        if not path:
            return
        config.save(path)
        self.log(f"参数配置已保存：{path}")

    def load_config(self) -> None:
        path, _ = QFileDialog.getOpenFileName(self, "加载参数配置", str(self.config_path), "JSON files (*.json)")
        if not path:
            return
        config = AppConfig.load(path)
        self._apply_config(config)
        self.log(f"参数配置已加载：{path}")

    def _load_default_config(self) -> None:
        if self.config_path.exists():
            self._apply_config(AppConfig.load(self.config_path))

    def _current_config(self) -> AppConfig:
        return AppConfig(
            port=self.port_combo.currentText(),
            baudrate=int(self.baud_combo.currentText()),
            kp=self.kp_spin.value(),
            ki=self.ki_spin.value(),
            kd=self.kd_spin.value(),
            sp=self.sp_spin.value(),
            raw_frames_visible=self.raw_checkbox.isChecked(),
        )

    def _apply_config(self, config: AppConfig) -> None:
        if config.port and self.port_combo.findText(config.port) < 0:
            self.port_combo.addItem(config.port)
        if config.port:
            self.port_combo.setCurrentText(config.port)
        self.baud_combo.setCurrentText(str(config.baudrate))
        self.kp_spin.setValue(config.kp)
        self.ki_spin.setValue(config.ki)
        self.kd_spin.setValue(config.kd)
        self.sp_spin.setValue(config.sp)
        self.raw_checkbox.setChecked(config.raw_frames_visible)

    def log(self, message: str) -> None:
        self.log_view.append(f"{datetime.now():%H:%M:%S}  {message}")

    def _log_raw(self, direction: str, line: str) -> None:
        if self.raw_checkbox.isChecked():
            self.log(f"{direction} {line}")

    def _show_error(self, message: str) -> None:
        self.log(f"错误：{message}")
        QMessageBox.warning(self, "PID-HOST", message)

    def closeEvent(self, event: object) -> None:
        self.recorder.stop()
        self.disconnect_serial()
        super().closeEvent(event)
