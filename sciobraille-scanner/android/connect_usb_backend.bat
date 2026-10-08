@echo off
setlocal
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0connect_usb_backend.ps1" -InstallApk
if errorlevel 1 (
  echo.
  echo USB connection setup failed. Read the message above.
)
echo.
pause
endlocal
