#!/bin/bash
# 修复前端proxy配置，让前端能连接到后端

PROJECT_DIR="$(cd "$(dirname "$0")" && pwd)"
PACKAGE_JSON="$PROJECT_DIR/frontend/package.json"

echo "🔧 修复前端配置"
echo "================================"

# 备份
if [ ! -f "$PACKAGE_JSON.bak" ]; then
    cp "$PACKAGE_JSON" "$PACKAGE_JSON.bak"
    echo "✓ 已备份 package.json"
fi

# 检查是否已有proxy
if grep -q '"proxy"' "$PACKAGE_JSON"; then
    echo "⚠️  package.json 已有 proxy 配置"
    echo ""
    echo "当前配置:"
    grep -A 1 '"proxy"' "$PACKAGE_JSON"
    echo ""
    read -p "是否要更新为 http://localhost:8000? (y/n): " answer
    if [ "$answer" != "y" ]; then
        echo "取消操作"
        exit 0
    fi
    
    # 删除旧的proxy行
    sed -i '/"proxy"/d' "$PACKAGE_JSON"
fi

# 添加proxy（在最后一个}之前）
sed -i '$ s/}/,\n  "proxy": "http:\/\/localhost:8000"\n}/' "$PACKAGE_JSON"

echo ""
echo "✓ 已添加 proxy 配置"
echo ""
echo "新配置:"
tail -5 "$PACKAGE_JSON"
echo ""
echo "================================"
echo "✅ 配置完成！"
echo ""
echo "📝 下一步:"
echo "  1. 停止前端: pkill -f 'npm start'"
echo "  2. 重启前端: ./start_frontend.sh"
echo "  或使用: ./start_all.sh dev"
echo ""
