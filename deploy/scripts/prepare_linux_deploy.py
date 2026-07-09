#!/usr/bin/env python3
"""
Linux服务器部署准备脚本
检查和创建Linux部署所需的所有文件和配置
"""

import os
import sys
from pathlib import Path
import shutil

class LinuxDeploymentPreparer:
    """Linux部署准备器"""
    
    def __init__(self, project_root: str):
        self.project_root = Path(project_root)
        self.checks = []
        
    def check_all(self):
        """执行所有检查"""
        print("=" * 70)
        print("🔍 Linux部署准备检查")
        print("=" * 70)
        print()
        
        self.check_project_structure()
        self.check_backend_config()
        self.check_frontend_config()
        self.check_data_directory()
        self.check_scripts()
        
        self.print_summary()
        
    def check_project_structure(self):
        """检查项目结构"""
        print("📁 检查项目结构...")
        
        required_dirs = [
            "backend",
            "backend/app",
            "backend/scripts",
            "frontend-client",
            "frontend-client/src",
            "devops",
            "sql",
            "data"
        ]
        
        for dir_path in required_dirs:
            full_path = self.project_root / dir_path
            if full_path.exists():
                print(f"   ✓ {dir_path}")
            else:
                print(f"   ⚠ {dir_path} 不存在，将创建...")
                full_path.mkdir(parents=True, exist_ok=True)
                self.checks.append(("warning", f"创建目录: {dir_path}"))
        
        print()
        
    def check_backend_config(self):
        """检查后端配置"""
        print("🔧 检查后端配置...")
        
        # 检查requirements.txt
        req_file = self.project_root / "backend" / "requirements.txt"
        if req_file.exists():
            print(f"   ✓ requirements.txt 存在")
        else:
            print(f"   ❌ requirements.txt 不存在")
            self.checks.append(("error", "缺少 requirements.txt"))
        
        # 检查.env.example
        env_example = self.project_root / "backend" / ".env.example"
        if env_example.exists():
            print(f"   ✓ .env.example 存在")
        else:
            print(f"   ⚠ .env.example 不存在")
            self.checks.append(("warning", "建议创建 .env.example"))
        
        # 检查.env
        env_file = self.project_root / "backend" / ".env"
        if env_file.exists():
            print(f"   ✓ .env 存在")
        else:
            print(f"   ⚠ .env 不存在，需要从 .env.example 复制并配置")
            self.checks.append(("warning", "需要配置 .env 文件"))
        
        print()
        
    def check_frontend_config(self):
        """检查前端配置"""
        print("🎨 检查前端配置...")
        
        package_json = self.project_root / "frontend-client" / "package.json"
        if package_json.exists():
            print(f"   ✓ package.json 存在")
        else:
            print(f"   ❌ package.json 不存在")
            self.checks.append(("error", "缺少 package.json"))
        
        print()
        
    def check_data_directory(self):
        """检查数据目录"""
        print("📊 检查数据目录...")
        
        data_dir = self.project_root / "data"
        if not data_dir.exists():
            data_dir.mkdir(parents=True, exist_ok=True)
            print(f"   ✓ 创建 data 目录")
        
        xlsx_files = list(data_dir.glob("*.xlsx"))
        if xlsx_files:
            print(f"   ✓ 找到 {len(xlsx_files)} 个Excel文件")
        else:
            print(f"   ⚠ data 目录为空，需要上传Excel文件")
            self.checks.append(("warning", "需要上传Excel数据文件"))
        
        print()
        
    def check_scripts(self):
        """检查Python启动脚本"""
        print("🚀 检查启动脚本...")
        
        scripts = [
            "devops/start_backend.py",
            "devops/start_frontend.py",
            "devops/start_all.py"
        ]
        
        for script in scripts:
            script_path = self.project_root / script
            if script_path.exists():
                print(f"   ✓ {script}")
                # 在Linux上确保脚本有执行权限
                if os.name != 'nt':  # 不是Windows
                    os.chmod(script_path, 0o755)
            else:
                print(f"   ⚠ {script} 不存在")
                self.checks.append(("warning", f"缺少 {script}"))
        
        print()
        
    def print_summary(self):
        """打印总结"""
        errors = [c for c in self.checks if c[0] == "error"]
        warnings = [c for c in self.checks if c[0] == "warning"]
        
        print("=" * 70)
        print("📋 检查总结")
        print("=" * 70)
        
        if errors:
            print(f"\n❌ 发现 {len(errors)} 个错误:")
            for _, msg in errors:
                print(f"   • {msg}")
        
        if warnings:
            print(f"\n⚠ 发现 {len(warnings)} 个警告:")
            for _, msg in warnings:
                print(f"   • {msg}")
        
        if not errors and not warnings:
            print("\n✅ 所有检查通过！项目已准备好部署到Linux服务器")
        elif not errors:
            print("\n✅ 基本检查通过，但有一些警告需要注意")
        else:
            print("\n❌ 请先修复错误，然后再部署")
        
        print("=" * 70)


def create_linux_deployment_guide():
    """创建Linux部署指南"""
    guide = """
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
\\q
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
cd ../frontend-client
npm install
npm run build
```

---

## 🚀 启动服务

### 方式一：使用Python启动脚本（推荐）

```bash
cd /path/to/deploy/stock_analysis_app

# 启动后端（在一个终端）
bash devops/start_backend.sh

# 启动前端（在另一个终端）
bash devops/start_frontend.sh

# 或一键启动（后台运行）
nohup bash devops/start_backend.sh > backend.log 2>&1 &
nohup bash devops/start_frontend.sh > frontend.log 2>&1 &
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
        root /path/to/stock_analysis_app/frontend-client/build;
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
"""
    return guide


def main():
    """主函数"""
    project_root = Path(__file__).resolve().parents[2]
    
    print()
    preparer = LinuxDeploymentPreparer(project_root)
    preparer.check_all()
    
    print("\n" + "=" * 70)
    print("📖 创建Linux部署指南...")
    print("=" * 70)
    
    guide_file = project_root / "deploy" / "LINUX_DEPLOY_GUIDE.md"
    guide_content = create_linux_deployment_guide()
    
    with open(guide_file, 'w', encoding='utf-8') as f:
        f.write(guide_content)
    
    print(f"✅ 已创建: {guide_file}")
    print()
    print("💡 下一步：")
    print("   1. 阅读 LINUX_DEPLOY_GUIDE.md")
    print("   2. 配置 backend/.env 文件")
    print("   3. 上传项目到Linux服务器")
    print("   4. 按照指南进行部署")
    print()


if __name__ == "__main__":
    main()
