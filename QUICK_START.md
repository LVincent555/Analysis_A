# 🚀 Stock Analysis App - 快速开始指南

## 📋 5分钟快速部署

### 前置要求

✅ 服务器配置: 2核2G+  
✅ 操作系统: Linux (Ubuntu 20.04+ / CentOS 8+)  
✅ 已安装: Docker 20.10+ 和 Docker Compose 2.0+

---

## 🎯 部署步骤

### 1️⃣ 克隆项目

```bash
git clone <your-repo-url>
cd stock_analysis_app
```

### 2️⃣ 配置环境

```bash
# 复制环境变量模板
cp .env.example .env

# 编辑.env文件，设置数据库密码
nano .env
```

修改这一行：
```env
DATABASE_PASSWORD=your_strong_password_here
```

### 3️⃣ 准备数据

```bash
# 创建数据目录
mkdir -p data

# 上传Excel文件到data目录
# 文件命名格式: YYYYMMDD_data_sma_feature_color.xlsx
```

### 4️⃣ 执行部署

```bash
# 赋予执行权限
chmod +x deploy.sh backup.sh

# 一键部署
./deploy.sh
```

选择 **1** (全新部署)，等待几分钟。

### 5️⃣ 验证部署

```bash
# 检查服务状态
docker-compose ps

# 应该看到3个容器都是 "Up" 状态
```

访问应用：
- 前端: http://your-server-ip
- API文档: http://your-server-ip/api/docs

---

## 📊 测试功能

1. **热点分析**: 点击左侧"最新热点"
2. **股票查询**: 输入股票代码（如：000657）
3. **排名跳变**: 点击"排名跳变"
4. **行业趋势**: 点击"行业趋势分析"

---

## 🔧 常用命令

### 查看日志
```bash
docker-compose logs -f
```

### 重启服务
```bash
docker-compose restart
```

### 停止服务
```bash
docker-compose down
```

### 备份数据
```bash
./backup.sh
```

---

## 📝 更多信息

- **完整文档**: README_DEPLOY.md
- **项目说明**: PROJECT_OVERVIEW.md
- **API文档**: http://localhost/api/docs（部署后访问）

---

## 🆘 遇到问题？

### 端口被占用
编辑 `.env`，修改 `WEB_PORT=8080`

### 内存不足
添加Swap分区:
```bash
sudo fallocate -l 2G /swapfile
sudo chmod 600 /swapfile
sudo mkswap /swapfile
sudo swapon /swapfile
```

### 数据未导入
进入容器手动导入:
```bash
docker-compose exec backend bash
python scripts/import_data_robust.py
```

### 查看详细错误
```bash
docker-compose logs backend
```

---

**🎉 部署成功！开始使用吧！**
