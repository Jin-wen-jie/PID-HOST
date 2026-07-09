from __future__ import annotations

import queue
import time

from PySide6.QtCore import QThread, Signal


class SerialWorker(QThread):
    line_received = Signal(str)
    connected = Signal(str)
    disconnected = Signal()
    error = Signal(str)
    raw_tx = Signal(str)

    def __init__(self, port: str, baudrate: int = 115200) -> None:
        super().__init__()
        self.port = port
        self.baudrate = baudrate
        self._running = False
        self._writes: queue.Queue[str] = queue.Queue()

    def send_line(self, line: str) -> None:
        self._writes.put(line)
        self.raw_tx.emit(line.rstrip("\r\n"))

    def stop(self) -> None:
        self._running = False
        self.requestInterruption()

    def run(self) -> None:
        try:
            import serial
        except ImportError as exc:
            self.error.emit("pyserial is not installed")
            self.disconnected.emit()
            return

        try:
            with serial.Serial(
                self.port,
                self.baudrate,
                bytesize=serial.EIGHTBITS,
                parity=serial.PARITY_NONE,
                stopbits=serial.STOPBITS_ONE,
                timeout=0.05,
                write_timeout=0.2,
                xonxoff=False,
                rtscts=False,
                dsrdtr=False,
            ) as ser:
                self._running = True
                self.connected.emit(self.port)
                while self._running and not self.isInterruptionRequested():
                    self._drain_writes(ser)
                    line = ser.readline()
                    if line:
                        try:
                            self.line_received.emit(line.decode("utf-8", errors="replace"))
                        except UnicodeDecodeError as exc:
                            self.error.emit(str(exc))
                    else:
                        time.sleep(0.005)
        except Exception as exc:  # pragma: no cover - depends on hardware/driver
            self.error.emit(str(exc))
        finally:
            self._running = False
            self.disconnected.emit()

    def _drain_writes(self, ser: object) -> None:
        while True:
            try:
                line = self._writes.get_nowait()
            except queue.Empty:
                return
            ser.write(line.encode("utf-8"))
