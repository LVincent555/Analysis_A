#!/bin/bash
# 股票分析系统 - 服务器一键部署脚本
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

# 获取当前版本（从git tag）
CURRENT_VERSION=$(git describe --tags --abbrev=0 2>/dev/null || echo "未知版本")

echo ""
echo "============================================================"
echo "🚀 股票分析系统 $CURRENT_VERSION - 服务器部署脚本"
echo "============================================================"
echo ""
echo "📍 项目目录: $PROJECT_DIR"
echo "📁 备份目录: $BACKUP_DIR"
echo ""

# ============================================================
# 步骤 1: 备份重要配置文件
# ============================================================
echo "============================================================"
echo "💾 步骤 1/9: 备份重要配置文件"
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
echo "📥 步骤 2/9: 拉取最新代码"
echo "============================================================"

cd "$PROJECT_DIR"

# 显示当前版本
OLD_VERSION=$(git describe --tags --abbrev=0 2>/dev/null || echo "未知")
CURRENT_COMMIT=$(git rev-parse --short HEAD)
echo "当前版本: $OLD_VERSION ($CURRENT_COMMIT)"

# 拉取代码
echo "正在拉取最新代码..."
git pull origin main

NEW_VERSION=$(git describe --tags --abbrev=0 2>/dev/null || echo "未知")
NEW_COMMIT=$(git rev-parse --short HEAD)
echo "✅ 代码更新完成"
echo "新版本: $NEW_VERSION ($NEW_COMMIT)"
echo ""

# ============================================================
# 步骤 3: 恢复重要配置文件
# ============================================================
echo "============================================================"
echo "🔄 步骤 3/9: 检查并恢复配置文件"
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

# 检查数据导入状态文件
# 注意：状态文件应该跟随代码更新，只在文件不存在时才恢复备份
if [ ! -f "$PROJECT_DIR/data/data_import_state.json" ] && [ -f "$BACKUP_DIR/data_import_state.json" ]; then
    cp "$BACKUP_DIR/data_import_state.json" "$PROJECT_DIR/data/data_import_state.json"
    echo "✅ 已恢复: data_import_state.json（文件缺失）"
else
    echo "ℹ️  data_import_state.json 保持最新版本"
fi

if [ ! -f "$PROJECT_DIR/data/sector_import_state.json" ] && [ -f "$BACKUP_DIR/sector_import_state.json" ]; then
    cp "$BACKUP_DIR/sector_import_state.json" "$PROJECT_DIR/data/sector_import_state.json"
    echo "✅ 已恢复: sector_import_state.json（文件缺失）"
else
    echo "ℹ️  sector_import_state.json 保持最新版本"
fi

echo ""

# ============================================================
# 步骤 4: 部署客户端更新文件
# ============================================================
echo "============================================================"
echo "📦 步骤 4/9: 部署客户端更新文件"
echo "============================================================"

# 客户端更新目录
UPDATES_DIR="/var/www/stock-analysis/updates"
CLIENT_DIST_DIR="$PROJECT_DIR/frontend-client/dist"

# 确保更新目录存在
mkdir -p "$UPDATES_DIR"

# 检查是否有新的客户端构建文件
if [ -d "$CLIENT_DIST_DIR" ]; then
    # 检查 latest.yml 文件
    if [ -f "$CLIENT_DIST_DIR/latest.yml" ]; then
        echo "发现客户端更新文件，正在部署..."
        
        # 复制更新文件到服务目录
        cp -f "$CLIENT_DIST_DIR/latest.yml" "$UPDATES_DIR/"
        echo "  ✅ 已复制: latest.yml"
        
        # 复制所有 .exe 文件
        for exe_file in "$CLIENT_DIST_DIR"/*.exe; do
            if [ -f "$exe_file" ]; then
                cp -f "$exe_file" "$UPDATES_DIR/"
                echo "  ✅ 已复制: $(basename "$exe_file")"
            fi
        done
        
        # 复制 blockmap 文件（用于增量更新）
        for blockmap_file in "$CLIENT_DIST_DIR"/*.blockmap; do
            if [ -f "$blockmap_file" ]; then
                cp -f "$blockmap_file" "$UPDATES_DIR/"
                echo "  ✅ 已复制: $(basename "$blockmap_file")"
            fi
        done
        
        # 显示更新版本
        UPDATE_VERSION=$(grep "version:" "$UPDATES_DIR/latest.yml" | head -1 | awk '{print $2}')
        echo ""
        echo "✅ 客户端更新文件部署完成"
        echo "   版本: $UPDATE_VERSION"
        echo "   目录: $UPDATES_DIR"
    else
        echo "ℹ️  未发现新的客户端构建 (latest.yml 不存在)"
        echo "   如需更新客户端，请在本地执行:"
        echo "   cd frontend-client && npm run build && npm run electron:build"
    fi
else
    echo "ℹ️  客户端构建目录不存在，跳过客户端更新"
fi

echo ""

# ============================================================
# 步骤 5: 安装/更新 Python 依赖
# ============================================================
echo "============================================================"
echo "📦 步骤 5/9: 安装/更新 Python 依赖"
echo "============================================================"

cd "$PROJECT_DIR/backend"

# 检查 requirements.txt 是否存在
if [ -f "requirements.txt" ]; then
    echo "正在安装 Python 依赖..."
    # 使用 --break-system-packages 解决 Debian/Ubuntu 系统的 PEP 668 限制
    pip3 install -r requirements.txt --quiet --upgrade --break-system-packages 2>&1 | grep -v "already satisfied" || true
    echo "✅ Python 依赖安装完成"
else
    echo -e "${YELLOW}⚠️  requirements.txt 不存在，跳过依赖安装${NC}"
fi

echo ""

# ============================================================
# 步骤 6: 清除Python缓存
# ============================================================
echo "============================================================"
echo "🧹 步骤 6/9: 清除Python缓存"
echo "============================================================"

cd "$PROJECT_DIR/backend"

# 清除__pycache__
find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
find . -name "*.pyc" -delete 2>/dev/null || true

echo "✅ Python缓存已清除"
echo ""

# ============================================================
# 步骤 7: 停止现有服务
# ============================================================
echo "============================================================"
echo "🛑 步骤 7/9: 停止现有服务"
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
# 步骤 7: 初始化用户账户（如果需要）
# ============================================================
echo "============================================================"
echo "👤 步骤 8/9: 检查用户账户"
echo "============================================================"

cd "$PROJECT_DIR/backend"

# 检查是否需要初始化用户
echo "检查用户表..."
USER_COUNT=$(python3 -c "
from app.database import SessionLocal
from app.db_models import User
db = SessionLocal()
count = db.query(User).count()
print(count)
db.close()
" 2>/dev/null || echo "0")

if [ "$USER_COUNT" = "0" ]; then
    echo "⚠️  用户表为空，正在初始化默认用户（随机密码）..."
    python3 scripts/init_users.py --auto
    echo ""
    echo -e "${YELLOW}⚠️  请记录以上密码信息！${NC}"
else
    echo "✅ 已有 $USER_COUNT 个用户，跳过初始化"
fi

echo ""

# ============================================================
# 步骤 8: 启动服务
# ============================================================
echo "============================================================"
echo "▶️  步骤 9/9: 启动服务"
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
echo "✅ 部署完成！$NEW_VERSION"
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
echo "  • 前端页面: http://60.205.251.109 (通过Nginx)"
echo "  ℹ️  生产环境已禁用API文档（安全考虑）"
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
    
    # 检查更新目录是否可访问
    if curl -s -o /dev/null -w "%{http_code}" http://localhost:8000/updates/latest.yml | grep -q "200\|404"; then
        echo -e "  ${GREEN}✓${NC} 客户端更新目录可访问"
    else
        echo -e "  ${YELLOW}⚠️${NC} 客户端更新目录可能未配置"
        echo "     请确保 Nginx 配置了 /updates/ 静态目录"
    fi
else
    echo -e "  ${YELLOW}⚠️${NC} Nginx配置未启用"
    echo ""
    echo "配置Nginx:"
    echo "  sudo nginx -t"
    echo "  sudo systemctl reload nginx"
fi

# 显示客户端更新状态
echo ""
echo "📱 客户端更新状态:"
if [ -f "$UPDATES_DIR/latest.yml" ]; then
    CLIENT_VERSION=$(grep "version:" "$UPDATES_DIR/latest.yml" | head -1 | awk '{print $2}')
    echo -e "  ${GREEN}✓${NC} 当前客户端版本: $CLIENT_VERSION"
    echo "     更新地址: http://60.205.251.109:8000/updates/"
else
    echo -e "  ${YELLOW}⚠️${NC} 暂无客户端更新文件"
fi

echo ""
echo "📦 备份信息:"
echo "  配置备份保存在: $BACKUP_DIR"
echo "  如需回滚，请手动恢复备份文件"
echo ""

# 版本信息
echo "📌 版本信息:"
echo "  • 当前版本: $NEW_VERSION"
echo "  • Git提交: $NEW_COMMIT"
echo "  • 部署时间: $(date '+%Y-%m-%d %H:%M:%S')"
echo ""

echo "============================================================"
echo "🎉 部署成功！访问 http://60.205.251.109 查看网站"
echo "============================================================"
echo ""
