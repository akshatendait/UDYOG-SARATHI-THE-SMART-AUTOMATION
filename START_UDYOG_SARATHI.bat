@echo off
title Udyog Sarathi Server Launcher
echo ========================================================
echo        Starting Udyog Sarathi Enterprise System
echo ========================================================
echo.
cd /d "%~dp0backend"
echo [1/2] Launching FastAPI Backend on http://127.0.0.1:8000 ...
start "" python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
timeout /t 2 >nul
echo [2/2] Opening Web Application in Browser ...
start "" "http://127.0.0.1:8000/app"
echo.
echo ========================================================
echo Server is running! Keep this window open while using.
echo Press any key to exit launcher.
echo ========================================================
pause >nul
