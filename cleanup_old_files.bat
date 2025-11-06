@echo off
echo ========================================
echo 清理旧版本文件脚本 v0.2.0
echo ========================================
echo.
echo 本脚本将删除以下旧版本文件：
echo   - backend/main.py (旧的单文件后端)
echo   - frontend/src/App.v1.js (旧版本备份)
echo.
echo 注意：这些文件将被永久删除！
echo.
set /p confirm="确认删除? (Y/N): "

if /i "%confirm%" NEQ "Y" (
    echo 操作已取消
    pause
    exit /b 0
)

echo.
echo 开始清理...

REM 删除旧的后端单文件
if exist "backend\main.py" (
    echo [删除] backend\main.py
    del "backend\main.py"
) else (
    echo [跳过] backend\main.py 不存在
)

REM 删除前端备份文件
if exist "frontend\src\App.v1.js" (
    echo [删除] frontend\src\App.v1.js
    del "frontend\src\App.v1.js"
) else (
    echo [跳过] frontend\src\App.v1.js 不存在
)

echo.
echo ========================================
echo 清理完成！
echo ========================================
echo.
echo 保留的文件：
echo   - backend/app/ (新的模块化后端)
echo   - frontend/src/App.js (当前使用版本)
echo   - frontend/src/App.v2.js (新的模块化版本)
echo.
pause
