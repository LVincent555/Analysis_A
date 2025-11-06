#!/bin/bash
# ==========================================
# Stock Analysis App - 日志查看脚本
# ==========================================

echo "==========================================="
echo "📋 Stock Analysis App - 日志查看"
echo "==========================================="

# 颜色定义
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo ""
echo "请选择查看方式："
echo "1. 查看所有服务日志（实时）"
echo "2. 查看后端日志"
echo "3. 查看数据库日志"
echo "4. 查看Nginx日志"
echo "5. 查看最近100行日志"
echo "6. 查看错误日志"
read -p "请选择 (1-6): " -n 1 -r
echo

case $REPLY in
    1)
        echo -e "${YELLOW}📋 查看所有服务日志（按Ctrl+C退出）...${NC}"
        docker-compose logs -f
        ;;
    2)
        echo -e "${YELLOW}📋 查看后端日志（按Ctrl+C退出）...${NC}"
        docker-compose logs -f backend
        ;;
    3)
        echo -e "${YELLOW}📋 查看数据库日志（按Ctrl+C退出）...${NC}"
        docker-compose logs -f postgres
        ;;
    4)
        echo -e "${YELLOW}📋 查看Nginx日志（按Ctrl+C退出）...${NC}"
        docker-compose logs -f nginx
        ;;
    5)
        echo -e "${YELLOW}📋 查看最近100行日志...${NC}"
        docker-compose logs --tail=100
        ;;
    6)
        echo -e "${YELLOW}📋 查看错误日志...${NC}"
        docker-compose logs | grep -i error
        echo ""
        echo "💡 提示: 使用 docker-compose logs -f 查看实时日志"
        ;;
    *)
        echo -e "${YELLOW}❌ 无效选择，显示最近50行日志${NC}"
        docker-compose logs --tail=50
        ;;
esac
