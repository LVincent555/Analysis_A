#!/bin/bash
# Nginx超时配置优化脚本
# 解决504 Gateway Timeout问题

echo "================================================"
echo "🔧 Nginx超时配置优化"
echo "================================================"

# 检查是否为root用户
if [ "$EUID" -ne 0 ]; then 
    echo "❌ 请使用root权限运行此脚本"
    echo "   sudo bash 配置nginx超时.sh"
    exit 1
fi

# 查找Nginx配置文件
NGINX_CONF="/etc/nginx/sites-enabled/stock_analysis"

if [ ! -f "$NGINX_CONF" ]; then
    echo "❌ 未找到Nginx配置文件: $NGINX_CONF"
    echo "   请确认配置文件路径"
    exit 1
fi

echo "📄 找到配置文件: $NGINX_CONF"
echo ""

# 备份原配置
BACKUP_FILE="${NGINX_CONF}.backup.$(date +%Y%m%d_%H%M%S)"
echo "💾 备份原配置到: $BACKUP_FILE"
cp "$NGINX_CONF" "$BACKUP_FILE"

# 检查是否已经配置过
if grep -q "proxy_read_timeout" "$NGINX_CONF"; then
    echo "⚠️  检测到已存在超时配置，将更新配置..."
    
    # 更新现有配置
    sed -i 's/proxy_connect_timeout.*/proxy_connect_timeout 300s;/' "$NGINX_CONF"
    sed -i 's/proxy_send_timeout.*/proxy_send_timeout 300s;/' "$NGINX_CONF"
    sed -i 's/proxy_read_timeout.*/proxy_read_timeout 300s;/' "$NGINX_CONF"
else
    echo "➕ 添加新的超时配置..."
    
    # 在location块中添加超时配置
    # 查找 location / { 后面插入配置
    sed -i '/location \/ {/a\        # 超时配置\n        proxy_connect_timeout 300s;\n        proxy_send_timeout 300s;\n        proxy_read_timeout 300s;' "$NGINX_CONF"
fi

echo ""
echo "✅ 配置已更新"
echo ""
echo "📋 新的超时配置:"
echo "   proxy_connect_timeout 300s  (连接超时: 5分钟)"
echo "   proxy_send_timeout 300s     (发送超时: 5分钟)"
echo "   proxy_read_timeout 300s     (读取超时: 5分钟)"
echo ""

# 测试Nginx配置
echo "🧪 测试Nginx配置..."
if nginx -t; then
    echo "✅ Nginx配置测试通过"
    echo ""
    
    # 重载Nginx
    echo "🔄 重载Nginx..."
    if systemctl reload nginx; then
        echo "✅ Nginx重载成功"
        echo ""
        echo "================================================"
        echo "🎉 配置完成！"
        echo "================================================"
        echo ""
        echo "📊 查看当前配置:"
        echo "   cat $NGINX_CONF"
        echo ""
        echo "🔙 恢复备份:"
        echo "   sudo cp $BACKUP_FILE $NGINX_CONF"
        echo "   sudo systemctl reload nginx"
    else
        echo "❌ Nginx重载失败"
        echo "   请手动检查: sudo systemctl status nginx"
        exit 1
    fi
else
    echo "❌ Nginx配置测试失败"
    echo "   正在恢复备份..."
    cp "$BACKUP_FILE" "$NGINX_CONF"
    echo "   已恢复原配置"
    exit 1
fi
