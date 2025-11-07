@echo off
REM ############################################################################
REM 每日数据更新脚本 (Windows)
REM 
REM 使用方法：
REM   1. 将新的Excel数据文件放入 data\ 目录
REM   2. 双击运行此脚本，或在命令行执行：update_daily_data.bat
REM ############################################################################

chcp 65001 >nul
setlocal enabledelayedexpansion

echo ═══════════════════════════════════════════════════════════════
echo 🚀 每日数据更新任务
echo ═══════════════════════════════════════════════════════════════
echo.
echo 📅 执行时间: %date% %time%
echo 📂 工作目录: %cd%
echo.

REM 检查Python是否存在
python --version >nul 2>&1
if errorlevel 1 (
    echo ❌ 错误: 未找到 Python
    echo 请先安装 Python 并添加到系统PATH
    pause
    exit /b 1
)

REM 检查数据目录
if not exist "data" (
    echo ❌ 错误: data 目录不存在
    pause
    exit /b 1
)

REM 检查数据文件
set STOCK_COUNT=0
set SECTOR_COUNT=0

for %%f in (data\*_data_sma_feature_color.xlsx) do set /a STOCK_COUNT+=1
for %%f in (data\*_allbk_sma_feature_color.xlsx) do set /a SECTOR_COUNT+=1

echo 📊 找到股票数据文件: %STOCK_COUNT% 个
echo 📊 找到板块数据文件: %SECTOR_COUNT% 个
echo.

if %STOCK_COUNT%==0 if %SECTOR_COUNT%==0 (
    echo ⚠️ 没有找到待导入的数据文件
    echo 提示：请将数据文件放入 data\ 目录
    echo   - 股票数据：YYYYMMDD_data_sma_feature_color.xlsx
    echo   - 板块数据：YYYYMMDD_allbk_sma_feature_color.xlsx
    pause
    exit /b 0
)

REM 运行Python更新脚本
echo ───────────────────────────────────────────────────────────────
echo 执行 Python 更新脚本...
echo.

python update_daily_data.py
set EXIT_CODE=%errorlevel%

echo.
echo ═══════════════════════════════════════════════════════════════

if %EXIT_CODE%==0 (
    echo ✅ 数据更新完成！
) else (
    echo ❌ 数据更新失败 ^(退出码: %EXIT_CODE%^)
    echo 请查看日志文件获取详细信息
)

echo ═══════════════════════════════════════════════════════════════
echo.
pause
exit /b %EXIT_CODE%
