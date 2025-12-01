#!/bin/bash
# 启动后端服务（本地开发用）
# 默认启用 API 文档

echo "========================================"
echo "🚀 启动后端服务（开发模式）"
echo "========================================"

cd "$(dirname "$0")/backend"

# 激活虚拟环境并启动
# ENABLE_DOCS=true 启用 Swagger/OpenAPI 文档
source venv/bin/activate
ENABLE_DOCS=true python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

echo "后端服务已停止"
