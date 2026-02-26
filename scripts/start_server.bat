@echo off
echo ==============================================
echo   GreenFlow AI – System Relaunch (Robust)
echo ==============================================
echo.

:: Kill lingering processes
echo 🧹 Cleaning up port 8000 and old Python tasks...
taskkill /F /IM python.exe /T 2>nul
taskkill /F /IM uvicorn.exe /T 2>nul

echo 🚀 Starting Simulated Data Generator...
start /b python greenflow\simulated_background_worker.py

echo 🌐 Starting FastAPI Server (http://localhost:8000)...
echo.
python -m uvicorn greenflow.main:app --host 0.0.0.0 --port 8000 --reload

pause
