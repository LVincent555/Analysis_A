# 🚀 从这里开始

## 📖 文档导航

根据你的需求选择相应的文档：

### 🎯 我要部署到Linux服务器
➡️ **[部署使用手册.md](部署使用手册.md)** - 完整的部署教程

**快速命令：**
```bash
# 上传到服务器后执行
python3 deploy_smart.py dev    # 开发模式（推荐）
python3 deploy_smart.py prod   # 生产模式
```

---

### 🧹 我要清理Git中的大文件
➡️ **运行清理脚本：**
```bash
python3 clean_git_history.py
```

这会从Git中删除：
- `frontend/node_modules/`
- `backend/venv/`
- `__pycache__/` 等

---

### 💻 我要在本地开发（Windows）
➡️ **[快速开始.md](快速开始.md)** - Windows本地开发指南

**快速命令：**
```bash
# Windows
python start_backend.py   # 启动后端
python start_frontend.py  # 启动前端
```

---

### 🐳 我要使用Docker部署
➡️ **[README_DEPLOY.md](README_DEPLOY.md)** - Docker部署文档

---

### 📚 我要了解项目详情
- **[README.md](README.md)** - 项目总览
- **[PROJECT_OVERVIEW.md](PROJECT_OVERVIEW.md)** - 详细架构说明
- **[VERSION.md](VERSION.md)** - 版本历史

---

## ⚡ 超快速开始（Linux服务器）

### 你的服务器配置：
- **系统**：Ubuntu 24.04
- **IP**：60.205.251.109
- **数据库**：db_20251106_analysis_a（已配置）
- **数据**：已导入（data_import_state.json存在）

### 3步部署：

```bash
# 1. 上传项目
scp -r stock_analysis_app root@60.205.251.109:/root/

# 2. SSH登录
ssh root@60.205.251.109
cd /root/stock_analysis_app

# 3. 一键部署
python3 deploy_smart.py dev
```

**完成！** 访问 http://60.205.251.109:3000

---

## 🆘 遇到问题？

1. **部署问题** → 查看 [部署使用手册.md](部署使用手册.md) 的"故障排查"部分
2. **数据库问题** → 手册中有详细的数据库诊断命令
3. **性能问题** → 手册中有资源监控方法

---

## 📋 项目文件说明

### 🔥 核心脚本
- `deploy_smart.py` - **智能部署脚本**（推荐使用）
- `clean_git_history.py` - Git历史清理脚本
- `prepare_linux_deploy.py` - 部署准备检查

### 📖 文档
- `部署使用手册.md` - **完整部署指南**（推荐阅读）
- `START_HERE.md` - 本文档
- `快速开始.md` - Windows本地开发
- `README_LINUX.md` - Linux快速参考

### ⚙️ 配置目录
- `deploy/` - 部署配置文件（Systemd、Nginx等）
- `backend/.env` - 后端数据库配置
- `.gitignore` - Git忽略规则

---

**🎉 准备好了吗？打开 [部署使用手册.md](部署使用手册.md) 开始吧！**
