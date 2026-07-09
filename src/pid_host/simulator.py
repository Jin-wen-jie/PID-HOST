from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import datetime

from .data import TelemetrySample


@dataclass
class _MotorState:
    sp: float
    pv: float = 0.0
    integral: float = 0.0
    last_error: float = 0.0


class DemoGenerator:
    def __init__(
        self,
        sp: float = 50.0,
        interval_ms: int = 50,
        setpoints: dict[int, float] | None = None,
    ) -> None:
        self.interval_ms = interval_ms
        self._device_time_ms = 0
        if setpoints is None:
            setpoints = {0: sp, 1: sp}
        self._states = {ch: _MotorState(sp=float(setpoints.get(ch, sp))) for ch in (0, 1)}

    def set_sp(self, sp: float, ch: int = 0) -> None:
        if ch in self._states:
            self._states[ch].sp = sp

    def next_samples(self) -> list[TelemetrySample]:
        self._device_time_ms += self.interval_ms
        return [self._sample_for_channel(ch) for ch in sorted(self._states)]

    def next_sample(self, ch: int = 0) -> TelemetrySample:
        self._device_time_ms += self.interval_ms
        return self._sample_for_channel(ch)

    def _sample_for_channel(self, ch: int) -> TelemetrySample:
        state = self._states[ch]
        dt = self.interval_ms / 1000.0
        error = state.sp - state.pv
        state.integral += error * dt
        derivative = (error - state.last_error) / dt if dt else 0.0
        raw_out = 1.1 * error + 0.04 * state.integral + 0.02 * derivative
        out = max(0.0, min(100.0, raw_out))
        load_wave = math.sin(self._device_time_ms / (900.0 + ch * 120.0)) * 0.12
        state.pv += (out / 100.0 * state.sp - state.pv) * 0.08 + load_wave
        state.last_error = error
        return TelemetrySample(
            pc_time=datetime.now().isoformat(timespec="milliseconds"),
            device_time_ms=self._device_time_ms,
            ch=ch,
            sp=float(state.sp),
            pv=round(state.pv, 4),
            out=round(out, 4),
        )
