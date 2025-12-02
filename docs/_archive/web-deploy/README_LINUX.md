# 🐧 Linux服务器部署快速指南

> **不使用Docker，直接在Linux服务器上运行（PostgreSQL + Python + Node.js）**

---

## 🚀 30秒快速开始

```bash
# 1. 上传项目到服务器
scp -r stock_analysis_app user@server:/path/to/deploy/

# 2. SSH登录服务器
ssh user@server

# 3. 进入项目目录
cd /path/to/deploy/stock_analysis_app

# 4. 运行一键部署脚本
chmod +x deploy/setup_linux.sh
./deploy/setup_linux.sh

# 5. 完成！访问应用
# 开发模式：http://server-ip:3000
# 生产模式：http://server-ip （需配置Nginx）
```

---

## 📋 系统要求

- **系统**: Ubuntu 20.04+ / CentOS 8+
- **CPU**: 2核+
- **内存**: 2GB+
- **软件**: Python 3.8+, Node.js 16+, PostgreSQL 12+

---

## 📁 部署文档

| 文档 | 说明 | 优先级 |
|------|------|--------|
| **LINUX_DEPLOY_SUMMARY.md** | 部署总览（推荐先读） | ⭐⭐⭐ |
| **LINUX_DEPLOY_GUIDE.md** | 详细部署教程 | ⭐⭐⭐ |
| **DEPLOY_CHECKLIST.md** | 部署检查清单 | ⭐⭐ |
| **deploy/README.md** | 部署文件说明 | ⭐⭐ |

---

## 🔧 核心配置文件

### 必须修改
1. `backend/.env` - 数据库连接配置
2. `deploy/stock-backend.service` - Systemd服务（生产环境）
3. `deploy/nginx-stock-analysis.conf` - Nginx配置（生产环境）

---

## 💡 两种部署模式

### 🎯 快速开发模式（推荐先用这个测试）
```bash
./deploy/setup_linux.sh  # 自动配置

# 启动后端
./start_backend_linux.sh &

# 启动前端  
./start_frontend_linux.sh
```

### 🏭 生产环境模式
```bash
./deploy/setup_linux.sh  # 自动配置

# 配置Systemd + Nginx
sudo cp deploy/stock-backend.service /etc/systemd/system/
sudo systemctl start stock-backend
sudo systemctl enable stock-backend

sudo cp deploy/nginx-stock-analysis.conf /etc/nginx/sites-available/stock-analysis
sudo ln -s /etc/nginx/sites-available/stock-analysis /etc/nginx/sites-enabled/
sudo systemctl restart nginx
```

---

## 📊 内存优势

相比Docker部署，直接部署可节省：
- ❌ Docker Engine: ~500MB
- ❌ 容器开销: ~300MB
- ✅ **总节省**: ~800MB

**实际使用**（单机部署）：
- PostgreSQL: ~300MB
- Backend: ~200MB  
- Frontend (Nginx): ~50MB
- **总计**: ~550MB（相比Docker的1.3GB）

---

## ✅ 快速检查

运行准备检查脚本：
```bash
python prepare_linux_deploy.py
```

---

## 🆘 遇到问题？

1. 查看日志：`journalctl -u stock-backend -f`
2. 测试数据库：`psql -h localhost -U stock_user -d stock_analysis`
3. 检查服务：`sudo systemctl status stock-backend`
4. 查看详细文档：`LINUX_DEPLOY_GUIDE.md`

---

## 📞 常用命令

```bash
# 启动/停止服务
sudo systemctl start stock-backend
sudo systemctl stop stock-backend
sudo systemctl restart stock-backend

# 查看状态
sudo systemctl status stock-backend
sudo systemctl status nginx

# 查看日志
journalctl -u stock-backend -f
tail -f /var/log/nginx/stock-analysis-error.log

# 更新数据
cd backend && source venv/bin/activate
python scripts/import_data_robust.py

# 备份数据库
pg_dump -U stock_user -d stock_analysis > backup_$(date +%Y%m%d).sql
```

---

**📖 详细教程请阅读：LINUX_DEPLOY_SUMMARY.md 和 LINUX_DEPLOY_GUIDE.md**

**🎉 祝部署顺利！**
