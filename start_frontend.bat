@echo off
echo ========================================
echo 启动股票分析系统 - 前端应用
echo ========================================
echo.

cd frontend

echo 检查依赖...
if not exist "node_modules\" (
    echo 正在安装Node依赖...
    npm install
)

echo.
echo 启动前端开发服务器...
echo 应用地址: http://localhost:3000
echo.
echo 按 Ctrl+C 停止服务器
echo.

npm start

pause
