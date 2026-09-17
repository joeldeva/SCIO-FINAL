@echo off
setlocal EnableDelayedExpansion
title BrailleVision - Starting...
color 0A

echo.
echo  ============================================================
echo   BBBBB  rrr    aaaa  iii lll lll eee   VV        VV
echo   B    B r  r  a   a  i   l    l  e   e  VV      VV
echo   BBBBB  rrrr  aaaaa  i   l    l  eeeee   VV    VV
echo   B    B r  r  a   a  i   l    l  e        VV  VV
echo   BBBBB  r  r  a   a  iii lll lll eeeee     VVVV
echo  ============================================================
echo   Real-Time Braille Detection - BrailleVision Hackathon 2026
echo  ============================================================
echo.

:: ---- Use pre-built virtual environment ----
echo  [1/3] Checking for virtual environment...
set PYTHON="%~dp0venv_win311\Scripts\python.exe"
set PIP="%~dp0venv_win311\Scripts\pip.exe"

if not exist %PYTHON% (
    echo  [ERROR] The virtual environment 'venv_win311' is missing!
    pause
    exit /b 1
)
echo  [OK] Virtual environment found.
%PIP% install -r backend\requirements.txt
if %errorlevel% neq 0 (
    echo  [ERROR] Failed to install requirements.
    pause
    exit /b 1
)

:: ---- Generate samples if missing ----
if not exist "%~dp0dataset\sample_inputs\hello_clean.jpg" (
    echo  Generating sample dataset...
    cd /d "%~dp0"
    %PYTHON% backend\generate_samples.py
)

:: ---- Start backend server ----
echo.
echo  [4/4] Starting Backend API...
echo        URL:  http://localhost:8000
echo        Docs: http://localhost:8000/docs
echo.

set PYTHONIOENCODING=utf-8
start "BrailleVision Backend" cmd /k "title BrailleVision Backend && cd /d "%~dp0backend" && %PYTHON% -m uvicorn app:app --host 0.0.0.0 --port 8000 --reload"

:: Wait for backend
echo  Waiting for backend to start (5s)...
timeout /t 5 /nobreak >nul

:: ---- Open frontend ----
echo  [2/2] Opening frontend in browser...
start "" "%~dp0frontend\index.html"

:: Open API docs
timeout /t 2 /nobreak >nul
start "" "http://localhost:8000/docs"

echo.
echo  ============================================================
echo   BrailleVision is LIVE!
echo.
echo   Frontend : %~dp0frontend\index.html
echo   API      : http://localhost:8000
echo   API Docs : http://localhost:8000/docs
echo   Health   : http://localhost:8000/health
echo.
echo   To test CLI: %PYTHON% backend\inference_cli.py --image
echo      dataset\sample_inputs\hello_clean.jpg
echo  ============================================================
echo.
echo  Press any key to exit this window (backend will keep running)
pause >nul
