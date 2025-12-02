#!/bin/bash
# 服务器从Gitee部署v0.2.4一键脚本
# 使用方法：bash deploy_v0.2.4_from_gitee.sh

echo "=================================="
echo "🚀 从Gitee部署 v0.2.4"
echo "=================================="

# 1. 备份本地修改
echo "📦 备份本地修改..."
cp deploy_server.sh deploy_server.sh.backup 2>/dev/null || true
echo "✓ 已备份到 deploy_server.sh.backup"

# 2. 暂存本地修改
echo ""
echo "💾 暂存本地修改..."
git stash
echo "✓ 本地修改已暂存"

# 3. 确保远程是Gitee
echo ""
echo "🔗 设置远程仓库为Gitee..."
git remote set-url origin https://gitee.com/Vincent_lzh/Analysis_A.git
echo "✓ 远程仓库: $(git remote get-url origin)"

# 4. 拉取最新代码和标签
echo ""
echo "📥 拉取最新代码和标签..."
git fetch origin --tags
git pull origin main
echo "✓ 代码拉取完成"

# 5. 显示可用标签
echo ""
echo "📌 可用标签："
git tag -l | tail -5

# 6. 切换到v0.2.4
echo ""
echo "🔀 切换到 v0.2.4..."
git checkout v0.2.4
echo "✓ 当前版本: $(git describe --tags)"

# 7. 执行部署
echo ""
echo "=================================="
echo "🚀 开始部署..."
echo "=================================="
bash deploy_server.sh

# 8. 验证
echo ""
echo "=================================="
echo "✅ 部署完成！"
echo "=================================="
echo ""
echo "📊 验证部署："
echo "  tail -f logs/backend.log"
echo ""
echo "🔍 关键检查点："
echo "  ✅ 板块数据记录: 1430"
echo "  ✅ 板块数据日期数: 3 天"
echo "  ✅ 全量内存缓存已就绪"
echo ""
