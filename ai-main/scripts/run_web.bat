@echo off
setlocal
cd /d %~dp0\..

echo.
echo ============================================
echo   Local Voice AI - Web Interface
echo ============================================
echo.

if not exist ".venv\Scripts\python.exe" (
    echo [ERROR] Virtual environment not found.
    echo         Run: scripts\setup_windows.ps1
    pause
    exit /b 1
)

REM Check Ollama
curl -s http://localhost:11434 >nul 2>&1
if %errorlevel% neq 0 (
    echo [WARN] Ollama not running. Starting it...
    start /min ollama serve
    timeout /t 3 >nul
)

call .venv\Scripts\activate.bat

echo.
echo Starting web server...
echo Open http://127.0.0.1:8765 in your browser
echo.

python web_app.py

pause