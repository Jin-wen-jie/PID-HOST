from pathlib import Path


def test_windows_launchers_exist_and_run_pid_host_module():
    normal = Path("Start-PID-HOST.bat")
    demo = Path("Start-PID-HOST-Demo.bat")

    assert normal.exists()
    assert demo.exists()
    assert "python -m pid_host %*" in normal.read_text(encoding="utf-8")
    assert 'call "%~dp0Start-PID-HOST.bat" --demo' in demo.read_text(encoding="utf-8")
