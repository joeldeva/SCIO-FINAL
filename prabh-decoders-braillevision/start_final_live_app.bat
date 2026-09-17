@echo off
setlocal
cd /d "%~dp0"
echo Starting BrailleVision final live scanner...
echo.
python final_live_app.py
endlocal
