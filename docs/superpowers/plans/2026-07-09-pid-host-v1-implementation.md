# PID-HOST V1 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the first runnable PID-HOST desktop app for single-channel PID tuning, monitoring, logging, CSV recording, UART JSON Lines communication, and demo data mode.

**Architecture:** Implement a small Python package with separated protocol, data, config, serial, simulator, and UI modules. Core behavior is covered by pytest before UI wiring; the GUI uses PySide6 and PyQtGraph with a curve-first layout.

**Tech Stack:** Python 3.11+, PySide6, PyQtGraph, pyserial, pytest.

---

## File Structure

- `pyproject.toml`: package metadata, dependencies, pytest config, console script.
- `requirements.txt`: simple install path for users who prefer pip requirements.
- `src/pid_host/__init__.py`: package marker and version.
- `src/pid_host/__main__.py`: `python -m pid_host` entry.
- `src/pid_host/main.py`: CLI entry and Qt application bootstrap.
- `src/pid_host/protocol.py`: JSON Lines commands, decoding, validation, command tracker.
- `src/pid_host/data.py`: telemetry sample model, rolling buffer, CSV recorder.
- `src/pid_host/config.py`: app configuration save/load.
- `src/pid_host/simulator.py`: deterministic PID-like demo data generator.
- `src/pid_host/serial_link.py`: pyserial-backed Qt worker for line IO.
- `src/pid_host/ui/main_window.py`: PySide6 main window and UI behavior.
- `tests/test_protocol.py`: protocol tests.
- `tests/test_data.py`: telemetry buffer and CSV tests.
- `tests/test_config.py`: config persistence tests.
- `tests/test_simulator.py`: demo generator tests.
- `docs/dev-setup.md`: setup and run instructions.

## Task 1: Project Skeleton and Red Tests

**Files:**
- Create: `pyproject.toml`
- Create: `requirements.txt`
- Create: `src/pid_host/__init__.py`
- Create: `tests/test_protocol.py`
- Create: `tests/test_data.py`
- Create: `tests/test_config.py`
- Create: `tests/test_simulator.py`

- [ ] Create package/test skeleton and tests for protocol commands, line decoding, telemetry validation, rolling buffers, CSV recording, config round trip, and demo sample generation.
- [ ] Run `python -m pytest` and verify tests fail because production modules do not exist yet.

## Task 2: Core Modules

**Files:**
- Create: `src/pid_host/protocol.py`
- Create: `src/pid_host/data.py`
- Create: `src/pid_host/config.py`
- Create: `src/pid_host/simulator.py`

- [ ] Implement only enough production code for the red tests.
- [ ] Run `python -m pytest` and verify all core tests pass.
- [ ] Refactor names and duplication while keeping tests green.

## Task 3: Desktop Runtime

**Files:**
- Create: `src/pid_host/__main__.py`
- Create: `src/pid_host/main.py`
- Create: `src/pid_host/serial_link.py`
- Create: `src/pid_host/ui/main_window.py`
- Create: `src/pid_host/ui/__init__.py`

- [ ] Add Qt app bootstrap with `--demo` and `--version`.
- [ ] Add serial worker using pyserial with line-based JSON transport.
- [ ] Add curve-first PySide6 main window with toolbar, PID panel, PyQtGraph plot, and log panel.
- [ ] Wire demo mode to feed SP/PV/OUT data at 20 Hz.
- [ ] Wire CSV recording, pause/clear, config save/load, and command/log handling.

## Task 4: Documentation and Verification

**Files:**
- Modify: `README.md`
- Create: `docs/dev-setup.md`

- [ ] Document installation, running demo mode, running tests, and connecting real UART hardware.
- [ ] Run `python -m pytest`.
- [ ] Run a smoke import for the Qt app with offscreen platform.
- [ ] Run `python -m pid_host --version`.
- [ ] Run `git diff --check`.
- [ ] Commit and push the first runnable version.

## Coverage Check

- UART JSON Lines protocol: Task 1, Task 2, Task 3.
- Single-channel PID commands and telemetry: Task 1, Task 2, Task 3.
- Real-time SP/PV/OUT curve: Task 3.
- CSV recording: Task 1, Task 2, Task 3.
- Parameter config save/load: Task 1, Task 2, Task 3.
- Log panel and error handling: Task 3.
- Demo mode: Task 1, Task 2, Task 3.
- User setup documentation: Task 4.
