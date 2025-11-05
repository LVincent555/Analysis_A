@echo off
echo ========================================
echo 重启后端服务
echo ========================================

echo 正在停止旧服务...
taskkill /F /IM python.exe /FI "WINDOWTITLE eq *main.py*" 2>nul
timeout /t 2 /nobreak >nul

cd backend

echo.
echo 启动新版本后端...
start "Stock Analysis Backend" python main.py

echo.
echo 后端服务已启动！
echo API地址: http://localhost:8000
echo API文档: http://localhost:8000/docs
pause
