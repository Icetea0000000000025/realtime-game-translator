@echo off
chcp 65001 > nul
echo ========================================================
echo   Live Translation for Windows
echo ========================================================

REM Check if virtual environment exists
if exist .venv\Scripts\python.exe (
    set "PY_EXE=.\.venv\Scripts\python.exe"
) else if exist .venv_win\Scripts\python.exe (
    set "PY_EXE=.\.venv_win\Scripts\python.exe"
) else (
    echo [*] Creating virtual environment (.venv)...
    python -m venv .venv
    echo [*] Installing dependencies...
    .\.venv\Scripts\pip install -r requirements.txt
    set "PY_EXE=.\.venv\Scripts\python.exe"
)

echo [*] Starting Live Translation Overlay...
echo [*] Tip: Run with --help to see all options
echo.
%PY_EXE% live_translate_windows.py %*
pause
