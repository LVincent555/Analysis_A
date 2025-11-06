#!/bin/bash
# ==========================================
# Docker & Docker Compose 自动安装脚本
# 适用于 Ubuntu/Debian 系统
# ==========================================

set -e

echo "==========================================="
echo "🐳 Docker 自动安装脚本"
echo "==========================================="

# 颜色定义
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

# 检查是否为root用户
if [ "$EUID" -ne 0 ]; then 
    echo -e "${RED}❌ 请使用root权限运行此脚本${NC}"
    echo "使用: sudo $0"
    exit 1
fi

# 检测系统类型
if [ -f /etc/os-release ]; then
    . /etc/os-release
    OS=$ID
    VER=$VERSION_ID
else
    echo -e "${RED}❌ 无法检测系统类型${NC}"
    exit 1
fi

echo "检测到系统: $OS $VER"

# 检查Docker是否已安装
if command -v docker &> /dev/null; then
    DOCKER_VERSION=$(docker --version)
    echo -e "${YELLOW}⚠️  Docker 已安装: $DOCKER_VERSION${NC}"
    read -p "是否重新安装？(y/n): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo "跳过Docker安装"
        SKIP_DOCKER=1
    fi
fi

# 安装Docker
if [ -z "$SKIP_DOCKER" ]; then
    echo ""
    echo -e "${YELLOW}📦 开始安装 Docker...${NC}"
    echo "-------------------------------------------"
    
    # 卸载旧版本
    echo "1. 卸载旧版本..."
    apt-get remove -y docker docker-engine docker.io containerd runc 2>/dev/null || true
    
    # 更新apt包索引
    echo "2. 更新包索引..."
    apt-get update
    
    # 安装依赖
    echo "3. 安装依赖包..."
    apt-get install -y \
        ca-certificates \
        curl \
        gnupg \
        lsb-release
    
    # 添加Docker官方GPG密钥
    echo "4. 添加Docker GPG密钥..."
    mkdir -p /etc/apt/keyrings
    curl -fsSL https://download.docker.com/linux/$OS/gpg | gpg --dearmor -o /etc/apt/keyrings/docker.gpg
    
    # 设置Docker仓库
    echo "5. 设置Docker仓库..."
    echo \
      "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/$OS \
      $(lsb_release -cs) stable" | tee /etc/apt/sources.list.d/docker.list > /dev/null
    
    # 安装Docker Engine
    echo "6. 安装Docker Engine..."
    apt-get update
    apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
    
    # 启动Docker
    echo "7. 启动Docker服务..."
    systemctl start docker
    systemctl enable docker
    
    echo -e "${GREEN}✅ Docker 安装完成！${NC}"
fi

# 检查Docker Compose
echo ""
echo -e "${YELLOW}📦 检查 Docker Compose...${NC}"
echo "-------------------------------------------"

if command -v docker-compose &> /dev/null; then
    COMPOSE_VERSION=$(docker-compose --version)
    echo -e "${GREEN}✅ Docker Compose 已安装: $COMPOSE_VERSION${NC}"
else
    # Docker Compose plugin应该已经安装
    if docker compose version &> /dev/null; then
        echo -e "${GREEN}✅ Docker Compose (plugin) 已安装${NC}"
    else
        echo -e "${YELLOW}⚠️  安装 Docker Compose...${NC}"
        # 安装独立版本的docker-compose
        COMPOSE_VERSION=$(curl -s https://api.github.com/repos/docker/compose/releases/latest | grep 'tag_name' | cut -d\" -f4)
        curl -L "https://github.com/docker/compose/releases/download/${COMPOSE_VERSION}/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
        chmod +x /usr/local/bin/docker-compose
        ln -sf /usr/local/bin/docker-compose /usr/bin/docker-compose
        echo -e "${GREEN}✅ Docker Compose 安装完成！${NC}"
    fi
fi

# 配置用户权限
echo ""
echo -e "${YELLOW}👤 配置用户权限...${NC}"
echo "-------------------------------------------"
read -p "请输入需要使用Docker的用户名（默认: $SUDO_USER）: " DOCKER_USER
DOCKER_USER=${DOCKER_USER:-$SUDO_USER}

if [ ! -z "$DOCKER_USER" ]; then
    usermod -aG docker $DOCKER_USER
    echo -e "${GREEN}✅ 用户 $DOCKER_USER 已添加到docker组${NC}"
    echo -e "${YELLOW}⚠️  注意: 需要重新登录才能生效${NC}"
fi

# 验证安装
echo ""
echo "==========================================="
echo "🧪 验证安装"
echo "==========================================="
echo ""
echo "Docker 版本:"
docker --version
echo ""
echo "Docker Compose 版本:"
docker compose version 2>/dev/null || docker-compose --version
echo ""
echo "Docker 状态:"
systemctl status docker --no-pager -l | head -3
echo ""

# 测试运行
echo -e "${YELLOW}📝 运行测试容器...${NC}"
if docker run --rm hello-world &> /dev/null; then
    echo -e "${GREEN}✅ Docker 测试成功！${NC}"
else
    echo -e "${RED}❌ Docker 测试失败${NC}"
    exit 1
fi

# 完成
echo ""
echo "==========================================="
echo -e "${GREEN}🎉 Docker 安装完成！${NC}"
echo "==========================================="
echo ""
echo "📝 接下来的步骤："
echo "   1. 重新登录以使docker组权限生效"
echo "   2. 或运行: newgrp docker"
echo "   3. 测试: docker run hello-world"
echo "   4. 部署应用: ./deploy.sh"
echo ""
echo "📚 更多信息:"
echo "   Docker 文档: https://docs.docker.com"
echo "   Docker Compose: https://docs.docker.com/compose"
echo "==========================================="
