from pathlib import Path


def test_windows_launchers_exist_and_run_pid_host_module():
    normal = Path("Start-PID-HOST.bat")
    demo = Path("Start-PID-HOST-Demo.bat")
    hidden = Path("Start-PID-HOST-Hidden.vbs")
    hidden_demo = Path("Start-PID-HOST-Demo-Hidden.vbs")

    assert normal.exists()
    assert demo.exists()
    assert hidden.exists()
    assert hidden_demo.exists()
    assert "python -m pid_host %*" in normal.read_text(encoding="utf-8")
    assert 'call "%~dp0Start-PID-HOST.bat" --demo' in demo.read_text(encoding="utf-8")
    assert 'shell.Run command, 0, False' in hidden.read_text(encoding="utf-8")
    hidden_demo_text = hidden_demo.read_text(encoding="utf-8")
    assert "Start-PID-HOST-Hidden.vbs" in hidden_demo_text
    assert "--demo" in hidden_demo_text
