from pid_host.simulator import DemoGenerator


def test_demo_generator_produces_two_channel_telemetry():
    generator = DemoGenerator(setpoints={0: 50.0, 1: 80.0})

    first_tick = generator.next_samples()
    second_tick = generator.next_samples()

    assert [sample.ch for sample in first_tick] == [0, 1]
    assert [sample.sp for sample in first_tick] == [50.0, 80.0]
    assert second_tick[0].device_time_ms > first_tick[0].device_time_ms
    assert second_tick[1].device_time_ms > first_tick[1].device_time_ms
    assert all(0.0 <= sample.out <= 100.0 for sample in first_tick)


def test_demo_generator_accepts_new_setpoint_per_channel():
    generator = DemoGenerator(setpoints={0: 50.0, 1: 80.0})

    generator.set_sp(ch=1, sp=120.0)
    samples = generator.next_samples()

    assert samples[0].sp == 50.0
    assert samples[1].sp == 120.0
