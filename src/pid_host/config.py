from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class PidChannelConfig:
    ch: int = 0
    kp: float = 1.0
    ki: float = 0.0
    kd: float = 0.0
    sp: float = 50.0


DEFAULT_CHANNELS = (
    PidChannelConfig(ch=0),
    PidChannelConfig(ch=1),
)


@dataclass(frozen=True)
class AppConfig:
    port: str = ""
    baudrate: int = 115200
    selected_ch: int = 0
    channels: tuple[PidChannelConfig, ...] = DEFAULT_CHANNELS
    window_seconds: float = 60.0
    raw_frames_visible: bool = False

    @property
    def ch(self) -> int:
        return self.selected_ch

    @property
    def kp(self) -> float:
        return self.channel(self.selected_ch).kp

    @property
    def ki(self) -> float:
        return self.channel(self.selected_ch).ki

    @property
    def kd(self) -> float:
        return self.channel(self.selected_ch).kd

    @property
    def sp(self) -> float:
        return self.channel(self.selected_ch).sp

    def channel(self, ch: int) -> PidChannelConfig:
        for channel in self.channels:
            if channel.ch == ch:
                return channel
        return PidChannelConfig(ch=ch)

    def save(self, path: str | Path) -> None:
        target = Path(path)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(
            json.dumps(asdict(self), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    @classmethod
    def load(cls, path: str | Path) -> AppConfig:
        source = Path(path)
        if not source.exists():
            return cls()
        data = json.loads(source.read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            return cls()
        selected_ch = _channel_or_default(data.get("selected_ch", data.get("ch", 0)))
        allowed: dict[str, Any] = {
            field: data[field]
            for field in ("port", "baudrate", "window_seconds", "raw_frames_visible")
            if field in data
        }
        allowed["selected_ch"] = selected_ch
        allowed["channels"] = _load_channels(data, selected_ch)
        return cls(**allowed)


def _load_channels(data: dict[str, Any], selected_ch: int) -> tuple[PidChannelConfig, ...]:
    channels = {channel.ch: channel for channel in DEFAULT_CHANNELS}
    raw_channels = data.get("channels")
    if isinstance(raw_channels, list):
        for raw_channel in raw_channels:
            if not isinstance(raw_channel, dict):
                continue
            channel = _parse_channel_config(raw_channel)
            if channel.ch in channels:
                channels[channel.ch] = channel
    else:
        channels[selected_ch] = PidChannelConfig(
            ch=selected_ch,
            kp=_float_or_default(data.get("kp"), channels[selected_ch].kp),
            ki=_float_or_default(data.get("ki"), channels[selected_ch].ki),
            kd=_float_or_default(data.get("kd"), channels[selected_ch].kd),
            sp=_float_or_default(data.get("sp"), channels[selected_ch].sp),
        )
    return tuple(channels[ch] for ch in sorted(channels))


def _parse_channel_config(data: dict[str, Any]) -> PidChannelConfig:
    ch = _channel_or_default(data.get("ch"))
    default = PidChannelConfig(ch=ch)
    return PidChannelConfig(
        ch=ch,
        kp=_float_or_default(data.get("kp"), default.kp),
        ki=_float_or_default(data.get("ki"), default.ki),
        kd=_float_or_default(data.get("kd"), default.kd),
        sp=_float_or_default(data.get("sp"), default.sp),
    )


def _channel_or_default(value: Any, default: int = 0) -> int:
    if isinstance(value, int) and not isinstance(value, bool) and value in (0, 1):
        return value
    return default


def _float_or_default(value: Any, default: float) -> float:
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return float(value)
    return default
