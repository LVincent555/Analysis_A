@echo off
REM ================================================================
REM 回滚到 HTTP 模式 (Windows)
REM ================================================================

echo ⚠️ 正在切换回 HTTP 模式...

REM 设置环境变量
set ENABLE_HTTPS=false
set SECURITY_MODE=development

REM 停止现有服务
taskkill /f /im python.exe 2>nul

REM 启动 HTTP 服务
cd backend
start /b python -m uvicorn app.main:app --host 0.0.0.0 --port 8000

echo.
echo ⚠️ 已切换回 HTTP 模式
echo    HTTP 服务: http://0.0.0.0:8000
pause
