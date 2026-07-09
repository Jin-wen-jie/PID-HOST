@echo off
setlocal
cd /d "%~dp0"
set "PYTHONPATH=%CD%\src;%PYTHONPATH%"

python -m pid_host %*
if errorlevel 1 (
  echo.
  echo PID-HOST failed to start.
  echo Try running: python -m pip install -r requirements.txt
  echo Then double-click this file again.
  echo.
  pause
)
