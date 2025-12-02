#!/bin/bash
# Git 提交脚本 v0.2.4

echo "=================================="
echo "准备提交 v0.2.4"
echo "=================================="

# 1. 查看修改状态
echo ""
echo "📋 查看修改文件..."
git status

echo ""
read -p "是否继续提交？(y/n): " confirm
if [ "$confirm" != "y" ]; then
    echo "❌ 取消提交"
    exit 0
fi

# 2. 添加文件
echo ""
echo "➕ 添加文件到暂存区..."
git add .

# 3. 提交
echo ""
echo "💾 提交更改..."
git commit -m "Release v0.2.4: 板块数据全量缓存、智能去重系统

主要更新：
✨ 新增功能
- 板块数据全量内存缓存，查询性能 <1ms
- 启动时自动导入股票和板块数据
- 智能去重系统（基于全局离群值检测）
- 完善的数据一致性检验
- 详细的去重日志和追溯机制

🔧 技术改进
- 扩展 MemoryCacheManager 支持板块数据
- 新增 deduplicate_helper.py 智能去重模块
- 改进 data_manager.py 启动检查逻辑
- 新增 6 个板块数据查询方法

📚 文档
- 新增：智能去重技术详解.md（详细技术方案）
- 新增：v0.2.4部署检查清单.md（完整部署指南）
- 更新：README.md、待实现功能想法.md
- 更新：CHANGELOG.md（完整更新日志）

🐛 Bug 修复
- 修复临时列干扰重复检查的"灯下黑"问题
- 修复列名适配问题（支持 总分/综合评分/score）
- 完善去重逻辑（从局部检测改为全局统计）

📊 数据统计
- 股票数据：5,435 只，27,145 条记录
- 板块数据：1,430 条记录
- 智能去重：自动处理 5 个重复，删除 5 条异常

⚠️ 注意事项
- 确保服务器已创建 daily_sector_data 表
- 确保 data/ 目录包含所有板块Excel文件
- 板块缓存增加约 50MB 内存占用
"

# 4. 打标签
echo ""
echo "🏷️  创建标签..."
git tag -a v0.2.4 -m "Release v0.2.4

板块数据全量缓存、智能去重系统

主要特性：
- 板块数据内存缓存（<1ms查询性能）
- 全局离群值智能去重算法
- 自动导入股票和板块数据
- 完善的数据一致性检验

技术亮点：
- 扩展内存缓存架构
- 创新的去重算法设计
- 详细的日志和追溯机制
- 保护原始数据完整性

部署准备：
- 数据库表已创建
- 数据文件已上传
- 完整的部署检查清单
"

# 5. 显示最近的提交
echo ""
echo "📝 最近的提交："
git log --oneline -5

# 6. 显示标签
echo ""
echo "🏷️  现有标签："
git tag -l

# 7. 推送提示
echo ""
echo "=================================="
echo "✅ 本地提交完成！"
echo "=================================="
echo ""
echo "下一步：推送到远程仓库"
echo ""
echo "命令："
echo "  git push origin main"
echo "  git push origin v0.2.4"
echo ""
echo "或者："
echo "  git push origin main --tags"
echo ""
read -p "是否立即推送？(y/n): " push_confirm
if [ "$push_confirm" = "y" ]; then
    echo ""
    echo "🚀 推送到远程仓库..."
    git push origin main
    git push origin v0.2.4
    echo ""
    echo "✅ 推送完成！"
else
    echo ""
    echo "⏸️  稍后手动推送"
fi

echo ""
echo "=================================="
echo "🎉 v0.2.4 提交完成！"
echo "=================================="
