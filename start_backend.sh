#!/bin/bash
# 启动后端服务

echo "========================================"
echo "🚀 启动后端服务"
echo "========================================"

cd "$(dirname "$0")/backend"

# 激活虚拟环境并启动
source venv/bin/activate
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

echo "后端服务已停止"
