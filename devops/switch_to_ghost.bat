@echo off
REM Switch backend to HTTPS ghost mode.

cd /d "%~dp0\.."

if not exist "backend\certs\server.key" (
    echo Missing certificate. Run devops\certs\generate_certs.bat first.
    pause
    exit /b 1
)

set ENABLE_HTTPS=true
set SECURITY_MODE=ghost

taskkill /f /im python.exe 2>nul

cd backend
start /b python run_ssl.py

echo.
echo Switched to HTTPS mode: https://0.0.0.0:443
pause
