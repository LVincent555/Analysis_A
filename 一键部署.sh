#!/bin/bash
# 股票分析系统 v0.2.6 - 服务器一键部署脚本
# 使用方法：bash 一键部署.sh
# 参考文档：docs/⚠️重要-配置文件管理和常见错误.md

set -e  # 遇到错误立即退出

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

PROJECT_DIR="$(cd "$(dirname "$0")" && pwd)"
BACKUP_DIR="$HOME/backup_$(date +%Y%m%d_%H%M%S)"

echo ""
echo "============================================================"
echo "🚀 股票分析系统 v0.2.6 - 服务器部署脚本"
echo "============================================================"
echo ""
echo "📍 项目目录: $PROJECT_DIR"
echo "📁 备份目录: $BACKUP_DIR"
echo ""

# ============================================================
# 步骤 1: 备份重要配置文件
# ============================================================
echo "============================================================"
echo "💾 步骤 1/7: 备份重要配置文件"
echo "============================================================"

mkdir -p "$BACKUP_DIR"

# 备份数据库配置
if [ -f "$PROJECT_DIR/backend/app/database.py" ]; then
    cp "$PROJECT_DIR/backend/app/database.py" "$BACKUP_DIR/database.py"
    echo "✅ 已备份: database.py"
else
    echo -e "${YELLOW}⚠️  database.py 不存在，首次部署需要配置${NC}"
fi

# 备份数据导入状态
if [ -f "$PROJECT_DIR/data/data_import_state.json" ]; then
    cp "$PROJECT_DIR/data/data_import_state.json" "$BACKUP_DIR/data_import_state.json"
    echo "✅ 已备份: data_import_state.json"
fi

# 备份sector导入状态
if [ -f "$PROJECT_DIR/data/sector_import_state.json" ]; then
    cp "$PROJECT_DIR/data/sector_import_state.json" "$BACKUP_DIR/sector_import_state.json"
    echo "✅ 已备份: sector_import_state.json"
fi

echo ""

# ============================================================
# 步骤 2: 拉取最新代码
# ============================================================
echo "============================================================"
echo "📥 步骤 2/7: 拉取最新代码"
echo "============================================================"

cd "$PROJECT_DIR"

# 显示当前版本
CURRENT_COMMIT=$(git rev-parse --short HEAD)
echo "当前版本: $CURRENT_COMMIT"

# 拉取代码
echo "正在拉取最新代码..."
git pull origin main

NEW_COMMIT=$(git rev-parse --short HEAD)
echo "✅ 代码更新完成"
echo "新版本: $NEW_COMMIT"
echo ""

# ============================================================
# 步骤 3: 恢复重要配置文件
# ============================================================
echo "============================================================"
echo "🔄 步骤 3/7: 检查并恢复配置文件"
echo "============================================================"

# 检查database.py是否被覆盖
if [ -f "$PROJECT_DIR/backend/app/database.py" ]; then
    DB_HOST=$(grep "DB_HOST" "$PROJECT_DIR/backend/app/database.py" | head -1)
    echo "检查到: $DB_HOST"
    
    # 检查是否是本地IP（被覆盖的标志）
    if echo "$DB_HOST" | grep -q "192.168"; then
        echo -e "${RED}❌ 检测到database.py被覆盖为本地配置！${NC}"
        echo "正在恢复备份..."
        if [ -f "$BACKUP_DIR/database.py" ]; then
            cp "$BACKUP_DIR/database.py" "$PROJECT_DIR/backend/app/database.py"
            echo "✅ 已恢复: database.py"
        else
            echo -e "${RED}✗ 错误: 备份文件不存在！${NC}"
            echo "请手动配置 backend/app/database.py"
            exit 1
        fi
    else
        echo "✅ database.py 配置正常"
    fi
else
    echo -e "${YELLOW}⚠️  database.py 不存在${NC}"
    if [ -f "$BACKUP_DIR/database.py" ]; then
        cp "$BACKUP_DIR/database.py" "$PROJECT_DIR/backend/app/database.py"
        echo "✅ 已恢复: database.py"
    else
        echo -e "${RED}✗ 需要配置数据库，请参考 backend/app/database.py.example${NC}"
        exit 1
    fi
fi

# 恢复数据导入状态
if [ -f "$BACKUP_DIR/data_import_state.json" ]; then
    cp "$BACKUP_DIR/data_import_state.json" "$PROJECT_DIR/data/data_import_state.json"
    echo "✅ 已恢复: data_import_state.json"
fi

if [ -f "$BACKUP_DIR/sector_import_state.json" ]; then
    cp "$BACKUP_DIR/sector_import_state.json" "$PROJECT_DIR/data/sector_import_state.json"
    echo "✅ 已恢复: sector_import_state.json"
fi

echo ""

# ============================================================
# 步骤 4: 检查前端构建文件
# ============================================================
echo "============================================================"
echo "🔍 步骤 4/7: 检查前端构建文件"
echo "============================================================"

if [ ! -d "$PROJECT_DIR/frontend/build" ]; then
    echo -e "${RED}✗ 错误: frontend/build 目录不存在！${NC}"
    echo ""
    echo "请在本地执行以下命令："
    echo "  cd frontend"
    echo "  npm run build"
    echo "  git add frontend/build"
    echo "  git commit -m 'build: 更新前端构建文件'"
    echo "  git push"
    exit 1
fi

BUILD_FILES=$(find "$PROJECT_DIR/frontend/build" -type f | wc -l)
if [ "$BUILD_FILES" -lt 5 ]; then
    echo -e "${RED}✗ 错误: 构建文件不完整！${NC}"
    echo "文件数量: $BUILD_FILES (应该 > 5)"
    exit 1
fi

echo "✅ 前端构建文件完整"
echo "   文件数量: $BUILD_FILES"
echo "   构建目录: $PROJECT_DIR/frontend/build"
echo ""

# ============================================================
# 步骤 5: 清除Python缓存
# ============================================================
echo "============================================================"
echo "🧹 步骤 5/7: 清除Python缓存"
echo "============================================================"

cd "$PROJECT_DIR/backend"

# 清除__pycache__
find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
find . -name "*.pyc" -delete 2>/dev/null || true

echo "✅ Python缓存已清除"
echo ""

# ============================================================
# 步骤 6: 停止现有服务
# ============================================================
echo "============================================================"
echo "🛑 步骤 6/7: 停止现有服务"
echo "============================================================"

# 使用bash stop.sh脚本（如果存在）
if [ -f "$PROJECT_DIR/stop.sh" ]; then
    bash "$PROJECT_DIR/stop.sh"
else
    # 手动停止
    BACKEND_PIDS=$(pgrep -f "uvicorn.*app.main" || true)
    if [ -n "$BACKEND_PIDS" ]; then
        echo "正在停止后端服务 (PIDs: $BACKEND_PIDS)..."
        kill $BACKEND_PIDS 2>/dev/null || true
        sleep 2
        # 强制杀死
        kill -9 $BACKEND_PIDS 2>/dev/null || true
        echo "✅ 后端服务已停止"
    else
        echo "ℹ️  后端服务未运行"
    fi
fi

echo ""

# ============================================================
# 步骤 7: 启动服务
# ============================================================
echo "============================================================"
echo "▶️  步骤 7/7: 启动服务"
echo "============================================================"

# 使用bash start_all.sh脚本
if [ -f "$PROJECT_DIR/start_all.sh" ]; then
    bash "$PROJECT_DIR/start_all.sh"
else
    echo -e "${YELLOW}⚠️  start_all.sh 不存在，手动启动服务${NC}"
    
    # 创建日志目录
    mkdir -p "$PROJECT_DIR/logs"
    
    # 启动后端
    cd "$PROJECT_DIR/backend"
    echo "正在启动后端服务..."
    nohup python3 -m uvicorn app.main:app --host 0.0.0.0 --port 8000 > "$PROJECT_DIR/logs/backend.log" 2>&1 &
    BACKEND_PID=$!
    
    # 等待启动
    sleep 3
    
    # 检查是否成功
    if ps -p $BACKEND_PID > /dev/null; then
        echo "✅ 后端已启动 (PID: $BACKEND_PID)"
    else
        echo -e "${RED}✗ 后端启动失败${NC}"
        echo "查看日志: tail -f $PROJECT_DIR/logs/backend.log"
        exit 1
    fi
fi

echo ""

# ============================================================
# 部署完成
# ============================================================
echo "============================================================"
echo "✅ 部署完成！v0.2.6"
echo "============================================================"
echo ""

# 显示服务状态
echo "📊 服务状态:"
if ps aux | grep -v grep | grep "uvicorn.*app.main" > /dev/null; then
    BACKEND_PID=$(pgrep -f "uvicorn.*app.main")
    echo -e "  ${GREEN}✓${NC} 后端API: 运行中 (PID: $BACKEND_PID)"
else
    echo -e "  ${RED}✗${NC} 后端API: 未运行"
fi

echo ""
echo "🌐 访问地址:"
echo "  • 后端API: http://localhost:8000"
echo "  • API文档: http://localhost:8000/docs"
echo "  • 前端页面: http://60.205.251.109 (通过Nginx)"
echo ""

# 测试后端API
echo "🧪 测试后端API:"
if curl -s http://localhost:8000/api/dates > /dev/null; then
    echo -e "  ${GREEN}✓${NC} API响应正常"
else
    echo -e "  ${RED}✗${NC} API无响应，请检查日志"
fi

echo ""
echo "📝 常用命令:"
echo "  • 查看后端日志: tail -f $PROJECT_DIR/logs/backend.log"
echo "  • 停止服务: bash $PROJECT_DIR/stop.sh"
echo "  • 重启服务: bash $PROJECT_DIR/start_all.sh"
echo "  • 查看进程: ps aux | grep uvicorn"
echo ""

# 检查Nginx配置
echo "🔧 Nginx配置检查:"
if [ -f "/etc/nginx/sites-enabled/stock_analysis" ]; then
    echo -e "  ${GREEN}✓${NC} Nginx配置已启用"
    
    # 测试Nginx代理
    if curl -s http://localhost/api/dates > /dev/null; then
        echo -e "  ${GREEN}✓${NC} Nginx代理正常"
    else
        echo -e "  ${YELLOW}⚠️${NC} Nginx代理可能未工作，请检查配置"
    fi
else
    echo -e "  ${YELLOW}⚠️${NC} Nginx配置未启用"
    echo ""
    echo "配置Nginx:"
    echo "  sudo nginx -t"
    echo "  sudo systemctl reload nginx"
fi

echo ""
echo "📦 备份信息:"
echo "  配置备份保存在: $BACKUP_DIR"
echo "  如需回滚，请手动恢复备份文件"
echo ""

# 版本信息
echo "📌 版本信息:"
echo "  • 当前版本: v0.2.6"
echo "  • Git提交: $NEW_COMMIT"
echo "  • 部署时间: $(date '+%Y-%m-%d %H:%M:%S')"
echo ""

echo "============================================================"
echo "🎉 部署成功！访问 http://60.205.251.109 查看网站"
echo "============================================================"
echo ""
