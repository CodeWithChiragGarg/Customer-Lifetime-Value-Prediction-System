@echo off
title CLV Prediction System

echo ==========================================
echo   Customer Lifetime Value Prediction
echo ==========================================
echo.

:: Start Backend (using system Python, no venv)
echo [1/2] Starting FastAPI Backend on http://localhost:8000 ...
start "CLV Backend" cmd /k "cd /d "%~dp0backend" && python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload"

:: Wait 3 seconds for backend to boot
timeout /t 3 /nobreak > nul

:: Start Frontend
echo [2/2] Starting Next.js Frontend on http://localhost:3000 ...
start "CLV Frontend" cmd /k "cd /d "%~dp0frontend" && npm run dev"

echo.
echo Both servers are starting...
echo  Backend  --> http://localhost:8000
echo  Frontend --> http://localhost:3000
echo  API Docs --> http://localhost:8000/docs
echo.
pause
