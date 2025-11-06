#!/bin/bash
# ==========================================
# Stock Analysis App - 一键部署脚本
# ==========================================

set -e

echo "==========================================="
echo "🚀 Stock Analysis App - 部署脚本"
echo "==========================================="

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 检查Docker是否安装
if ! command -v docker &> /dev/null; then
    echo -e "${RED}❌ Docker 未安装！${NC}"
    echo "请先安装 Docker: https://docs.docker.com/get-docker/"
    exit 1
fi

if ! command -v docker-compose &> /dev/null; then
    echo -e "${RED}❌ Docker Compose 未安装！${NC}"
    echo "请先安装 Docker Compose: https://docs.docker.com/compose/install/"
    exit 1
fi

echo -e "${GREEN}✅ Docker 已安装${NC}"
echo -e "${GREEN}✅ Docker Compose 已安装${NC}"

# 检查.env文件
if [ ! -f .env ]; then
    echo -e "${YELLOW}⚠️  .env 文件不存在，从模板创建...${NC}"
    cp .env.example .env
    echo -e "${YELLOW}⚠️  请编辑 .env 文件并设置数据库密码！${NC}"
    echo -e "${YELLOW}   执行: nano .env 或 vim .env${NC}"
    read -p "按回车继续... " 
fi

# 检查data目录
if [ ! -d "./data" ]; then
    echo -e "${YELLOW}⚠️  创建 data 目录...${NC}"
    mkdir -p ./data
fi

EXCEL_COUNT=$(ls -1 ./data/*.xlsx 2>/dev/null | wc -l)
if [ "$EXCEL_COUNT" -eq "0" ]; then
    echo -e "${YELLOW}⚠️  警告: data 目录中没有 Excel 文件${NC}"
    echo -e "${YELLOW}   请将 Excel 文件放到 ./data 目录${NC}"
    read -p "是否继续部署？(y/n) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
else
    echo -e "${GREEN}✅ 找到 $EXCEL_COUNT 个 Excel 文件${NC}"
fi

# 询问部署模式
echo ""
echo "请选择部署模式："
echo "1. 全新部署（清除旧数据）"
echo "2. 重启服务（保留数据）"
echo "3. 更新应用（重新构建）"
read -p "请选择 (1/2/3): " -n 1 -r
echo

case $REPLY in
    1)
        echo -e "${YELLOW}📦 执行全新部署（清除旧数据）...${NC}"
        docker-compose down -v
        docker-compose build --no-cache
        docker-compose up -d
        ;;
    2)
        echo -e "${YELLOW}🔄 重启服务（保留数据）...${NC}"
        docker-compose restart
        ;;
    3)
        echo -e "${YELLOW}🔨 更新应用（重新构建）...${NC}"
        docker-compose down
        docker-compose build
        docker-compose up -d
        ;;
    *)
        echo -e "${RED}❌ 无效选择${NC}"
        exit 1
        ;;
esac

# 等待服务启动
echo ""
echo -e "${YELLOW}⏳ 等待服务启动...${NC}"
sleep 10

# 检查服务状态
echo ""
echo "==========================================="
echo "📊 服务状态："
echo "==========================================="
docker-compose ps

# 检查健康状态
echo ""
echo "🏥 健康检查："
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
if curl -f http://localhost:8000/api/dates &>/dev/null; then
    echo -e "${GREEN}✅ Backend: 健康${NC}"
    ((HEALTHY++))
else
    echo -e "${YELLOW}⚠️  Backend: 启动中...${NC}"
fi

# 检查 Nginx
if curl -f http://localhost:80 &>/dev/null; then
    echo -e "${GREEN}✅ Nginx: 健康${NC}"
    ((HEALTHY++))
else
    echo -e "${RED}❌ Nginx: 异常${NC}"
fi

echo ""
echo "==========================================="
if [ $HEALTHY -eq $TOTAL ]; then
    echo -e "${GREEN}🎉 部署成功！所有服务正常运行${NC}"
    echo ""
    echo "📝 访问信息："
    echo "   前端地址: http://localhost"
    echo "   API文档:  http://localhost/api/docs"
    echo "   数据库:   localhost:5432"
    echo ""
    echo "📊 查看日志:"
    echo "   docker-compose logs -f"
    echo ""
    echo "🛑 停止服务:"
    echo "   docker-compose down"
else
    echo -e "${YELLOW}⚠️  部署完成，但有 $((TOTAL-HEALTHY)) 个服务未就绪${NC}"
    echo "请稍等片刻或查看日志: docker-compose logs -f"
fi
echo "==========================================="
