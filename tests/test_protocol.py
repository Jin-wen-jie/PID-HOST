import math

import pytest

from pid_host.protocol import (
    AckMessage,
    CommandTracker,
    ProtocolError,
    TelemetryMessage,
    decode_line,
    encode_command,
    parse_incoming,
    validate_pid_values,
    validate_setpoint,
)


def test_encode_command_outputs_compact_json_line():
    line = encode_command("set_pid", seq=2, ch=0, kp=1.2, ki=0.05, kd=0.01)

    assert line == '{"type":"set_pid","seq":2,"ch":0,"kp":1.2,"ki":0.05,"kd":0.01}\n'


def test_decode_line_accepts_lf_and_crlf():
    assert decode_line('{"type":"ack","seq":2}\n') == {"type": "ack", "seq": 2}
    assert decode_line('{"type":"ack","seq":3}\r\n') == {"type": "ack", "seq": 3}


def test_decode_line_rejects_bad_json():
    with pytest.raises(ProtocolError) as exc:
        decode_line("{bad json}\n")

    assert exc.value.code == "bad_json"


def test_parse_incoming_validates_ack_and_telemetry():
    ack = parse_incoming('{"type":"ack","seq":7}\n')
    tel = parse_incoming('{"type":"tel","ch":0,"t":123,"sp":50.0,"pv":48.7,"out":32.1}\n')

    assert ack == AckMessage(seq=7)
    assert tel == TelemetryMessage(ch=0, t=123, sp=50.0, pv=48.7, out=32.1)


def test_parse_incoming_rejects_missing_telemetry_field():
    with pytest.raises(ProtocolError) as exc:
        parse_incoming('{"type":"tel","ch":0,"t":123,"sp":50.0,"pv":48.7}\n')

    assert exc.value.code == "missing_field"


def test_validate_pid_values_accepts_two_motor_channels_and_rejects_invalid_channel():
    validate_pid_values(ch=0, kp=1.0, ki=0.0, kd=0.0)
    validate_pid_values(ch=1, kp=1.0, ki=0.0, kd=0.0)

    with pytest.raises(ProtocolError) as exc:
        validate_pid_values(ch=2, kp=1.0, ki=0.0, kd=0.0)
    assert exc.value.code == "bad_value"

    with pytest.raises(ProtocolError):
        validate_pid_values(ch=0, kp=math.nan, ki=0.0, kd=0.0)


def test_validate_setpoint_accepts_two_motor_channels_and_rejects_invalid_channel():
    validate_setpoint(ch=0, sp=50.0)
    validate_setpoint(ch=1, sp=80.0)

    with pytest.raises(ProtocolError) as exc:
        validate_setpoint(ch=2, sp=50.0)
    assert exc.value.code == "bad_value"


def test_command_tracker_allows_one_pending_command_and_matches_ack():
    tracker = CommandTracker(timeout_ms=1000)

    assert tracker.start("set_sp", now_ms=10) == 1
    assert tracker.can_send is False
    with pytest.raises(ProtocolError) as exc:
        tracker.start("set_pid", now_ms=11)
    assert exc.value.code == "busy"

    assert tracker.handle_response(AckMessage(seq=1)) == "set_sp"
    assert tracker.can_send is True


def test_command_tracker_times_out_pending_command():
    tracker = CommandTracker(timeout_ms=1000)

    tracker.start("stream", now_ms=100)
    timed_out = tracker.check_timeout(now_ms=1101)

    assert timed_out == "stream"
    assert tracker.can_send is True
