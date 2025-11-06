@echo off
chcp 65001 >nul
echo ========================================
echo 数据库连接测试
echo ========================================
echo.

cd %~dp0
python scripts\test_db_connection.py

echo.
pause
