@echo off
setlocal
set "SCRIPT=%~dp0tools\platformio\maintenance-gui.ps1"
if not exist "%SCRIPT%" (
  echo PlatformIO maintenance tool was not found.
  pause
  exit /b 1
)
start "" powershell.exe -NoProfile -WindowStyle Hidden -ExecutionPolicy Bypass -File "%SCRIPT%"
exit /b 0
