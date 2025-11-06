#!/bin/bash
# ==========================================
# Stock Analysis App - 停止服务脚本
# ==========================================

echo "==========================================="
echo "🛑 Stock Analysis App - 停止服务"
echo "==========================================="

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

# 询问停止方式
echo ""
echo "请选择停止方式："
echo "1. 停止服务（保留数据和容器）"
echo "2. 停止并删除容器（保留数据）"
echo "3. 停止并删除所有（包括数据卷）⚠️"
read -p "请选择 (1/2/3): " -n 1 -r
echo

case $REPLY in
    1)
        echo -e "${YELLOW}🛑 停止服务（保留数据和容器）...${NC}"
        docker-compose stop
        echo -e "${GREEN}✅ 服务已停止${NC}"
        echo "💡 重启服务: docker-compose start"
        ;;
    2)
        echo -e "${YELLOW}🛑 停止并删除容器（保留数据）...${NC}"
        docker-compose down
        echo -e "${GREEN}✅ 容器已删除，数据已保留${NC}"
        echo "💡 重新部署: ./deploy.sh"
        ;;
    3)
        echo -e "${RED}⚠️  警告: 将删除所有数据！${NC}"
        read -p "确认删除所有数据？(yes/no): " confirm
        if [ "$confirm" = "yes" ]; then
            echo -e "${YELLOW}🗑️  停止并删除所有（包括数据卷）...${NC}"
            docker-compose down -v
            echo -e "${GREEN}✅ 所有容器和数据已删除${NC}"
            echo "💡 重新部署: ./deploy.sh"
        else
            echo -e "${YELLOW}❌ 操作已取消${NC}"
        fi
        ;;
    *)
        echo -e "${RED}❌ 无效选择${NC}"
        exit 1
        ;;
esac

echo "==========================================="
