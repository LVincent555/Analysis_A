@echo off
chcp 65001 >nul
REM Git 提交脚本 v0.2.4 (Windows)

echo ==================================
echo 准备提交 v0.2.4
echo ==================================

REM 1. 查看修改状态
echo.
echo 📋 查看修改文件...
git status

echo.
set /p confirm="是否继续提交？(y/n): "
if /i not "%confirm%"=="y" (
    echo ❌ 取消提交
    exit /b 0
)

REM 2. 添加文件
echo.
echo ➕ 添加文件到暂存区...
git add .

REM 3. 提交
echo.
echo 💾 提交更改...
git commit -m "Release v0.2.4: 板块数据全量缓存、智能去重系统" -m "" -m "主要更新：" -m "✨ 新增功能" -m "- 板块数据全量内存缓存，查询性能 <1ms" -m "- 启动时自动导入股票和板块数据" -m "- 智能去重系统（基于全局离群值检测）" -m "- 完善的数据一致性检验" -m "- 详细的去重日志和追溯机制" -m "" -m "🔧 技术改进" -m "- 扩展 MemoryCacheManager 支持板块数据" -m "- 新增 deduplicate_helper.py 智能去重模块" -m "- 改进 data_manager.py 启动检查逻辑" -m "- 新增 6 个板块数据查询方法" -m "" -m "📚 文档" -m "- 新增：智能去重技术详解.md（详细技术方案）" -m "- 新增：v0.2.4部署检查清单.md（完整部署指南）" -m "- 更新：README.md、待实现功能想法.md" -m "- 更新：CHANGELOG.md（完整更新日志）" -m "" -m "🐛 Bug 修复" -m "- 修复临时列干扰重复检查的灯下黑问题" -m "- 修复列名适配问题（支持 总分/综合评分/score）" -m "- 完善去重逻辑（从局部检测改为全局统计）" -m "" -m "📊 数据统计" -m "- 股票数据：5,435 只，27,145 条记录" -m "- 板块数据：1,430 条记录" -m "- 智能去重：自动处理 5 个重复，删除 5 条异常" -m "" -m "⚠️ 注意事项" -m "- 确保服务器已创建 daily_sector_data 表" -m "- 确保 data/ 目录包含所有板块Excel文件" -m "- 板块缓存增加约 50MB 内存占用"

REM 4. 打标签
echo.
echo 🏷️  创建标签...
git tag -a v0.2.4 -m "Release v0.2.4" -m "" -m "板块数据全量缓存、智能去重系统" -m "" -m "主要特性：" -m "- 板块数据内存缓存（<1ms查询性能）" -m "- 全局离群值智能去重算法" -m "- 自动导入股票和板块数据" -m "- 完善的数据一致性检验" -m "" -m "技术亮点：" -m "- 扩展内存缓存架构" -m "- 创新的去重算法设计" -m "- 详细的日志和追溯机制" -m "- 保护原始数据完整性" -m "" -m "部署准备：" -m "- 数据库表已创建" -m "- 数据文件已上传" -m "- 完整的部署检查清单"

REM 5. 显示最近的提交
echo.
echo 📝 最近的提交：
git log --oneline -5

REM 6. 显示标签
echo.
echo 🏷️  现有标签：
git tag -l

REM 7. 推送提示
echo.
echo ==================================
echo ✅ 本地提交完成！
echo ==================================
echo.
echo 下一步：推送到远程仓库
echo.
echo 命令：
echo   git push origin main
echo   git push origin v0.2.4
echo.
echo 或者：
echo   git push origin main --tags
echo.
set /p push_confirm="是否立即推送？(y/n): "
if /i "%push_confirm%"=="y" (
    echo.
    echo 🚀 推送到远程仓库...
    git push origin main
    git push origin v0.2.4
    echo.
    echo ✅ 推送完成！
) else (
    echo.
    echo ⏸️  稍后手动推送
)

echo.
echo ==================================
echo 🎉 v0.2.4 提交完成！
echo ==================================
pause
