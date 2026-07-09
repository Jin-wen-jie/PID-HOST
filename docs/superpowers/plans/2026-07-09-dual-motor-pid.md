# Dual Motor PID Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add two independent motor PID channels while keeping one compact tuning panel.

**Architecture:** Store PID values per channel in a small channel config model. The UI edits one selected channel at a time and sends `ch=0` or `ch=1` with each command. Telemetry remains one buffer, with plotting and latest labels filtered to the selected channel.

**Tech Stack:** Python, PySide6, PyQtGraph, pytest.

---

### Task 1: Protocol and Config

**Files:**
- Modify: `src/pid_host/protocol.py`
- Modify: `src/pid_host/config.py`
- Test: `tests/test_protocol.py`
- Test: `tests/test_config.py`

- [ ] Add failing tests that accept `ch=1`, reject `ch=2`, and round-trip two channel configs.
- [ ] Update validation to allow channels `0` and `1`.
- [ ] Add `PidChannelConfig` and let `AppConfig` store `selected_ch` plus two channel entries.
- [ ] Keep loading old flat configs by converting old `ch/kp/ki/kd/sp` fields into one channel entry.
- [ ] Run `python -m pytest tests/test_protocol.py tests/test_config.py -q`.

### Task 2: Data and Simulator

**Files:**
- Modify: `src/pid_host/data.py`
- Modify: `src/pid_host/simulator.py`
- Test: `tests/test_data.py`
- Test: `tests/test_simulator.py`

- [ ] Add failing tests for `TelemetryBuffer.series(ch=1)` and `latest(ch=1)`.
- [ ] Add failing tests for demo samples from both channels and per-channel setpoint updates.
- [ ] Filter buffer series and latest sample by optional channel.
- [ ] Generate one demo sample per motor tick with independent internal state.
- [ ] Run `python -m pytest tests/test_data.py tests/test_simulator.py -q`.

### Task 3: UI Channel Switching

**Files:**
- Modify: `src/pid_host/ui/main_window.py`
- Test: `tests/test_runtime.py`

- [ ] Add failing tests that switching from motor 1 to motor 2 preserves independent `Kp/Ki/Kd/SP`.
- [ ] Add failing tests that `send_pid` and `send_sp` use the selected channel.
- [ ] Add a channel selector with `电机1 (CH0)` and `电机2 (CH1)`.
- [ ] Store current spin values before switching channel and load the selected channel values after switching.
- [ ] Filter latest labels and plot data to the selected channel.
- [ ] Run `python -m pytest tests/test_runtime.py -q`.

### Task 4: Docs and Verification

**Files:**
- Modify: `docs/spec.md`
- Modify: `docs/protocol-for-mcu.md`

- [ ] Update docs to say first supported channels are `0` and `1`.
- [ ] Update protocol examples for motor 1 and motor 2.
- [ ] Run `python -m pytest`.
- [ ] Run `git diff --check`.
- [ ] Commit with `feat: add dual motor PID channels`.
