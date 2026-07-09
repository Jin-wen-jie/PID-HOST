from pathlib import Path

from pid_host.config import AppConfig


def test_config_round_trip(tmp_path: Path):
    path = tmp_path / "config.json"
    config = AppConfig(port="COM3", baudrate=115200, kp=1.2, ki=0.05, kd=0.01, sp=50.0)

    config.save(path)
    loaded = AppConfig.load(path)

    assert loaded == config


def test_missing_config_returns_defaults(tmp_path: Path):
    loaded = AppConfig.load(tmp_path / "missing.json")

    assert loaded.baudrate == 115200
    assert loaded.ch == 0
