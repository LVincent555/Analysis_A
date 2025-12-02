# ✅ Linux部署检查清单

用于确保所有部署步骤都已正确完成。

## 🔧 部署前准备

### 服务器环境
- [ ] Linux服务器已准备（Ubuntu 20.04+, CentOS 8+）
- [ ] 服务器内存 >= 2GB
- [ ] 磁盘空间 >= 10GB
- [ ] 已获取服务器SSH访问权限
- [ ] 已配置防火墙允许所需端口（80, 8000, 5432等）

### 本地准备
- [ ] 项目代码已整理
- [ ] 已运行 `python prepare_linux_deploy.py` 检查
- [ ] Excel数据文件已准备好
- [ ] 已阅读 `LINUX_DEPLOY_GUIDE.md`

---

## 📦 服务器端安装

### 1. 系统依赖安装
- [ ] Python 3.8+ 已安装
- [ ] Node.js 16+ 已安装
- [ ] PostgreSQL 12+ 已安装
- [ ] Nginx 已安装（生产环境）
- [ ] Git 已安装（如果使用git部署）

**验证命令：**
```bash
python3 --version
node --version
psql --version
nginx -v
```

### 2. 数据库配置
- [ ] PostgreSQL 服务已启动
- [ ] 数据库 `stock_analysis` 已创建
- [ ] 用户 `stock_user` 已创建
- [ ] 已授予用户适当权限
- [ ] pg_hba.conf 已配置允许本地连接
- [ ] PostgreSQL 服务已重启

**验证命令：**
```bash
sudo systemctl status postgresql
psql -h localhost -U stock_user -d stock_analysis -c "SELECT version();"
```

---

## 🚀 项目部署

### 3. 上传项目文件
- [ ] 项目文件已上传到服务器
- [ ] 目录权限设置正确
- [ ] Excel数据文件已上传到 `data/` 目录

**上传方式：**
```bash
# 方式1: SCP
scp -r stock_analysis_app user@server:/path/to/deploy/

# 方式2: Git
git clone <repo-url> /path/to/deploy/stock_analysis_app
```

### 4. 后端配置
- [ ] 进入 `backend/` 目录
- [ ] 已从 `.env.example` 创建 `.env` 文件
- [ ] `.env` 中数据库连接信息已配置
- [ ] Python虚拟环境已创建 (`python3 -m venv venv`)
- [ ] Python依赖已安装 (`pip install -r requirements.txt`)
- [ ] 数据库表已创建（SQLAlchemy自动创建）
- [ ] Excel数据已导入 (`python scripts/import_data_robust.py`)

**验证命令：**
```bash
cd backend
source venv/bin/activate
python -c "from app.database import test_connection; test_connection()"
```

### 5. 前端配置
- [ ] 进入 `frontend/` 目录
- [ ] npm依赖已安装 (`npm install`)
- [ ] 前端已构建 (`npm run build`)
- [ ] `build/` 目录已生成

**验证命令：**
```bash
cd frontend
ls -la build/
```

---

## 🔧 服务配置

### 6. 后端服务（Systemd）
- [ ] `deploy/stock-backend.service` 文件路径已修改
- [ ] 服务文件中的用户名已修改
- [ ] 服务文件已复制到 `/etc/systemd/system/`
- [ ] systemd 已重新加载配置
- [ ] 服务已启动
- [ ] 服务已设置开机自启
- [ ] 服务状态正常运行

**验证命令：**
```bash
sudo systemctl status stock-backend
curl http://localhost:8000/api/dates
```

### 7. Nginx配置（生产环境）
- [ ] `deploy/nginx-stock-analysis.conf` 域名/IP已修改
- [ ] 配置文件中的路径已修改
- [ ] 配置文件已复制到 `/etc/nginx/sites-available/`
- [ ] 已创建软链接到 `/etc/nginx/sites-enabled/`
- [ ] Nginx配置测试通过 (`nginx -t`)
- [ ] Nginx已重启
- [ ] 可以通过80端口访问

**验证命令：**
```bash
sudo nginx -t
curl http://localhost/
```

---

## ✅ 功能测试

### 8. 基本功能测试
- [ ] 前端页面可以访问
- [ ] API接口返回正常
- [ ] 可以查看最新热点
- [ ] 股票查询功能正常
- [ ] 排名跳变功能正常
- [ ] 行业趋势分析正常
- [ ] 稳步走强功能正常

**测试URL：**
- 前端: `http://your-server-ip/`
- API文档: `http://your-server-ip/api/docs`
- 健康检查: `http://your-server-ip/api/dates`

### 9. 性能测试
- [ ] 页面加载速度正常（< 3秒）
- [ ] API响应时间正常（< 1秒）
- [ ] 内存使用在合理范围内
- [ ] CPU使用正常

**监控命令：**
```bash
htop
free -h
systemctl status stock-backend
```

---

## 🔒 安全加固

### 10. 安全检查
- [ ] 数据库密码已修改为强密码
- [ ] `.env` 文件权限设置为 600
- [ ] PostgreSQL 只监听本地连接
- [ ] 防火墙已配置（只开放必要端口）
- [ ] SSH密钥登录已配置（禁用密码登录）
- [ ] 已配置HTTPS（生产环境强烈推荐）

**安全命令：**
```bash
chmod 600 backend/.env
sudo ufw status
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
```

---

## 📝 日常维护

### 11. 备份配置
- [ ] 已设置数据库定期备份
- [ ] 已测试备份恢复流程
- [ ] 已设置日志轮转

**备份脚本示例：**
```bash
# 数据库备份
pg_dump -U stock_user -d stock_analysis > backup_$(date +%Y%m%d).sql

# 配置文件备份
tar -czf config_backup_$(date +%Y%m%d).tar.gz backend/.env deploy/
```

### 12. 监控配置
- [ ] 已配置服务状态监控
- [ ] 已配置日志监控
- [ ] 已配置磁盘空间监控
- [ ] 已设置告警通知

---

## 🎉 部署完成确认

### 最终验证
- [ ] 所有服务正常运行
- [ ] 所有功能测试通过
- [ ] 性能符合预期
- [ ] 安全配置就绪
- [ ] 备份机制已建立
- [ ] 监控已配置

### 文档记录
- [ ] 部署过程已记录
- [ ] 遇到的问题和解决方案已记录
- [ ] 服务器信息已记录（IP、账号、密码等）
- [ ] 联系信息已记录

---

## 📞 常用运维命令

```bash
# 查看服务状态
sudo systemctl status stock-backend

# 重启服务
sudo systemctl restart stock-backend
sudo systemctl restart nginx

# 查看日志
journalctl -u stock-backend -f
tail -f /var/log/nginx/stock-analysis-error.log

# 更新代码（如果使用git）
cd /path/to/stock_analysis_app
git pull
sudo systemctl restart stock-backend

# 更新数据
cd /path/to/stock_analysis_app/backend
source venv/bin/activate
python scripts/import_data_robust.py
```

---

**✅ 检查完成日期：** ___________

**✅ 部署人员：** ___________

**✅ 服务器信息：** ___________

**✅ 备注：** ___________
