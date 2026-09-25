@echo off
chcp 65001 > nul
echo ========================================================
echo   Realtime Game Translator - Automated App Builder
echo ========================================================
echo.

if exist .venv\Scripts\python.exe (
    set "PY_EXE=.\.venv\Scripts\python.exe"
) else if exist .venv_win\Scripts\python.exe (
    set "PY_EXE=.\.venv_win\Scripts\python.exe"
) else (
    set "PY_EXE=python"
)

%PY_EXE% build_app.py
if errorlevel 1 (
    echo.
    echo [ERROR] Build failed! Check the error messages above.
    pause
    exit /b 1
)

echo.
echo ========================================================
echo   Build Successful! Check the 'dist' directory.
echo ========================================================
pause
