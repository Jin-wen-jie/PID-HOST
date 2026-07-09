from pathlib import Path

from pid_host.data import CsvRecorder, TelemetryBuffer, TelemetrySample


def sample(device_time_ms: int, value: float, ch: int = 0) -> TelemetrySample:
    return TelemetrySample(
        pc_time="2026-07-09T10:00:00.000",
        device_time_ms=device_time_ms,
        ch=ch,
        sp=50.0 + ch * 10.0,
        pv=value,
        out=value / 2,
    )


def test_telemetry_buffer_keeps_recent_window():
    buffer = TelemetryBuffer(window_seconds=1.0)

    buffer.add(sample(0, 1.0))
    buffer.add(sample(500, 2.0))
    buffer.add(sample(1500, 3.0))

    assert [item.device_time_ms for item in buffer.samples()] == [500, 1500]


def test_telemetry_buffer_returns_plot_series():
    buffer = TelemetryBuffer(window_seconds=60)
    buffer.add(sample(1000, 42.0))

    x, sp, pv, out = buffer.series()

    assert x == [1.0]
    assert sp == [50.0]
    assert pv == [42.0]
    assert out == [21.0]


def test_telemetry_buffer_filters_latest_and_series_by_channel():
    buffer = TelemetryBuffer(window_seconds=60)
    buffer.add(sample(1000, 10.0, ch=0))
    buffer.add(sample(1100, 20.0, ch=1))
    buffer.add(sample(1200, 30.0, ch=0))

    assert buffer.latest(ch=0).pv == 30.0
    assert buffer.latest(ch=1).pv == 20.0

    x, sp, pv, out = buffer.series(ch=1)

    assert x == [1.1]
    assert sp == [60.0]
    assert pv == [20.0]
    assert out == [10.0]


def test_csv_recorder_writes_header_and_rows(tmp_path: Path):
    path = tmp_path / "pid_log.csv"
    recorder = CsvRecorder()

    recorder.start(path)
    recorder.write(sample(1000, 42.0))
    recorder.stop()

    assert path.read_text(encoding="utf-8").splitlines() == [
        "pc_time,device_time_ms,ch,sp,pv,out",
        "2026-07-09T10:00:00.000,1000,0,50.0,42.0,21.0",
    ]
