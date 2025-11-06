#!/bin/bash
# ==========================================
# Stock Analysis App - 管理脚本入口
# ==========================================

echo "==========================================="
echo "🎛️  Stock Analysis App - 管理面板"
echo "==========================================="

# 颜色定义
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'

while true; do
    echo ""
    echo -e "${CYAN}请选择操作：${NC}"
    echo "-------------------------------------------"
    echo "  1. 🚀 部署/启动服务"
    echo "  2. 🛑 停止服务"
    echo "  3. 📊 查看状态"
    echo "  4. 📋 查看日志"
    echo "  5. 🔄 更新数据"
    echo "  6. 💾 备份数据库"
    echo "  7. 🔨 重启服务"
    echo "  8. 🧹 清理Docker资源"
    echo "  0. 退出"
    echo "-------------------------------------------"
    read -p "请输入选项 (0-8): " choice

    case $choice in
        1)
            echo ""
            ./deploy.sh
            ;;
        2)
            echo ""
            ./stop.sh
            ;;
        3)
            echo ""
            ./status.sh
            ;;
        4)
            echo ""
            ./logs.sh
            ;;
        5)
            echo ""
            ./update_data.sh
            ;;
        6)
            echo ""
            ./backup.sh
            ;;
        7)
            echo -e "${YELLOW}🔄 重启所有服务...${NC}"
            docker-compose restart
            echo -e "${GREEN}✅ 服务已重启${NC}"
            ;;
        8)
            echo -e "${YELLOW}🧹 清理Docker资源...${NC}"
            echo "这将删除未使用的镜像、容器、网络和卷"
            read -p "确认清理？(y/n): " -n 1 -r
            echo
            if [[ $REPLY =~ ^[Yy]$ ]]; then
                docker system prune -a --volumes
                echo -e "${GREEN}✅ 清理完成${NC}"
            fi
            ;;
        0)
            echo -e "${GREEN}👋 再见！${NC}"
            exit 0
            ;;
        *)
            echo -e "${YELLOW}⚠️  无效选项，请重新选择${NC}"
            ;;
    esac
    
    echo ""
    read -p "按回车键继续..." 
    clear
    echo "==========================================="
    echo "🎛️  Stock Analysis App - 管理面板"
    echo "==========================================="
done
