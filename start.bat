@echo off
setlocal
title KLYPTRA Studio Launcher

echo ===================================================
echo           KLYPTRA - AI Video Clipping Studio
echo ===================================================
echo [1/3] Locating local Python environment...

set "PYTHON_EXE=C:\Users\Somesh\AppData\Local\Python\pythoncore-3.14-64\python.exe"
if not exist "%PYTHON_EXE%" (
    set "PYTHON_EXE=python"
)

echo [2/3] Starting KLYPTRA local backend on http://127.0.0.1:8000...
start "KLYPTRA Backend Service" /min "%PYTHON_EXE%" -m uvicorn backend.main:app --host 127.0.0.1 --port 8000

echo [3/3] Waiting for backend service health check...
:wait_loop
curl -s http://127.0.0.1:8000/api/health >nul 2>&1
if errorlevel 1 (
    timeout /t 1 /nobreak >nul
    goto wait_loop
)

echo.
echo ===================================================
echo KLYPTRA is ready! Opening Studio in your browser...
echo Localhost Link: http://localhost:8000/
echo Press Ctrl+C in this window to stop KLYPTRA.
echo ===================================================

start http://localhost:8000/

:: Keep launcher open
pause

