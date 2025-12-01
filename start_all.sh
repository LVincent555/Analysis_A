#!/bin/bash
# 一键启动所有服务（后端 + 前端）
# 用法: ./start_all.sh [dev|prod]

PROJECT_DIR="$(cd "$(dirname "$0")" && pwd)"
MODE=${1:-prod}  # 默认生产模式

echo "============================================================"
echo "🚀 一键启动股票分析系统 - ${MODE^^} 模式"
echo "============================================================"
echo ""
echo "📍 项目目录: $PROJECT_DIR"

if [ "$MODE" = "prod" ]; then
    echo "📋 生产模式:"
    echo "   1️⃣  后端API  (http://0.0.0.0:8000)"
    echo "   2️⃣  前端构建 (静态文件，需要Nginx)"
else
    echo "📋 开发模式:"
    echo "   1️⃣  后端API  (http://0.0.0.0:8000)"
    echo "   2️⃣  前端应用 (http://0.0.0.0:3000)"
fi
echo ""
echo "============================================================"

# 创建日志目录
mkdir -p "$PROJECT_DIR/logs"

# 后台启动后端
echo ""
echo "▶ 启动后端服务..."
cd "$PROJECT_DIR/backend"

if [ "$MODE" = "prod" ]; then
    # 生产模式：不使用--reload，禁用API文档
    nohup python3 -m uvicorn app.main:app --host 0.0.0.0 --port 8000 > "$PROJECT_DIR/logs/backend.log" 2>&1 &
else
    # 开发模式：使用--reload自动重载，启用API文档
    ENABLE_DOCS=true nohup python3 -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload > "$PROJECT_DIR/logs/backend.log" 2>&1 &
fi

BACKEND_PID=$!
echo "✓ 后端已启动 (PID: $BACKEND_PID)"
echo "  日志: $PROJECT_DIR/logs/backend.log"

# 等待后端启动
sleep 3

if [ "$MODE" = "prod" ]; then
    # 生产模式：检查前端build目录
    echo ""
    echo "▶ 检查前端构建..."
    cd "$PROJECT_DIR/frontend"
    
    if [ ! -d "build" ]; then
        echo "  ✗ 前端build目录不存在！"
        echo "  📝 请在本地执行: npm run build"
        echo "  📝 然后 git push，在服务器上git pull"
        exit 1
    else
        echo "✓ 前端build目录已存在"
        echo "  构建目录: $PROJECT_DIR/frontend/build"
        echo "  📄 文件数: $(find build -type f | wc -l)"
    fi
    
    FRONTEND_PID="N/A"
else
    # 开发模式：启动开发服务器
    echo ""
    echo "▶ 启动前端开发服务器..."
    cd "$PROJECT_DIR/frontend"
    
    # 检查proxy配置
    if ! grep -q '"proxy"' package.json; then
        echo "  ⚠️  警告：package.json 缺少 proxy 配置"
        echo "  添加proxy配置以连接后端..."
        
        # 备份package.json
        cp package.json package.json.bak
        
        # 添加proxy（在最后一个}之前）
        sed -i '$ s/}/,\n  "proxy": "http:\/\/localhost:8000"\n}/' package.json
        echo "  ✓ 已添加 proxy 配置"
    fi
    
    nohup npm start > "$PROJECT_DIR/logs/frontend.log" 2>&1 &
    FRONTEND_PID=$!
    echo "✓ 前端已启动 (PID: $FRONTEND_PID)"
    echo "  日志: $PROJECT_DIR/logs/frontend.log"
    
    # 等待前端启动
    echo ""
    echo "⏳ 等待前端启动（约30-60秒）..."
    sleep 10
fi

echo ""
echo "============================================================"
echo "✅ 所有服务已启动！"
echo "============================================================"
echo ""

if [ "$MODE" = "prod" ]; then
    echo "📊 服务状态:"
    echo "  • 后端: PID $BACKEND_PID"
    echo "  • 前端: 已构建静态文件"
    echo ""
    echo "🌐 访问方式:"
    echo "  • 后端API:  http://60.205.251.109:8000"
    echo "  • 前端: 需要配置Nginx"
    echo "  ℹ️  生产环境已禁用API文档"
    echo ""
    echo "📝 Nginx配置示例:"
    echo "  server {"
    echo "    listen 80;"
    echo "    root $PROJECT_DIR/frontend/build;"
    echo "    location /api { proxy_pass http://localhost:8000; }"
    echo "  }"
    echo ""
    echo "📖 详细配置: deploy/configs/nginx-stock-analysis.conf"
else
    echo "📊 服务状态:"
    ps aux | grep -E "uvicorn|node" | grep -v grep | awk '{printf "  • PID %-6s  %s\n", $2, $11}'
    echo ""
    echo "🌐 访问地址:"
    echo "  • 后端API:  http://60.205.251.109:8000"
    echo "  • API文档:  http://60.205.251.109:8000/docs (开发模式)"
    echo "  • 前端应用: http://60.205.251.109:3000"
    echo ""
    echo "💡 提示: 前端通过proxy连接后端"
    echo ""
    echo "📝 查看日志:"
    echo "  tail -f $PROJECT_DIR/logs/backend.log"
    echo "  tail -f $PROJECT_DIR/logs/frontend.log"
fi

echo ""
echo "🛑 停止服务:"
echo "  ./stop.sh"
if [ "$FRONTEND_PID" != "N/A" ]; then
    echo "  或者: kill $BACKEND_PID $FRONTEND_PID"
fi
echo ""
echo "============================================================"
