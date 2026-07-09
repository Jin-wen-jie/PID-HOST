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
    QTabWidget,
    QTextEdit,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from ..config import AppConfig, PidChannelConfig
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
        self.channel_values = {0: PidChannelConfig(ch=0), 1: PidChannelConfig(ch=1)}
        self.current_channel = 0
        self._loading_channel = False

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
        panel.setFixedWidth(310)
        panel.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Expanding)
        layout = QVBoxLayout(panel)
        layout.setSpacing(10)

        self.motor_tabs = QTabWidget()
        self.motor_tabs.setObjectName("motorTabs")
        self.channel_summary_labels: dict[int, dict[str, QLabel]] = {}
        self.motor_tabs.addTab(self._build_motor_tab(0), "电机1")
        self.motor_tabs.addTab(self._build_motor_tab(1), "电机2")
        layout.addWidget(self.motor_tabs)

        form = QFormLayout()
        (
            pid_step_row,
            self.pid_step_spin,
            self.pid_step_decrease_button,
            self.pid_step_increase_button,
        ) = self._step_control(default_value=0.02, step_value=0.01, tooltip_name="PID步长")
        self.pid_step_spin.valueChanged.connect(self._update_parameter_step)
        kp_row, self.kp_spin, self.kp_decrease_button, self.kp_increase_button = self._parameter_control(1.0)
        ki_row, self.ki_spin, self.ki_decrease_button, self.ki_increase_button = self._parameter_control(0.0)
        kd_row, self.kd_spin, self.kd_decrease_button, self.kd_increase_button = self._parameter_control(0.0)
        (
            sp_step_row,
            self.sp_step_spin,
            self.sp_step_decrease_button,
            self.sp_step_increase_button,
        ) = self._step_control(default_value=1.0, step_value=0.1, tooltip_name="SP步长")
        self.step_spin = self.pid_step_spin
        self.step_decrease_button = self.pid_step_decrease_button
        self.step_increase_button = self.pid_step_increase_button
        sp_row, self.sp_spin, self.sp_decrease_button, self.sp_increase_button = self._parameter_control(
            50.0,
            self.sp_step_spin.value(),
        )
        self.sp_step_spin.valueChanged.connect(self._update_sp_step)
        form.addRow("PID步长", pid_step_row)
        form.addRow("Kp", kp_row)
        form.addRow("Ki", ki_row)
        form.addRow("Kd", kd_row)
        form.addRow("SP步长", sp_step_row)
        form.addRow("SP", sp_row)
        layout.addLayout(form)

        self.send_pid_button = QPushButton("发送 PID")
        self.send_pid_button.setObjectName("primaryAction")
        self.send_sp_button = QPushButton("发送目标值")
        self.send_sp_button.setObjectName("primaryAction")
        self.copy_to_other_button = QPushButton("复制到另一个电机")
        self.copy_to_other_button.setObjectName("secondaryAction")
        action_row = QGridLayout()
        action_row.setSpacing(6)
        action_row.addWidget(self.send_pid_button, 0, 0)
        action_row.addWidget(self.send_sp_button, 0, 1)
        action_row.addWidget(self.copy_to_other_button, 1, 0, 1, 2)
        layout.addLayout(action_row)

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

    def _build_motor_tab(self, ch: int) -> QWidget:
        tab = QWidget()
        layout = QGridLayout(tab)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setHorizontalSpacing(10)
        layout.setVerticalSpacing(5)

        labels: dict[str, QLabel] = {}
        rows = (
            ("channel", "通道", f"CH{ch}"),
            ("kp", "Kp", "-"),
            ("ki", "Ki", "-"),
            ("kd", "Kd", "-"),
            ("sp", "SP", "-"),
            ("pv", "PV", "-"),
            ("out", "OUT", "-"),
        )
        for row, (key, name, value) in enumerate(rows):
            name_label = QLabel(name)
            name_label.setObjectName("summaryName")
            value_label = QLabel(value)
            value_label.setObjectName("summaryValue")
            labels[key] = value_label
            layout.addWidget(name_label, row, 0)
            layout.addWidget(value_label, row, 1)
        self.channel_summary_labels[ch] = labels
        self._sync_channel_summary(ch)
        return tab

    def _sync_channel_summary(self, ch: int) -> None:
        labels = getattr(self, "channel_summary_labels", {}).get(ch)
        if labels is None:
            return
        values = self.channel_values.get(ch, PidChannelConfig(ch=ch))
        labels["channel"].setText(f"CH{ch}")
        labels["kp"].setText(self._format_value(values.kp))
        labels["ki"].setText(self._format_value(values.ki))
        labels["kd"].setText(self._format_value(values.kd))
        labels["sp"].setText(self._format_value(values.sp))
        latest = self.buffer.latest(ch=ch)
        if latest is not None:
            labels["pv"].setText(self._format_value(latest.pv))
            labels["out"].setText(self._format_value(latest.out))

    def _format_value(self, value: float) -> str:
        return f"{value:.4g}"

    def _double_spin(self, value: float, step: float | None = None) -> QDoubleSpinBox:
        spin = QDoubleSpinBox()
        spin.setDecimals(4)
        spin.setRange(-1_000_000.0, 1_000_000.0)
        spin.setValue(value)
        spin.setSingleStep(step if step is not None else self.pid_step_spin.value())
        spin.setButtonSymbols(QAbstractSpinBox.ButtonSymbols.NoButtons)
        return spin

    def _step_spin(self, default_value: float, step_value: float) -> QDoubleSpinBox:
        spin = QDoubleSpinBox()
        spin.setDecimals(4)
        spin.setRange(0.0001, 1000.0)
        spin.setValue(default_value)
        spin.setSingleStep(step_value)
        spin.setButtonSymbols(QAbstractSpinBox.ButtonSymbols.NoButtons)
        return spin

    def _step_control(
        self,
        default_value: float,
        step_value: float,
        tooltip_name: str,
    ) -> tuple[QWidget, QDoubleSpinBox, QToolButton, QToolButton]:
        row = QWidget()
        layout = QHBoxLayout(row)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)

        spin = self._step_spin(default_value, step_value)
        decrease = self._step_button("-", f"减少{tooltip_name}")
        increase = self._step_button("+", f"增加{tooltip_name}")
        decrease.clicked.connect(lambda _checked=False, target=spin: target.stepDown())
        increase.clicked.connect(lambda _checked=False, target=spin: target.stepUp())
        layout.addWidget(spin, stretch=1)
        layout.addWidget(decrease)
        layout.addWidget(increase)
        return row, spin, decrease, increase

    def _parameter_control(
        self,
        value: float,
        step: float | None = None,
    ) -> tuple[QWidget, QDoubleSpinBox, QToolButton, QToolButton]:
        row = QWidget()
        layout = QHBoxLayout(row)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)

        spin = self._double_spin(value, step)
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
        ):
            if spin is not None:
                spin.setSingleStep(step)

    def _update_sp_step(self, step: float) -> None:
        if hasattr(self, "sp_spin"):
            self.sp_spin.setSingleStep(step)

    def _apply_style(self) -> None:
        self.setStyleSheet(
            """
            QMainWindow, QWidget { background: #eef2f7; color: #172033; font-size: 13px; }
            QPushButton { background: #ffffff; border: 1px solid #b9c2cf; border-radius: 4px; padding: 6px 10px; }
            QPushButton:hover { border-color: #2563eb; }
            QPushButton#primaryAction { background: #123c69; color: #ffffff; border-color: #123c69; font-weight: 600; }
            QPushButton#primaryAction:hover { background: #0f5132; border-color: #0f5132; }
            QPushButton#secondaryAction { background: #fff7ed; border-color: #d97706; color: #7c2d12; }
            QPushButton#secondaryAction:hover { background: #ffedd5; border-color: #b45309; }
            QPushButton:disabled { color: #8a94a6; background: #edf1f5; }
            QToolButton#paramStepButton { background: #ffffff; border: 1px solid #b9c2cf; border-radius: 4px; padding: 4px; font-weight: 700; }
            QToolButton#paramStepButton:hover { border-color: #2563eb; color: #0f5132; }
            QToolButton#paramStepButton:pressed { background: #dbeafe; }
            QComboBox, QDoubleSpinBox { background: #ffffff; border: 1px solid #b9c2cf; border-radius: 4px; padding: 4px; }
            QTabWidget#motorTabs::pane { background: #ffffff; border: 1px solid #cbd5e1; border-radius: 6px; top: -1px; }
            QTabWidget#motorTabs QTabBar::tab { background: #e2e8f0; border: 1px solid #cbd5e1; border-bottom: none; border-top-left-radius: 5px; border-top-right-radius: 5px; padding: 6px 18px; font-weight: 600; }
            QTabWidget#motorTabs QTabBar::tab:selected { background: #ffffff; color: #123c69; border-color: #94a3b8; }
            QLabel#summaryName { color: #5b667a; font-size: 12px; }
            QLabel#summaryValue { color: #172033; font-family: Consolas, monospace; font-weight: 700; }
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
        self.copy_to_other_button.clicked.connect(self.copy_current_to_other_motor)
        self.pause_button.clicked.connect(self.toggle_pause)
        self.clear_button.clicked.connect(self.clear_plot)
        self.demo_checkbox.toggled.connect(self._set_demo_mode)
        self.motor_tabs.currentChanged.connect(self._on_channel_changed)
        self.kp_spin.valueChanged.connect(self._on_parameter_value_changed)
        self.ki_spin.valueChanged.connect(self._on_parameter_value_changed)
        self.kd_spin.valueChanged.connect(self._on_parameter_value_changed)
        self.sp_spin.valueChanged.connect(self._on_parameter_value_changed)

    def _selected_channel(self) -> int:
        return self.motor_tabs.currentIndex()

    def _read_channel_values(self, ch: int) -> PidChannelConfig:
        return PidChannelConfig(
            ch=ch,
            kp=self.kp_spin.value(),
            ki=self.ki_spin.value(),
            kd=self.kd_spin.value(),
            sp=self.sp_spin.value(),
        )

    def _store_current_channel_values(self) -> None:
        self.channel_values[self.current_channel] = self._read_channel_values(self.current_channel)
        self._sync_channel_summary(self.current_channel)

    def _load_channel_values(self, ch: int) -> None:
        values = self.channel_values.get(ch, PidChannelConfig(ch=ch))
        self.kp_spin.setValue(values.kp)
        self.ki_spin.setValue(values.ki)
        self.kd_spin.setValue(values.kd)
        self.sp_spin.setValue(values.sp)
        self._sync_channel_summary(ch)
        self._refresh_latest_values()

    def _on_channel_changed(self, _index: int = -1) -> None:
        if self._loading_channel:
            return
        next_channel = self._selected_channel()
        if next_channel == self.current_channel:
            return
        self._store_current_channel_values()
        self.current_channel = next_channel
        self._load_channel_values(next_channel)
        self.refresh_plot()

    def _on_parameter_value_changed(self, *_args: object) -> None:
        if self._loading_channel:
            return
        self.channel_values[self.current_channel] = self._read_channel_values(self.current_channel)
        self._sync_channel_summary(self.current_channel)

    def copy_current_to_other_motor(self) -> None:
        self._store_current_channel_values()
        target_channel = 1 - self.current_channel
        values = self.channel_values[self.current_channel]
        self.channel_values[target_channel] = PidChannelConfig(
            ch=target_channel,
            kp=values.kp,
            ki=values.ki,
            kd=values.kd,
            sp=values.sp,
        )
        self.generator.set_sp(ch=target_channel, sp=values.sp)
        self._sync_channel_summary(target_channel)

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
            self.generator.set_sp(ch=int(fields["ch"]), sp=float(fields["sp"]))
        self.tracker.handle_response(AckMessage(seq=seq))
        self.log(f"模拟 ACK：{message_type}")

    def send_pid(self) -> None:
        ch = self.current_channel
        kp, ki, kd = self.kp_spin.value(), self.ki_spin.value(), self.kd_spin.value()
        self.channel_values[ch] = PidChannelConfig(ch=ch, kp=kp, ki=ki, kd=kd, sp=self.sp_spin.value())
        try:
            validate_pid_values(ch=ch, kp=kp, ki=ki, kd=kd)
        except ProtocolError as exc:
            self._show_error(exc.message)
            return
        self._send_command("set_pid", ch=ch, kp=kp, ki=ki, kd=kd)

    def send_sp(self) -> None:
        ch = self.current_channel
        sp = self.sp_spin.value()
        self.channel_values[ch] = PidChannelConfig(
            ch=ch,
            kp=self.kp_spin.value(),
            ki=self.ki_spin.value(),
            kd=self.kd_spin.value(),
            sp=sp,
        )
        try:
            validate_setpoint(ch=ch, sp=sp)
        except ProtocolError as exc:
            self._show_error(exc.message)
            return
        self._send_command("set_sp", ch=ch, sp=sp)

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
        for sample in self.generator.next_samples():
            self.add_telemetry(sample)

    def add_telemetry(self, sample: TelemetrySample) -> None:
        self.buffer.add(sample)
        self._sync_channel_summary(sample.ch)
        if sample.ch == self.current_channel:
            self._show_latest_sample(sample)
        if self.recorder.is_recording:
            self.recorder.write(sample)

    def _show_latest_sample(self, sample: TelemetrySample) -> None:
        self.current_sp_label.setText(self._format_value(sample.sp))
        self.current_pv_label.setText(self._format_value(sample.pv))
        self.current_out_label.setText(self._format_value(sample.out))

    def _refresh_latest_values(self) -> None:
        sample = self.buffer.latest(ch=self.current_channel)
        if sample is None:
            self.current_sp_label.setText("-")
            self.current_pv_label.setText("-")
            self.current_out_label.setText("-")
            return
        self._show_latest_sample(sample)

    def refresh_plot(self) -> None:
        timed_out = self.tracker.check_timeout(int(datetime.now().timestamp() * 1000))
        if timed_out:
            self.log(f"命令超时：{timed_out}")
        if self.paused:
            return
        x, sp, pv, out = self.buffer.series(ch=self.current_channel)
        self.curve_sp.setData(x, sp)
        self.curve_pv.setData(x, pv)
        self.curve_out.setData(x, out)

    def toggle_pause(self) -> None:
        self.paused = not self.paused
        self.pause_button.setText("继续曲线" if self.paused else "暂停曲线")

    def clear_plot(self) -> None:
        self.buffer.clear()
        self.refresh_plot()
        self._refresh_latest_values()
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
        self._store_current_channel_values()
        return AppConfig(
            port=self.port_combo.currentText(),
            baudrate=int(self.baud_combo.currentText()),
            selected_ch=self.current_channel,
            channels=tuple(self.channel_values[ch] for ch in sorted(self.channel_values)),
            raw_frames_visible=self.raw_checkbox.isChecked(),
        )

    def _apply_config(self, config: AppConfig) -> None:
        if config.port and self.port_combo.findText(config.port) < 0:
            self.port_combo.addItem(config.port)
        if config.port:
            self.port_combo.setCurrentText(config.port)
        self.baud_combo.setCurrentText(str(config.baudrate))
        self.channel_values = {channel.ch: channel for channel in config.channels}
        for ch in (0, 1):
            self.channel_values.setdefault(ch, PidChannelConfig(ch=ch))
        selected_ch = config.selected_ch if config.selected_ch in self.channel_values else 0
        self._loading_channel = True
        try:
            self.current_channel = selected_ch
            self.motor_tabs.setCurrentIndex(selected_ch)
            self._load_channel_values(selected_ch)
        finally:
            self._loading_channel = False
        for channel in self.channel_values.values():
            self.generator.set_sp(ch=channel.ch, sp=channel.sp)
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
