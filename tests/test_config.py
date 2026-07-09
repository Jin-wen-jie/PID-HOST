from pathlib import Path

from pid_host.config import AppConfig, PidChannelConfig


def test_config_round_trip(tmp_path: Path):
    path = tmp_path / "config.json"
    config = AppConfig(
        port="COM3",
        baudrate=115200,
        selected_ch=1,
        channels=(
            PidChannelConfig(ch=0, kp=1.2, ki=0.05, kd=0.01, sp=50.0),
            PidChannelConfig(ch=1, kp=0.8, ki=0.03, kd=0.02, sp=80.0),
        ),
    )

    config.save(path)
    loaded = AppConfig.load(path)

    assert loaded == config


def test_missing_config_returns_defaults(tmp_path: Path):
    loaded = AppConfig.load(tmp_path / "missing.json")

    assert loaded.baudrate == 115200
    assert loaded.selected_ch == 0
    assert [channel.ch for channel in loaded.channels] == [0, 1]


def test_load_legacy_single_channel_config_maps_values_to_selected_channel(tmp_path: Path):
    path = tmp_path / "legacy.json"
    path.write_text(
        """
        {
          "port": "COM4",
          "baudrate": 57600,
          "ch": 1,
          "kp": 2.0,
          "ki": 0.2,
          "kd": 0.02,
          "sp": 120.0,
          "raw_frames_visible": true
        }
        """,
        encoding="utf-8",
    )

    loaded = AppConfig.load(path)

    assert loaded.port == "COM4"
    assert loaded.baudrate == 57600
    assert loaded.selected_ch == 1
    assert loaded.channels[1] == PidChannelConfig(ch=1, kp=2.0, ki=0.2, kd=0.02, sp=120.0)
    assert loaded.raw_frames_visible is True
