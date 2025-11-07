#!/bin/bash
# ==========================================
# Linux服务器一键部署脚本（不使用Docker）
# ==========================================

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}=========================================="
echo "🚀 股票分析系统 - Linux部署脚本"
echo -e "==========================================${NC}"
echo ""

# 获取项目根目录
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BACKEND_DIR="$PROJECT_ROOT/backend"
FRONTEND_DIR="$PROJECT_ROOT/frontend"
DATA_DIR="$PROJECT_ROOT/data"

echo -e "${BLUE}项目路径: $PROJECT_ROOT${NC}"
echo ""

# ==========================================
# 检查系统依赖
# ==========================================
echo -e "${YELLOW}📋 检查系统依赖...${NC}"

# 检查Python
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}❌ Python3 未安装${NC}"
    exit 1
fi
PYTHON_VERSION=$(python3 --version)
echo -e "${GREEN}✓ $PYTHON_VERSION${NC}"

# 检查pip
if ! command -v pip3 &> /dev/null; then
    echo -e "${RED}❌ pip3 未安装${NC}"
    exit 1
fi
echo -e "${GREEN}✓ pip3 已安装${NC}"

# 检查Node.js
if ! command -v node &> /dev/null; then
    echo -e "${RED}❌ Node.js 未安装${NC}"
    echo "请安装Node.js 16+: https://nodejs.org/"
    exit 1
fi
NODE_VERSION=$(node --version)
echo -e "${GREEN}✓ Node.js $NODE_VERSION${NC}"

# 检查npm
if ! command -v npm &> /dev/null; then
    echo -e "${RED}❌ npm 未安装${NC}"
    exit 1
fi
NPM_VERSION=$(npm --version)
echo -e "${GREEN}✓ npm $NPM_VERSION${NC}"

# 检查PostgreSQL
if ! command -v psql &> /dev/null; then
    echo -e "${YELLOW}⚠  PostgreSQL客户端未安装${NC}"
    echo "如果数据库在远程服务器，可以忽略此警告"
else
    echo -e "${GREEN}✓ PostgreSQL 已安装${NC}"
fi

echo ""

# ==========================================
# 配置后端
# ==========================================
echo -e "${YELLOW}🔧 配置后端...${NC}"

cd "$BACKEND_DIR"

# 检查.env文件
if [ ! -f .env ]; then
    if [ -f .env.example ]; then
        echo -e "${YELLOW}⚠  .env 文件不存在，从模板创建...${NC}"
        cp .env.example .env
        echo -e "${YELLOW}⚠  请编辑 backend/.env 文件配置数据库连接！${NC}"
        read -p "按回车继续... " 
    else
        echo -e "${RED}❌ .env.example 不存在${NC}"
        exit 1
    fi
else
    echo -e "${GREEN}✓ .env 配置文件存在${NC}"
fi

# 创建虚拟环境
if [ ! -d "venv" ]; then
    echo "创建Python虚拟环境..."
    python3 -m venv venv
    echo -e "${GREEN}✓ 虚拟环境已创建${NC}"
else
    echo -e "${GREEN}✓ 虚拟环境已存在${NC}"
fi

# 激活虚拟环境并安装依赖
echo "安装Python依赖..."
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
echo -e "${GREEN}✓ Python依赖已安装${NC}"

echo ""

# ==========================================
# 配置前端
# ==========================================
echo -e "${YELLOW}🎨 配置前端...${NC}"

cd "$FRONTEND_DIR"

# 检查package.json
if [ ! -f package.json ]; then
    echo -e "${RED}❌ package.json 不存在${NC}"
    exit 1
fi

# 安装npm依赖
if [ ! -d "node_modules" ]; then
    echo "安装npm依赖..."
    npm install
    echo -e "${GREEN}✓ npm依赖已安装${NC}"
else
    echo -e "${GREEN}✓ npm依赖已存在${NC}"
fi

# 询问是否构建前端
read -p "是否立即构建前端生产版本？(y/n) " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo "构建前端..."
    npm run build
    echo -e "${GREEN}✓ 前端构建完成${NC}"
else
    echo -e "${YELLOW}⚠  跳过前端构建（开发模式需要单独启动）${NC}"
fi

echo ""

# ==========================================
# 检查数据目录
# ==========================================
echo -e "${YELLOW}📊 检查数据目录...${NC}"

if [ ! -d "$DATA_DIR" ]; then
    mkdir -p "$DATA_DIR"
    echo -e "${GREEN}✓ 创建data目录${NC}"
fi

XLSX_COUNT=$(ls -1 "$DATA_DIR"/*.xlsx 2>/dev/null | wc -l)
if [ "$XLSX_COUNT" -eq "0" ]; then
    echo -e "${YELLOW}⚠  data目录中没有Excel文件${NC}"
    echo "请将Excel文件放到: $DATA_DIR"
else
    echo -e "${GREEN}✓ 找到 $XLSX_COUNT 个Excel文件${NC}"
fi

echo ""

# ==========================================
# 数据库初始化
# ==========================================
echo -e "${YELLOW}🗄️  数据库初始化...${NC}"

cd "$BACKEND_DIR"
source venv/bin/activate

# 测试数据库连接
echo "测试数据库连接..."
if python -c "from app.database import test_connection; import sys; sys.exit(0 if test_connection() else 1)" 2>/dev/null; then
    echo -e "${GREEN}✓ 数据库连接成功${NC}"
    
    # 询问是否导入数据
    read -p "是否导入Excel数据到数据库？(y/n) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        echo "开始导入数据..."
        python scripts/import_data_robust.py
        echo -e "${GREEN}✓ 数据导入完成${NC}"
    else
        echo -e "${YELLOW}⚠  跳过数据导入${NC}"
    fi
else
    echo -e "${RED}❌ 数据库连接失败${NC}"
    echo "请检查:"
    echo "  1. PostgreSQL是否运行"
    echo "  2. backend/.env 配置是否正确"
    echo "  3. 数据库用户是否有权限"
fi

echo ""

# ==========================================
# 创建启动脚本
# ==========================================
echo -e "${YELLOW}📝 创建启动脚本...${NC}"

# 创建后端启动脚本
cat > "$PROJECT_ROOT/start_backend_linux.sh" << 'EOF'
#!/bin/bash
cd "$(dirname "$0")/backend"
source venv/bin/activate
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
EOF
chmod +x "$PROJECT_ROOT/start_backend_linux.sh"
echo -e "${GREEN}✓ 创建 start_backend_linux.sh${NC}"

# 创建前端启动脚本（开发模式）
cat > "$PROJECT_ROOT/start_frontend_linux.sh" << 'EOF'
#!/bin/bash
cd "$(dirname "$0")/frontend"
npm start
EOF
chmod +x "$PROJECT_ROOT/start_frontend_linux.sh"
echo -e "${GREEN}✓ 创建 start_frontend_linux.sh${NC}"

echo ""

# ==========================================
# 完成
# ==========================================
echo -e "${GREEN}=========================================="
echo "✅ 部署准备完成！"
echo -e "==========================================${NC}"
echo ""
echo "📝 下一步："
echo ""
echo "1️⃣  配置数据库连接:"
echo "   nano backend/.env"
echo ""
echo "2️⃣  启动后端（在一个终端）:"
echo "   ./start_backend_linux.sh"
echo "   或后台运行: nohup ./start_backend_linux.sh > backend.log 2>&1 &"
echo ""
echo "3️⃣  启动前端（在另一个终端，开发模式）:"
echo "   ./start_frontend_linux.sh"
echo ""
echo "4️⃣  访问应用:"
echo "   前端: http://localhost:3000"
echo "   API:  http://localhost:8000/docs"
echo ""
echo "💡 生产环境部署:"
echo "   阅读 LINUX_DEPLOY_GUIDE.md 配置 systemd + nginx"
echo ""
echo -e "${GREEN}=========================================="
echo "🎉 祝你部署顺利！"
echo -e "==========================================${NC}"
