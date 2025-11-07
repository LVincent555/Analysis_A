#!/bin/bash
# 停止所有服务

echo "🛑 停止所有服务..."

# 方式1: 使用服务管理器
if [ -f "deploy/scripts/service_manager.py" ]; then
    python3 deploy/scripts/service_manager.py stop all
fi

# 方式2: 直接杀进程（确保停止）
echo ""
echo "🔍 检查并停止进程..."

# 停止后端
BACKEND_PID=$(ps aux | grep "uvicorn app.main:app" | grep -v grep | awk '{print $2}')
if [ -n "$BACKEND_PID" ]; then
    echo "  停止后端 (PID: $BACKEND_PID)"
    kill $BACKEND_PID 2>/dev/null
fi

# 停止前端
FRONTEND_PID=$(ps aux | grep "npm start" | grep -v grep | awk '{print $2}')
if [ -n "$FRONTEND_PID" ]; then
    echo "  停止前端 (PID: $FRONTEND_PID)"
    kill $FRONTEND_PID 2>/dev/null
fi

# 停止node进程（前端）
NODE_PIDS=$(ps aux | grep "node.*react-scripts start" | grep -v grep | awk '{print $2}')
if [ -n "$NODE_PIDS" ]; then
    echo "  停止Node进程: $NODE_PIDS"
    kill $NODE_PIDS 2>/dev/null
fi

sleep 2
echo ""
echo "✓ 所有服务已停止"
