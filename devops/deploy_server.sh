#!/bin/bash
# 服务器一键部署脚本
# 在服务器上执行：bash deploy_server.sh

set -e  # 遇到错误立即退出

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

echo "============================================================"
echo "🚀 服务器部署脚本 v0.2.4"
echo "============================================================"
echo ""
echo "📍 项目目录: $PROJECT_DIR"
echo ""

# 1. 拉取最新代码
echo "============================================================"
echo "📥 步骤 1/5: 拉取最新代码"
echo "============================================================"
cd "$PROJECT_DIR"
git pull origin main
echo "✓ 代码更新完成"
echo ""

# 2. 检查frontend-client/build目录
echo "============================================================"
echo "🔍 步骤 2/5: 检查前端构建文件"
echo "============================================================"
if [ ! -d "frontend-client/build" ]; then
    echo "✗ 错误: frontend-client/build目录不存在！"
    echo "  请在本地执行："
    echo "    cd frontend-client"
    echo "    npm run build"
    echo "    git add frontend-client/build"
    echo "    git commit -m 'build: 更新前端构建文件'"
    echo "    git push"
    exit 1
fi

BUILD_FILES=$(find frontend-client/build -type f | wc -l)
echo "✓ 前端构建文件已存在"
echo "  文件数量: $BUILD_FILES"
echo "  构建目录: $PROJECT_DIR/frontend-client/build"
echo ""

# 3. 安装/更新Python依赖
echo "============================================================"
echo "📦 步骤 3/5: 检查Python依赖"
echo "============================================================"
cd "$PROJECT_DIR/backend"
if [ -f "requirements.txt" ]; then
    pip3 install -r requirements.txt --quiet
    echo "✓ Python依赖已更新"
else
    echo "⚠️  未找到requirements.txt"
fi
echo ""

# 4. 停止现有服务
echo "============================================================"
echo "🛑 步骤 4/5: 停止现有服务"
echo "============================================================"

# 停止后端
BACKEND_PIDS=$(pgrep -f "uvicorn.*app.main" || true)
if [ -n "$BACKEND_PIDS" ]; then
    echo "  停止后端服务 (PIDs: $BACKEND_PIDS)..."
    kill $BACKEND_PIDS 2>/dev/null || true
    sleep 2
    # 强制杀死
    kill -9 $BACKEND_PIDS 2>/dev/null || true
    echo "✓ 后端服务已停止"
else
    echo "  后端服务未运行"
fi

echo ""

# 5. 启动服务
echo "============================================================"
echo "▶️  步骤 5/5: 启动服务"
echo "============================================================"

# 创建日志目录
mkdir -p "$PROJECT_DIR/logs"

# 启动后端（生产模式）
cd "$PROJECT_DIR/backend"
echo "  启动后端服务..."
nohup python3 -m uvicorn app.main:app --host 0.0.0.0 --port 8000 > "$PROJECT_DIR/logs/backend.log" 2>&1 &
BACKEND_PID=$!
echo "✓ 后端已启动 (PID: $BACKEND_PID)"

# 等待后端启动
sleep 3

# 检查后端是否成功启动
if ps -p $BACKEND_PID > /dev/null; then
    echo "✓ 后端运行正常"
else
    echo "✗ 后端启动失败，查看日志："
    echo "  tail -f $PROJECT_DIR/logs/backend.log"
    exit 1
fi

echo ""
echo "============================================================"
echo "✅ 部署完成！"
echo "============================================================"
echo ""
echo "📊 服务状态:"
echo "  • 后端API: PID $BACKEND_PID (端口 8000)"
echo "  • 前端: 静态文件 (需要Nginx)"
echo ""
echo "🌐 访问地址:"
echo "  • 后端API: http://localhost:8000"
echo "  • API文档: http://localhost:8000/docs"
echo "  • 前端: 通过Nginx访问 (http://60.205.251.109)"
echo ""
echo "📝 查看日志:"
echo "  tail -f $PROJECT_DIR/logs/backend.log"
echo ""
echo "🔧 配置Nginx:"
echo "  sudo cp deploy/nginx.conf.example /etc/nginx/sites-available/stock_analysis"
echo "  sudo ln -s /etc/nginx/sites-available/stock_analysis /etc/nginx/sites-enabled/"
echo "  sudo nginx -t && sudo systemctl reload nginx"
echo ""
echo "🛑 停止服务:"
echo "  kill $BACKEND_PID"
echo ""
echo "============================================================"
