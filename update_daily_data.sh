#!/bin/bash
###############################################################################
# 每日数据更新脚本 (Linux/Mac)
# 
# 使用方法：
#   1. 将新的Excel数据文件放入 data/ 目录
#   2. 运行此脚本：./update_daily_data.sh
#
# 首次运行需要给予执行权限：
#   chmod +x update_daily_data.sh
###############################################################################

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 获取脚本所在目录
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR"

echo -e "${BLUE}═══════════════════════════════════════════════════════════════${NC}"
echo -e "${BLUE}🚀 每日数据更新任务${NC}"
echo -e "${BLUE}═══════════════════════════════════════════════════════════════${NC}"
echo ""
echo "📅 执行时间: $(date '+%Y-%m-%d %H:%M:%S')"
echo "📂 工作目录: $SCRIPT_DIR"
echo ""

# 检查Python是否存在
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}❌ 错误: 未找到 python3${NC}"
    echo "请先安装 Python 3"
    exit 1
fi

# 检查数据目录
if [ ! -d "data" ]; then
    echo -e "${RED}❌ 错误: data 目录不存在${NC}"
    exit 1
fi

# 检查数据文件
STOCK_COUNT=$(ls data/*_data_sma_feature_color.xlsx 2>/dev/null | wc -l)
SECTOR_COUNT=$(ls data/*_allbk_sma_feature_color.xlsx 2>/dev/null | wc -l)

echo "📊 找到股票数据文件: ${STOCK_COUNT} 个"
echo "📊 找到板块数据文件: ${SECTOR_COUNT} 个"
echo ""

if [ "$STOCK_COUNT" -eq 0 ] && [ "$SECTOR_COUNT" -eq 0 ]; then
    echo -e "${YELLOW}⚠️  没有找到待导入的数据文件${NC}"
    echo "提示：请将数据文件放入 data/ 目录"
    echo "  - 股票数据：YYYYMMDD_data_sma_feature_color.xlsx"
    echo "  - 板块数据：YYYYMMDD_allbk_sma_feature_color.xlsx"
    exit 0
fi

# 运行Python更新脚本
echo -e "${BLUE}───────────────────────────────────────────────────────────────${NC}"
echo "执行 Python 更新脚本..."
echo ""

python3 update_daily_data.py
EXIT_CODE=$?

echo ""
echo -e "${BLUE}═══════════════════════════════════════════════════════════════${NC}"

if [ $EXIT_CODE -eq 0 ]; then
    echo -e "${GREEN}✅ 数据更新完成！${NC}"
else
    echo -e "${RED}❌ 数据更新失败 (退出码: $EXIT_CODE)${NC}"
    echo "请查看日志文件获取详细信息"
fi

echo -e "${BLUE}═══════════════════════════════════════════════════════════════${NC}"
echo ""

exit $EXIT_CODE
