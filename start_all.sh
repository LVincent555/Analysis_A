#!/bin/bash
# 一键启动所有服务（后端 + 前端）

PROJECT_DIR="$(cd "$(dirname "$0")" && pwd)"

echo "============================================================"
echo "🚀 一键启动股票分析系统"
echo "============================================================"
echo ""
echo "📍 项目目录: $PROJECT_DIR"
echo "📋 将启动以下服务:"
echo "   1️⃣  后端API  (http://localhost:8000)"
echo "   2️⃣  前端应用 (http://localhost:3000)"
echo ""
echo "============================================================"

# 创建日志目录
mkdir -p "$PROJECT_DIR/logs"

# 后台启动后端
echo ""
echo "▶ 启动后端服务..."
cd "$PROJECT_DIR/backend"
nohup bash -c "source venv/bin/activate && python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload" > "$PROJECT_DIR/logs/backend.log" 2>&1 &
BACKEND_PID=$!
echo "✓ 后端已启动 (PID: $BACKEND_PID)"
echo "  日志: $PROJECT_DIR/logs/backend.log"

# 等待后端启动
sleep 3

# 后台启动前端
echo ""
echo "▶ 启动前端服务..."
cd "$PROJECT_DIR/frontend"
nohup npm start > "$PROJECT_DIR/logs/frontend.log" 2>&1 &
FRONTEND_PID=$!
echo "✓ 前端已启动 (PID: $FRONTEND_PID)"
echo "  日志: $PROJECT_DIR/logs/frontend.log"

# 等待前端启动
echo ""
echo "⏳ 等待服务完全启动..."
sleep 10

echo ""
echo "============================================================"
echo "✅ 所有服务已启动！"
echo "============================================================"
echo ""
echo "📊 服务状态:"
ps aux | grep -E "uvicorn|node" | grep -v grep | awk '{printf "  • PID %-6s  %s\n", $2, $11}'

echo ""
echo "🌐 访问地址:"
echo "  • 后端API:  http://localhost:8000"
echo "  • API文档:  http://localhost:8000/docs"
echo "  • 前端应用: http://localhost:3000"
echo ""
echo "📝 查看日志:"
echo "  tail -f $PROJECT_DIR/logs/backend.log"
echo "  tail -f $PROJECT_DIR/logs/frontend.log"
echo ""
echo "🛑 停止服务:"
echo "  ./stop.sh"
echo "  或者: kill $BACKEND_PID $FRONTEND_PID"
echo ""
echo "============================================================"
