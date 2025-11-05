@echo off
echo ========================================
echo 启动股票分析系统 - 后端服务
echo ========================================
echo.

cd backend

echo 检查依赖...
pip show fastapi >nul 2>&1
if errorlevel 1 (
    echo 正在安装Python依赖...
    pip install -r requirements.txt
)

echo.
echo 启动后端服务器...
echo API地址: http://localhost:8000
echo API文档: http://localhost:8000/docs
echo.
echo 按 Ctrl+C 停止服务器
echo.

python main.py

pause
