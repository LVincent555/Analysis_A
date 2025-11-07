@echo off
chcp 65001 >nul
echo ============================================================
echo 🚀 推送代码到GitHub
echo ============================================================
echo.

cd /d "%~dp0"

echo 📝 添加所有修改...
git add .
echo.

echo 💾 提交修改...
git commit -m "feat: 添加前N个股票选择功能和行业趋势前N名功能

- 前端: 最新热点添加分析股票数选择(100/200/400/600/800/1000)
- 前端: 行业趋势添加前N名选择(1000/2000/3000/5000)
- 前端: 排名跳变和稳步上升添加搜索功能
- 后端: API添加top_n和limit参数支持
- 后端: 优化缓存和日志机制
- 已编译生产版本到frontend/build"
echo.

echo 📤 推送到GitHub...
git push origin main
echo.

echo ============================================================
echo ✅ 推送完成！
echo ============================================================
echo.
echo 接下来在服务器上执行：
echo   1. ssh root@60.205.251.109
echo   2. cd /path/to/stock_analysis_app
echo   3. git pull origin main
echo   4. bash restart.sh
echo.
pause
