#!/bin/bash
# ==========================================
# Stock Analysis App - 状态检查脚本
# ==========================================

echo "==========================================="
echo "📊 Stock Analysis App - 状态检查"
echo "==========================================="

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

# 1. 检查容器状态
echo ""
echo "📦 容器状态："
echo "-------------------------------------------"
docker-compose ps
echo ""

# 2. 检查资源使用
echo "💾 资源使用："
echo "-------------------------------------------"
docker stats --no-stream --format "table {{.Name}}\t{{.CPUPerc}}\t{{.MemUsage}}\t{{.MemPerc}}"
echo ""

# 3. 检查健康状态
echo "🏥 健康检查："
echo "-------------------------------------------"
HEALTHY=0
TOTAL=3

# 检查 PostgreSQL
if docker-compose exec -T postgres pg_isready -U stock_user &>/dev/null; then
    echo -e "${GREEN}✅ PostgreSQL: 健康${NC}"
    ((HEALTHY++))
else
    echo -e "${RED}❌ PostgreSQL: 异常${NC}"
fi

# 检查 Backend
if curl -f http://localhost:8000/api/dates &>/dev/null 2>&1; then
    echo -e "${GREEN}✅ Backend: 健康${NC}"
    ((HEALTHY++))
else
    echo -e "${RED}❌ Backend: 异常${NC}"
fi

# 检查 Nginx
if curl -f http://localhost:80 &>/dev/null 2>&1; then
    echo -e "${GREEN}✅ Nginx: 健康${NC}"
    ((HEALTHY++))
else
    echo -e "${RED}❌ Nginx: 异常${NC}"
fi

echo ""
echo "健康度: $HEALTHY/$TOTAL"
echo ""

# 4. 检查数据库
echo "🗄️  数据库状态："
echo "-------------------------------------------"
DB_SIZE=$(docker-compose exec -T postgres psql -U stock_user -d stock_analysis -t -c "SELECT pg_size_pretty(pg_database_size('stock_analysis'));" 2>/dev/null | xargs)
STOCK_COUNT=$(docker-compose exec -T postgres psql -U stock_user -d stock_analysis -t -c "SELECT COUNT(*) FROM stocks;" 2>/dev/null | xargs)
DATA_COUNT=$(docker-compose exec -T postgres psql -U stock_user -d stock_analysis -t -c "SELECT COUNT(*) FROM daily_stock_data;" 2>/dev/null | xargs)

if [ ! -z "$DB_SIZE" ]; then
    echo "数据库大小: $DB_SIZE"
    echo "股票数量: $STOCK_COUNT"
    echo "数据记录: $DATA_COUNT"
else
    echo -e "${RED}⚠️  无法连接到数据库${NC}"
fi

echo ""

# 5. 检查磁盘空间
echo "💿 磁盘空间："
echo "-------------------------------------------"
df -h | grep -E "Filesystem|/$" | head -2

echo ""
echo "==========================================="

# 6. 访问信息
if [ $HEALTHY -eq $TOTAL ]; then
    echo -e "${GREEN}🎉 所有服务运行正常！${NC}"
    echo ""
    echo "📝 访问地址："
    echo "   前端: http://localhost"
    echo "   API:  http://localhost/api/docs"
else
    echo -e "${YELLOW}⚠️  部分服务异常${NC}"
    echo ""
    echo "💡 排查建议："
    echo "   查看日志: ./logs.sh"
    echo "   重启服务: docker-compose restart"
fi

echo "==========================================="
