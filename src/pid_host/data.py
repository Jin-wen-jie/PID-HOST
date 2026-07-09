from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path
from typing import TextIO


@dataclass(frozen=True)
class TelemetrySample:
    pc_time: str
    device_time_ms: int
    ch: int
    sp: float
    pv: float
    out: float


class TelemetryBuffer:
    def __init__(self, window_seconds: float = 60.0) -> None:
        self.window_seconds = window_seconds
        self._samples: list[TelemetrySample] = []

    def add(self, sample: TelemetrySample) -> None:
        self._samples.append(sample)
        cutoff_ms = sample.device_time_ms - int(self.window_seconds * 1000)
        self._samples = [item for item in self._samples if item.device_time_ms >= cutoff_ms]

    def clear(self) -> None:
        self._samples.clear()

    def samples(self, ch: int | None = None) -> list[TelemetrySample]:
        if ch is None:
            return list(self._samples)
        return [sample for sample in self._samples if sample.ch == ch]

    def latest(self, ch: int | None = None) -> TelemetrySample | None:
        if ch is None:
            return self._samples[-1] if self._samples else None
        for sample in reversed(self._samples):
            if sample.ch == ch:
                return sample
        return None

    def series(self, ch: int | None = None) -> tuple[list[float], list[float], list[float], list[float]]:
        samples = self.samples(ch=ch)
        return (
            [item.device_time_ms / 1000.0 for item in samples],
            [item.sp for item in samples],
            [item.pv for item in samples],
            [item.out for item in samples],
        )


class CsvRecorder:
    def __init__(self) -> None:
        self._file: TextIO | None = None
        self._writer: csv.writer | None = None
        self.path: Path | None = None

    @property
    def is_recording(self) -> bool:
        return self._file is not None

    def start(self, path: str | Path) -> None:
        self.stop()
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._file = self.path.open("w", encoding="utf-8", newline="")
        self._writer = csv.writer(self._file)
        self._writer.writerow(["pc_time", "device_time_ms", "ch", "sp", "pv", "out"])
        self._file.flush()

    def write(self, sample: TelemetrySample) -> None:
        if self._writer is None or self._file is None:
            return
        self._writer.writerow(
            [sample.pc_time, sample.device_time_ms, sample.ch, sample.sp, sample.pv, sample.out]
        )
        self._file.flush()

    def stop(self) -> None:
        if self._file is not None:
            self._file.close()
        self._file = None
        self._writer = None

    def __enter__(self) -> CsvRecorder:
        return self

    def __exit__(self, *_exc: object) -> None:
        self.stop()
