# 📁 部署文件说明

本目录包含Linux服务器部署所需的配置文件和脚本。

## 📄 文件列表

### 1. **setup_linux.sh** - 一键部署脚本
自动化部署脚本，会检查依赖、安装包、配置环境。

**使用方法：**
```bash
chmod +x setup_linux.sh
./setup_linux.sh
```

### 2. **stock-backend.service** - Systemd服务文件
用于将后端配置为系统服务，开机自启动。

**安装方法：**
```bash
# 1. 编辑文件，修改路径和用户
nano stock-backend.service

# 2. 复制到systemd目录
sudo cp stock-backend.service /etc/systemd/system/

# 3. 重新加载并启动
sudo systemctl daemon-reload
sudo systemctl start stock-backend
sudo systemctl enable stock-backend

# 4. 查看状态
sudo systemctl status stock-backend
```

### 3. **nginx-stock-analysis.conf** - Nginx配置文件
配置Nginx作为前端静态文件服务器和API反向代理。

**安装方法：**
```bash
# 1. 编辑文件，修改路径和域名
nano nginx-stock-analysis.conf

# 2. 复制到nginx配置目录
sudo cp nginx-stock-analysis.conf /etc/nginx/sites-available/stock-analysis

# 3. 创建软链接
sudo ln -s /etc/nginx/sites-available/stock-analysis /etc/nginx/sites-enabled/

# 4. 测试配置
sudo nginx -t

# 5. 重启nginx
sudo systemctl restart nginx
```

### 4. **init_database.sql** - 数据库初始化脚本
创建数据库、用户和授权。

**使用方法：**
```bash
# 1. 编辑文件，修改密码
nano init_database.sql

# 2. 执行脚本
sudo -u postgres psql < init_database.sql
```

## 🚀 快速部署流程

### 方案一：开发模式（快速测试）

```bash
# 1. 运行自动部署脚本
./deploy/setup_linux.sh

# 2. 启动服务
./start_backend_linux.sh &    # 后台运行后端
./start_frontend_linux.sh      # 前台运行前端（或用screen/tmux）
```

### 方案二：生产模式（推荐）

```bash
# 1. 初始化数据库
sudo -u postgres psql < deploy/init_database.sql

# 2. 运行部署脚本
./deploy/setup_linux.sh

# 3. 构建前端
cd frontend && npm run build

# 4. 配置systemd服务
sudo cp deploy/stock-backend.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl start stock-backend
sudo systemctl enable stock-backend

# 5. 配置nginx
sudo cp deploy/nginx-stock-analysis.conf /etc/nginx/sites-available/stock-analysis
sudo ln -s /etc/nginx/sites-available/stock-analysis /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl restart nginx
```

## 📝 配置检查清单

在部署前，请确认以下配置：

- [ ] `stock-backend.service` 中的路径和用户名
- [ ] `nginx-stock-analysis.conf` 中的域名和路径
- [ ] `init_database.sql` 中的密码
- [ ] `backend/.env` 中的数据库连接信息

## 🔍 常用命令

### 查看服务状态
```bash
sudo systemctl status stock-backend
```

### 查看服务日志
```bash
journalctl -u stock-backend -f
```

### 重启服务
```bash
sudo systemctl restart stock-backend
sudo systemctl restart nginx
```

### 查看nginx日志
```bash
tail -f /var/log/nginx/stock-analysis-access.log
tail -f /var/log/nginx/stock-analysis-error.log
```

## ⚠️ 注意事项

1. **安全性**：
   - 修改所有默认密码
   - 配置防火墙规则
   - 使用HTTPS（生产环境）

2. **性能**：
   - 根据服务器内存调整workers数量
   - 配置适当的数据库连接池大小

3. **备份**：
   - 定期备份数据库
   - 备份配置文件

## 📞 问题排查

如果遇到问题，请查看：
1. 服务日志：`journalctl -u stock-backend -f`
2. Nginx日志：`/var/log/nginx/stock-analysis-error.log`
3. 数据库连接：`psql -h localhost -U stock_user -d stock_analysis`

---

📖 更多详细信息请参考 `../LINUX_DEPLOY_GUIDE.md`
