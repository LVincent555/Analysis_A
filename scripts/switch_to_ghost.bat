@echo off
REM ================================================================
REM 幽灵协议 - 一键切换脚本 (Windows)
REM ================================================================

echo 🔐 正在切换到幽灵协议...

REM 检查证书
if not exist "backend\certs\server.key" (
    echo ❌ 缺少证书，请先运行证书生成脚本
    echo    scripts\certs\generate_certs.bat
    pause
    exit /b 1
)

REM 设置环境变量
set ENABLE_HTTPS=true
set SECURITY_MODE=ghost

REM 停止现有服务
echo 停止现有服务...
taskkill /f /im python.exe 2>nul

REM 启动 HTTPS 服务
echo 启动 HTTPS 服务...
cd backend
start /b python run_ssl.py

echo.
echo ✅ 切换完成！
echo    HTTPS 服务: https://0.0.0.0:443
echo.
echo ⚠️ 注意: 客户端需要更新指纹配置后重新打包
pause
