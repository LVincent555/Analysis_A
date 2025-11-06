@echo off
chcp 65001 >nul
echo ========================================
echo 股票数据导入工具
echo ========================================
echo.

cd %~dp0
python scripts\import_data.py

echo.
echo 按任意键退出...
pause >nul
