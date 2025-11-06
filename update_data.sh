#!/bin/bash
# ==========================================
# Stock Analysis App - 数据更新脚本
# ==========================================

echo "==========================================="
echo "🔄 Stock Analysis App - 数据更新"
echo "==========================================="

# 颜色定义
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

# 检查data目录
if [ ! -d "./data" ]; then
    echo -e "${RED}❌ data 目录不存在${NC}"
    exit 1
fi

# 统计Excel文件
EXCEL_COUNT=$(ls -1 ./data/*.xlsx 2>/dev/null | wc -l)
echo ""
echo "📊 Excel文件统计："
echo "   找到 $EXCEL_COUNT 个Excel文件"
echo ""

if [ "$EXCEL_COUNT" -eq "0" ]; then
    echo -e "${RED}❌ 没有找到Excel文件${NC}"
    echo "请将新的Excel文件放到 ./data 目录"
    exit 1
fi

# 显示文件列表
echo "📁 文件列表："
ls -lh ./data/*.xlsx 2>/dev/null | awk '{print "   " $9 " (" $5 ")"}'
echo ""

# 询问是否继续
read -p "是否导入这些文件到数据库？(y/n): " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo -e "${YELLOW}❌ 操作已取消${NC}"
    exit 0
fi

echo ""
echo -e "${YELLOW}🔄 开始导入数据...${NC}"
echo "-------------------------------------------"

# 执行导入
docker-compose exec backend python scripts/import_data_robust.py

if [ $? -eq 0 ]; then
    echo ""
    echo -e "${GREEN}✅ 数据导入成功！${NC}"
    echo ""
    echo -e "${YELLOW}🧹 清除缓存...${NC}"
    docker-compose exec backend python clear_cache.py
    
    echo ""
    echo -e "${GREEN}✅ 缓存已清除${NC}"
    echo ""
    echo "💡 提示："
    echo "   - 数据已更新，前端会自动加载新数据"
    echo "   - 查看导入状态: cat data/data_import_state.json"
    echo "   - 检查数据: docker-compose exec postgres psql -U stock_user stock_analysis"
else
    echo ""
    echo -e "${RED}❌ 数据导入失败${NC}"
    echo "请查看日志: ./logs.sh"
fi

echo "==========================================="
