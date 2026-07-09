from __future__ import annotations

import math
from datetime import datetime

from .data import TelemetrySample


class DemoGenerator:
    def __init__(self, sp: float = 50.0, interval_ms: int = 50) -> None:
        self.sp = sp
        self.interval_ms = interval_ms
        self._device_time_ms = 0
        self._pv = 0.0
        self._integral = 0.0
        self._last_error = 0.0

    def set_sp(self, sp: float) -> None:
        self.sp = sp

    def next_sample(self) -> TelemetrySample:
        dt = self.interval_ms / 1000.0
        self._device_time_ms += self.interval_ms
        error = self.sp - self._pv
        self._integral += error * dt
        derivative = (error - self._last_error) / dt if dt else 0.0
        raw_out = 1.1 * error + 0.04 * self._integral + 0.02 * derivative
        out = max(0.0, min(100.0, raw_out))
        load_wave = math.sin(self._device_time_ms / 900.0) * 0.12
        self._pv += (out / 100.0 * self.sp - self._pv) * 0.08 + load_wave
        self._last_error = error
        return TelemetrySample(
            pc_time=datetime.now().isoformat(timespec="milliseconds"),
            device_time_ms=self._device_time_ms,
            ch=0,
            sp=float(self.sp),
            pv=round(self._pv, 4),
            out=round(out, 4),
        )
