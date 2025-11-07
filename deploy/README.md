# 📦 部署目录

本目录包含所有部署相关的文件和脚本。

## 📁 目录结构

```
deploy/
├── scripts/              # 部署脚本
│   ├── deploy_smart.py  # 智能部署主脚本
│   ├── service_manager.py # 服务管理器
│   ├── setup_linux.sh   # Linux环境配置
│   └── ...
├── configs/             # 配置模板
│   ├── stock-backend.service  # Systemd服务配置
│   ├── nginx-stock-analysis.conf # Nginx配置
│   └── init_database.sql # 数据库初始化
└── README.md           # 本文件

## 🚀 快速开始

### 开发模式部署
```bash
python3 deploy/scripts/deploy_smart.py dev
```

### 服务管理
```bash
python3 deploy/scripts/service_manager.py start all
python3 deploy/scripts/service_manager.py status
```

## 📖 详细文档

查看 `docs/` 目录获取完整文档：
- `docs/部署使用手册.md` - 完整部署教程
- `docs/服务管理手册.md` - 服务管理说明
- `docs/服务器更新指南.md` - 更新流程

## 💡 提示

所有部署脚本都在 `scripts/` 子目录中，配置模板在 `configs/` 子目录中。
