@echo off
chcp 65001 >nul
echo ========================================
echo 健壮数据导入工具（带状态管理）
echo ========================================
echo.
echo 特性：
echo   ✓ 幂等性 - 已导入的日期自动跳过
echo   ✓ 原子性 - 失败自动回滚
echo   ✓ 状态管理 - JSON文件记录导入状态
echo   ✓ 文件校验 - MD5检测文件变化
echo.

cd %~dp0
python scripts\import_data_robust.py

echo.
echo 按任意键退出...
pause >nul
