from __future__ import annotations

import json
import math
from dataclasses import dataclass
from typing import Any


ERROR_CODES = {
    "bad_json",
    "bad_type",
    "missing_field",
    "bad_value",
    "unsupported",
    "busy",
}
SUPPORTED_CHANNELS = (0, 1)


class ProtocolError(ValueError):
    def __init__(self, code: str, message: str, seq: int | None = None) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.seq = seq


@dataclass(frozen=True)
class AckMessage:
    seq: int


@dataclass(frozen=True)
class ErrorMessage:
    seq: int | None
    code: str
    message: str


@dataclass(frozen=True)
class HelloMessage:
    seq: int
    device: str
    fw: str
    proto: int


@dataclass(frozen=True)
class TelemetryMessage:
    ch: int
    t: int
    sp: float
    pv: float
    out: float


IncomingMessage = AckMessage | ErrorMessage | HelloMessage | TelemetryMessage


def encode_command(message_type: str, **fields: Any) -> str:
    payload = {"type": message_type}
    payload.update(fields)
    return json.dumps(payload, ensure_ascii=False, separators=(",", ":")) + "\n"


def decode_line(line: str | bytes) -> dict[str, Any]:
    if isinstance(line, bytes):
        line = line.decode("utf-8")
    text = line.strip("\r\n")
    if not text:
        raise ProtocolError("bad_json", "empty line")
    try:
        decoded = json.loads(text)
    except json.JSONDecodeError as exc:
        raise ProtocolError("bad_json", str(exc)) from exc
    if not isinstance(decoded, dict):
        raise ProtocolError("bad_json", "message must be a JSON object")
    return decoded


def parse_incoming(line: str | bytes) -> IncomingMessage:
    payload = decode_line(line)
    message_type = _required_str(payload, "type")
    if message_type == "ack":
        return AckMessage(seq=_required_int(payload, "seq"))
    if message_type == "err":
        code = _required_str(payload, "code")
        if code not in ERROR_CODES:
            raise ProtocolError("bad_value", f"unknown error code: {code}")
        return ErrorMessage(
            seq=_optional_int(payload, "seq"),
            code=code,
            message=str(payload.get("message", "")),
        )
    if message_type == "hello":
        return HelloMessage(
            seq=_required_int(payload, "seq"),
            device=_required_str(payload, "device"),
            fw=_required_str(payload, "fw"),
            proto=_required_int(payload, "proto"),
        )
    if message_type == "tel":
        ch = _required_int(payload, "ch")
        _validate_channel(ch)
        return TelemetryMessage(
            ch=ch,
            t=_required_int(payload, "t"),
            sp=_required_float(payload, "sp"),
            pv=_required_float(payload, "pv"),
            out=_required_float(payload, "out"),
        )
    raise ProtocolError("bad_type", f"unsupported message type: {message_type}")


def validate_pid_values(ch: int, kp: float, ki: float, kd: float) -> None:
    _validate_channel(ch)
    for name, value in {"kp": kp, "ki": ki, "kd": kd}.items():
        if not _is_finite_number(value):
            raise ProtocolError("bad_value", f"{name} must be finite")


def validate_setpoint(ch: int, sp: float) -> None:
    _validate_channel(ch)
    if not _is_finite_number(sp):
        raise ProtocolError("bad_value", "sp must be finite")


def validate_stream_rate(rate_hz: int) -> None:
    if rate_hz < 10 or rate_hz > 20:
        raise ProtocolError("bad_value", "rate_hz must be between 10 and 20")


class CommandTracker:
    def __init__(self, timeout_ms: int = 1000) -> None:
        self.timeout_ms = timeout_ms
        self._next_seq = 1
        self._pending: tuple[int, str, int] | None = None

    @property
    def can_send(self) -> bool:
        return self._pending is None

    @property
    def pending_seq(self) -> int | None:
        return self._pending[0] if self._pending else None

    def start(self, command_name: str, now_ms: int) -> int:
        if self._pending is not None:
            raise ProtocolError("busy", "another command is waiting for ack")
        seq = self._next_seq
        self._next_seq += 1
        self._pending = (seq, command_name, now_ms)
        return seq

    def handle_response(self, message: AckMessage | ErrorMessage) -> str | None:
        if self._pending is None:
            return None
        seq, command_name, _ = self._pending
        if message.seq != seq:
            return None
        self._pending = None
        return command_name

    def check_timeout(self, now_ms: int) -> str | None:
        if self._pending is None:
            return None
        _, command_name, started_ms = self._pending
        if now_ms - started_ms <= self.timeout_ms:
            return None
        self._pending = None
        return command_name


def _required(payload: dict[str, Any], field: str) -> Any:
    if field not in payload:
        raise ProtocolError("missing_field", f"missing field: {field}")
    return payload[field]


def _required_str(payload: dict[str, Any], field: str) -> str:
    value = _required(payload, field)
    if not isinstance(value, str) or not value:
        raise ProtocolError("bad_value", f"{field} must be a non-empty string")
    return value


def _required_int(payload: dict[str, Any], field: str) -> int:
    value = _required(payload, field)
    if isinstance(value, bool) or not isinstance(value, int):
        raise ProtocolError("bad_value", f"{field} must be an integer")
    return value


def _optional_int(payload: dict[str, Any], field: str) -> int | None:
    if field not in payload:
        return None
    value = payload[field]
    if isinstance(value, bool) or not isinstance(value, int):
        raise ProtocolError("bad_value", f"{field} must be an integer")
    return value


def _required_float(payload: dict[str, Any], field: str) -> float:
    value = _required(payload, field)
    if not _is_finite_number(value):
        raise ProtocolError("bad_value", f"{field} must be finite")
    return float(value)


def _is_finite_number(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)


def _validate_channel(ch: int) -> None:
    if ch not in SUPPORTED_CHANNELS:
        raise ProtocolError("bad_value", "supported channels are ch=0 and ch=1")
