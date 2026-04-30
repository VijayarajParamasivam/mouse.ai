@echo off
echo ============================================
echo    mouse.ai - AI Cursor Assistant Setup
echo ============================================
echo.

if not exist "venv" (
    echo Creating virtual environment...
    python -m venv venv
    echo.
)

echo Installing dependencies...
.\venv\Scripts\pip.exe install -r requirements.txt
echo.
if %ERRORLEVEL% NEQ 0 (
    echo [ERROR] Failed to install dependencies.
    echo Make sure Python and pip are in your PATH.
    pause
    exit /b 1
)
echo.
echo ============================================
echo    Setup complete!
echo ============================================
echo.
echo To start mouse.ai:
echo    .\venv\Scripts\pythonw.exe main.py
echo.
echo Or for debug output:
echo    .\venv\Scripts\python.exe main.py
echo.
echo Hotkey:           Alt+A (capture screen region)
echo Text Selection:   Select any text, click the sparkle icon
echo System Tray:      Right-click tray icon for options
echo.
pause
