
# 🚀 Linux服务器部署指南（不使用Docker）

## 📋 系统要求

- **操作系统**: Linux (Ubuntu 20.04+, CentOS 8+)
- **Python**: 3.8+
- **Node.js**: 16+
- **PostgreSQL**: 12+
- **内存**: 2GB+
- **磁盘**: 10GB+

---

## 🔧 准备工作

### 1. 安装PostgreSQL

**Ubuntu/Debian:**
```bash
sudo apt update
sudo apt install postgresql postgresql-contrib
sudo systemctl start postgresql
sudo systemctl enable postgresql
```

**CentOS/RHEL:**
```bash
sudo dnf install postgresql-server postgresql-contrib
sudo postgresql-setup --initdb
sudo systemctl start postgresql
sudo systemctl enable postgresql
```

### 2. 创建数据库和用户

```bash
# 切换到postgres用户
sudo -u postgres psql

# 在psql中执行：
CREATE DATABASE stock_analysis;
CREATE USER stock_user WITH PASSWORD 'your_strong_password';
GRANT ALL PRIVILEGES ON DATABASE stock_analysis TO stock_user;
\q
```

### 3. 配置PostgreSQL允许本地连接

编辑 `/etc/postgresql/*/main/pg_hba.conf` (路径可能不同):

```
# 添加以下行
local   all             stock_user                              md5
host    all             stock_user      127.0.0.1/32            md5
```

重启PostgreSQL:
```bash
sudo systemctl restart postgresql
```

---

## 📦 部署步骤

### 1. 上传项目到服务器

```bash
# 使用scp或git
scp -r stock_analysis_app user@server:/path/to/deploy/
# 或
git clone <your-repo> /path/to/deploy/stock_analysis_app
```

### 2. 配置后端

```bash
cd /path/to/deploy/stock_analysis_app/backend

# 复制环境变量模板
cp .env.example .env

# 编辑.env文件
nano .env
```

修改以下配置：
```env
DB_HOST=localhost
DB_PORT=5432
DB_NAME=stock_analysis
DB_USER=stock_user
DB_PASSWORD=your_strong_password
```

### 3. 安装Python依赖

```bash
# 创建虚拟环境（推荐）
python3 -m venv venv
source venv/bin/activate

# 安装依赖
pip install -r requirements.txt
```

### 4. 初始化数据库表

```bash
# 在backend目录下
python -c "from app.db_models import Base; from app.database import engine; Base.metadata.create_all(engine)"
```

### 5. 上传数据文件

```bash
# 将Excel文件放到data目录
mkdir -p ../data
cp /path/to/your/*.xlsx ../data/
```

### 6. 导入数据

```bash
python scripts/import_data_robust.py
```

### 7. 安装前端依赖并构建

```bash
cd ../frontend
npm install
npm run build
```

---

## 🚀 启动服务

### 方式一：使用Python启动脚本（推荐）

```bash
cd /path/to/deploy/stock_analysis_app

# 启动后端（在一个终端）
python start_backend.py

# 启动前端（在另一个终端）
python start_frontend.py

# 或一键启动（后台运行）
nohup python start_backend.py > backend.log 2>&1 &
nohup python start_frontend.py > frontend.log 2>&1 &
```

### 方式二：使用系统服务（生产环境推荐）

创建systemd服务文件，参见下方"生产环境部署"部分。

---

## 🌐 访问应用

- **前端**: http://server-ip:3000
- **API文档**: http://server-ip:8000/docs
- **健康检查**: http://server-ip:8000/api/dates

---

## 🔥 生产环境部署

### 使用Systemd管理服务

#### 1. 创建后端服务文件

```bash
sudo nano /etc/systemd/system/stock-backend.service
```

内容：
```ini
[Unit]
Description=Stock Analysis Backend
After=network.target postgresql.service

[Service]
Type=simple
User=your_user
WorkingDirectory=/path/to/stock_analysis_app/backend
Environment="PATH=/path/to/stock_analysis_app/backend/venv/bin"
ExecStart=/path/to/stock_analysis_app/backend/venv/bin/python -m uvicorn app.main:app --host 0.0.0.0 --port 8000
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

#### 2. 启动并启用服务

```bash
sudo systemctl daemon-reload
sudo systemctl start stock-backend
sudo systemctl enable stock-backend
sudo systemctl status stock-backend
```

### 使用Nginx作为前端和反向代理

#### 1. 安装Nginx

```bash
sudo apt install nginx  # Ubuntu
sudo dnf install nginx  # CentOS
```

#### 2. 配置Nginx

```bash
sudo nano /etc/nginx/sites-available/stock-analysis
```

内容：
```nginx
server {
    listen 80;
    server_name your-domain.com;

    # 前端静态文件
    location / {
        root /path/to/stock_analysis_app/frontend/build;
        try_files $uri $uri/ /index.html;
    }

    # API反向代理
    location /api {
        proxy_pass http://localhost:8000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_cache_bypass $http_upgrade;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    }
}
```

启用配置：
```bash
sudo ln -s /etc/nginx/sites-available/stock-analysis /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl restart nginx
```

---

## 🔍 故障排查

### 后端无法连接数据库

```bash
# 检查PostgreSQL状态
sudo systemctl status postgresql

# 测试数据库连接
psql -h localhost -U stock_user -d stock_analysis

# 查看后端日志
journalctl -u stock-backend -f
```

### 前端无法访问API

```bash
# 检查后端是否运行
curl http://localhost:8000/api/dates

# 检查防火墙
sudo ufw status
sudo ufw allow 8000
sudo ufw allow 3000
```

### 内存不足

```bash
# 创建Swap
sudo fallocate -l 2G /swapfile
sudo chmod 600 /swapfile
sudo mkswap /swapfile
sudo swapon /swapfile
echo '/swapfile none swap sw 0 0' | sudo tee -a /etc/fstab
```

---

## 🛠 维护命令

```bash
# 查看服务状态
sudo systemctl status stock-backend

# 重启服务
sudo systemctl restart stock-backend

# 查看日志
journalctl -u stock-backend -f

# 更新数据
cd /path/to/stock_analysis_app/backend
source venv/bin/activate
python scripts/import_data_robust.py

# 备份数据库
pg_dump -U stock_user -d stock_analysis > backup_$(date +%Y%m%d).sql
```

---

## ✅ 部署检查清单

- [ ] PostgreSQL已安装并运行
- [ ] 数据库和用户已创建
- [ ] Python虚拟环境已创建
- [ ] Python依赖已安装
- [ ] .env文件已配置
- [ ] 数据库表已创建
- [ ] Excel数据已导入
- [ ] 前端已构建
- [ ] 后端服务正常运行
- [ ] 前端可以访问
- [ ] API可以正常调用
- [ ] Nginx配置正确（如果使用）

---

🎉 部署完成！
