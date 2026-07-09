from pid_host.simulator import DemoGenerator


def test_demo_generator_produces_single_channel_telemetry():
    generator = DemoGenerator(sp=50.0)

    first = generator.next_sample()
    second = generator.next_sample()

    assert first.ch == 0
    assert second.device_time_ms > first.device_time_ms
    assert first.sp == 50.0
    assert 0.0 <= first.out <= 100.0


def test_demo_generator_accepts_new_setpoint():
    generator = DemoGenerator(sp=50.0)

    generator.set_sp(80.0)
    sample = generator.next_sample()

    assert sample.sp == 80.0
