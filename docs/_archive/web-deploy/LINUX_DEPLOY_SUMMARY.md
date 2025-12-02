# 🚀 Linux服务器部署总结

## 📦 已为您准备的部署文件

本项目已完全准备好部署到Linux服务器（不使用Docker，直接运行PostgreSQL）。

### 📁 新增文件清单

```
stock_analysis_app/
├── 📖 LINUX_DEPLOY_GUIDE.md         # 详细部署指南（必读）
├── ✅ DEPLOY_CHECKLIST.md           # 部署检查清单
├── 🧹 prepare_linux_deploy.py       # 部署准备检查脚本
├── deploy/                          # 部署配置目录
│   ├── setup_linux.sh              # 一键部署脚本
│   ├── stock-backend.service       # Systemd服务配置
│   ├── nginx-stock-analysis.conf   # Nginx配置
│   ├── init_database.sql           # 数据库初始化脚本
│   └── README.md                   # 部署文件说明
└── data/
    └── .gitkeep                    # Git保留空目录
```

---

## 🎯 部署方式对比

### 方式一：快速开发模式 ⚡

**适用场景**：测试、开发、个人使用

**特点**：
- ✅ 部署简单快速
- ✅ 方便调试
- ⚠️ 需要保持终端连接
- ⚠️ 不适合生产环境

**部署步骤**：
```bash
# 1. 运行自动部署脚本
chmod +x deploy/setup_linux.sh
./deploy/setup_linux.sh

# 2. 启动服务（使用screen或tmux）
screen -S backend
./start_backend_linux.sh
# Ctrl+A+D 分离会话

screen -S frontend
./start_frontend_linux.sh
# Ctrl+A+D 分离会话
```

**访问**：
- 前端：http://server-ip:3000
- API：http://server-ip:8000/docs

---

### 方式二：生产模式 🏭

**适用场景**：正式生产环境、对外服务

**特点**：
- ✅ 服务稳定可靠
- ✅ 开机自启动
- ✅ 统一80端口访问
- ✅ 更好的性能和安全
- ⚠️ 配置稍复杂

**部署步骤**：
```bash
# 1. 初始化数据库
sudo -u postgres psql < deploy/init_database.sql

# 2. 运行部署脚本
./deploy/setup_linux.sh

# 3. 配置Systemd（后端自启动）
sudo cp deploy/stock-backend.service /etc/systemd/system/
# 编辑文件，修改路径和用户
sudo nano /etc/systemd/system/stock-backend.service
sudo systemctl daemon-reload
sudo systemctl start stock-backend
sudo systemctl enable stock-backend

# 4. 配置Nginx（前端+反向代理）
sudo cp deploy/nginx-stock-analysis.conf /etc/nginx/sites-available/stock-analysis
# 编辑文件，修改域名和路径
sudo nano /etc/nginx/sites-available/stock-analysis
sudo ln -s /etc/nginx/sites-available/stock-analysis /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl restart nginx
```

**访问**：
- 统一入口：http://server-ip/

---

## 🔑 关键配置文件

### 1. `backend/.env` - 数据库连接配置

```env
DB_HOST=localhost
DB_PORT=5432
DB_NAME=stock_analysis
DB_USER=stock_user
DB_PASSWORD=your_strong_password  # ⚠️ 必须修改
```

### 2. `deploy/stock-backend.service` - 服务配置

需要修改的地方：
```ini
User=your_user              # 改为你的用户名
WorkingDirectory=/path/to/stock_analysis_app/backend  # 改为实际路径
Environment="PATH=/path/to/stock_analysis_app/backend/venv/bin"  # 改为实际路径
ExecStart=/path/to/stock_analysis_app/backend/venv/bin/python ...  # 改为实际路径
```

### 3. `deploy/nginx-stock-analysis.conf` - Nginx配置

需要修改的地方：
```nginx
server_name your-domain.com;  # 改为你的域名或IP
root /path/to/stock_analysis_app/frontend/build;  # 改为实际路径
```

---

## 📊 资源需求

### 最低配置
- CPU: 2核
- 内存: 2GB
- 磁盘: 10GB
- 带宽: 1Mbps

### 推荐配置
- CPU: 4核
- 内存: 4GB
- 磁盘: 20GB
- 带宽: 10Mbps

### 实际使用（单机部署）
```
PostgreSQL:     ~300MB
Backend (Python): ~200MB
Frontend (Nginx): ~50MB
系统开销:        ~500MB
------------------------
总计:           ~1GB
```

💡 **节省内存提示**：
- 不使用Docker可节省约500MB内存
- 调整PostgreSQL `shared_buffers` 可进一步优化
- 使用Nginx而非npm serve可节省约100MB

---

## 🔒 安全建议

### 必须做的
1. ✅ 修改所有默认密码
2. ✅ 配置防火墙（ufw/firewalld）
3. ✅ 定期备份数据库
4. ✅ 更新系统安全补丁

### 推荐做的
1. 🔐 配置HTTPS（Let's Encrypt免费证书）
2. 🔐 使用SSH密钥登录，禁用密码
3. 🔐 配置fail2ban防暴力破解
4. 🔐 限制数据库只监听localhost

### 防火墙配置示例
```bash
# Ubuntu/Debian
sudo ufw allow 22/tcp      # SSH
sudo ufw allow 80/tcp      # HTTP
sudo ufw allow 443/tcp     # HTTPS
sudo ufw enable

# 开发模式额外端口
sudo ufw allow 3000/tcp    # Frontend dev
sudo ufw allow 8000/tcp    # Backend API
```

---

## 📝 部署流程图

```
┌─────────────────────────────────────────────────┐
│  1️⃣  准备服务器                                  │
│     • 安装系统依赖（Python, Node, PostgreSQL）  │
└───────────────────┬─────────────────────────────┘
                    ↓
┌─────────────────────────────────────────────────┐
│  2️⃣  配置数据库                                  │
│     • 创建数据库和用户                          │
│     • 配置连接权限                              │
└───────────────────┬─────────────────────────────┘
                    ↓
┌─────────────────────────────────────────────────┐
│  3️⃣  上传项目                                    │
│     • 使用scp或git上传代码                      │
│     • 上传Excel数据文件                         │
└───────────────────┬─────────────────────────────┘
                    ↓
┌─────────────────────────────────────────────────┐
│  4️⃣  配置后端                                    │
│     • 创建虚拟环境                              │
│     • 安装Python依赖                            │
│     • 配置.env文件                              │
│     • 导入Excel数据                             │
└───────────────────┬─────────────────────────────┘
                    ↓
┌─────────────────────────────────────────────────┐
│  5️⃣  配置前端                                    │
│     • 安装npm依赖                               │
│     • 构建生产版本                              │
└───────────────────┬─────────────────────────────┘
                    ↓
         ┌──────────┴──────────┐
         ↓                     ↓
┌──────────────────┐  ┌──────────────────┐
│  开发模式        │  │  生产模式        │
│  • 直接启动脚本  │  │  • Systemd服务   │
│  • 使用screen   │  │  • Nginx反向代理 │
└──────────────────┘  └──────────────────┘
```

---

## 🎓 常用运维操作

### 查看服务状态
```bash
sudo systemctl status stock-backend
sudo systemctl status nginx
sudo systemctl status postgresql
```

### 查看日志
```bash
# 后端日志
journalctl -u stock-backend -f

# Nginx日志
tail -f /var/log/nginx/stock-analysis-access.log
tail -f /var/log/nginx/stock-analysis-error.log

# PostgreSQL日志
sudo tail -f /var/log/postgresql/postgresql-*-main.log
```

### 重启服务
```bash
sudo systemctl restart stock-backend
sudo systemctl restart nginx
sudo systemctl restart postgresql
```

### 更新数据
```bash
cd /path/to/stock_analysis_app/backend
source venv/bin/activate
python scripts/import_data_robust.py
```

### 备份数据库
```bash
pg_dump -U stock_user -d stock_analysis > backup_$(date +%Y%m%d).sql
```

### 恢复数据库
```bash
psql -U stock_user -d stock_analysis < backup_20251107.sql
```

---

## 🆘 常见问题

### Q1: 后端无法连接数据库？
```bash
# 检查PostgreSQL是否运行
sudo systemctl status postgresql

# 测试连接
psql -h localhost -U stock_user -d stock_analysis

# 检查.env配置
cat backend/.env
```

### Q2: 前端显示空白页？
```bash
# 检查是否正确构建
ls -la frontend/build/

# 检查Nginx配置
sudo nginx -t

# 查看浏览器控制台错误
```

### Q3: API请求返回502？
```bash
# 检查后端是否运行
sudo systemctl status stock-backend
curl http://localhost:8000/api/dates

# 检查Nginx配置
sudo nginx -t
```

### Q4: 内存不足？
```bash
# 查看内存使用
free -h

# 创建Swap
sudo fallocate -l 2G /swapfile
sudo chmod 600 /swapfile
sudo mkswap /swapfile
sudo swapon /swapfile
```

---

## 📚 相关文档

1. **LINUX_DEPLOY_GUIDE.md** - 详细部署教程（必读）
2. **DEPLOY_CHECKLIST.md** - 部署检查清单（推荐打印）
3. **deploy/README.md** - 部署文件说明
4. **README.md** - 项目总体介绍

---

## 📞 获取帮助

如遇到部署问题：

1. 📖 查看详细文档：`LINUX_DEPLOY_GUIDE.md`
2. ✅ 检查清单：`DEPLOY_CHECKLIST.md`
3. 🔍 查看日志：`journalctl -u stock-backend -f`
4. 🐛 检查数据库：`psql -h localhost -U stock_user -d stock_analysis`

---

## ✅ 部署准备状态

当前项目状态：
- ✅ 项目结构完整
- ✅ Python启动脚本已创建（跨平台）
- ✅ 部署配置文件已创建
- ✅ 数据库初始化脚本已创建
- ✅ Systemd服务文件已创建
- ✅ Nginx配置文件已创建
- ✅ .gitignore已更新（保护敏感文件）
- ✅ 所有文档已创建

**✨ 项目已准备好部署到Linux服务器！**

---

## 🎯 下一步行动

1. **立即执行**：
   ```bash
   python prepare_linux_deploy.py  # 检查部署准备
   ```

2. **阅读文档**：
   - 仔细阅读 `LINUX_DEPLOY_GUIDE.md`
   - 打印 `DEPLOY_CHECKLIST.md` 逐项检查

3. **准备配置**：
   - 修改 `backend/.env`
   - 修改 `deploy/stock-backend.service`
   - 修改 `deploy/nginx-stock-analysis.conf`

4. **上传到服务器**：
   ```bash
   scp -r stock_analysis_app user@server:/path/to/deploy/
   ```

5. **开始部署**：
   ```bash
   chmod +x deploy/setup_linux.sh
   ./deploy/setup_linux.sh
   ```

---

**🎉 祝部署顺利！如有任何问题，请查阅相关文档。**
