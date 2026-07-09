@echo off
REM Switch backend to HTTP mode.

cd /d "%~dp0\.."

set ENABLE_HTTPS=false
set SECURITY_MODE=development

taskkill /f /im python.exe 2>nul

cd backend
start /b python -m uvicorn app.main:app --host 0.0.0.0 --port 8000

echo.
echo Switched to HTTP mode: http://0.0.0.0:8000
pause
