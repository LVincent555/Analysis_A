# 📁 项目结构说明

## 目录组织

```
stock_analysis_app/
├── backend/              # 后端FastAPI应用
│   ├── app/             # 应用代码
│   ├── scripts/         # 工具脚本
│   ├── venv/            # Python虚拟环境
│   └── requirements.txt # Python依赖
│
├── frontend/            # 前端React应用
│   ├── src/            # 源代码
│   ├── public/         # 静态资源
│   └── package.json    # Node.js依赖
│
├── data/               # 数据文件
│   └── *.xlsx         # Excel数据文件
│
├── deploy/             # 部署相关
│   ├── scripts/       # 部署脚本
│   │   ├── deploy_smart.py      # 智能部署
│   │   ├── service_manager.py   # 服务管理
│   │   ├── git_commit_push.py   # Git提交
│   │   └── ...
│   ├── configs/       # 配置模板
│   │   ├── *.service          # Systemd配置
│   │   ├── *.conf             # Nginx配置
│   │   └── *.sql              # 数据库SQL
│   └── README.md
│
├── docs/              # 项目文档
│   ├── START_HERE.md         # 入门指南
│   ├── 部署使用手册.md       # 部署教程
│   ├── 服务管理手册.md       # 服务管理
│   └── ...
│
├── logs/              # 运行日志（自动生成）
├── .pids/             # 进程PID（自动生成）
│
├── start_*.py         # 快速启动脚本
├── *.sh              # Shell快捷命令
├── reorganize_project.py  # 项目重组脚本
└── README.md         # 项目主文档
```

## 快捷命令（Shell脚本）

| 脚本 | 说明 | 示例 |
|------|------|------|
| `./service.sh` | 服务管理 | `./service.sh start all` |
| `./deploy.sh` | 智能部署 | `./deploy.sh dev` |
| `./start.sh` | 启动服务 | `./start.sh` |
| `./stop.sh` | 停止服务 | `./stop.sh` |
| `./restart.sh` | 重启服务 | `./restart.sh` |
| `./status.sh` | 查看状态 | `./status.sh` |
| `./logs.sh` | 查看日志 | `./logs.sh backend` |

## Python快速启动

| 脚本 | 说明 |
|------|------|
| `start_backend.py` | 启动后端 |
| `start_frontend.py` | 启动前端 |
| `start_all.py` | 一键启动所有 |

## 部署相关

### 开发环境
```bash
python3 deploy/scripts/deploy_smart.py dev
python3 deploy/scripts/service_manager.py start all
```

### 生产环境
```bash
python3 deploy/scripts/deploy_smart.py prod
# 然后按提示配置Systemd和Nginx
```

## 文档导航

1. **新手入门**: `docs/START_HERE.md`
2. **部署系统**: `docs/部署使用手册.md`
3. **管理服务**: `docs/服务管理手册.md`
4. **更新代码**: `docs/服务器更新指南.md`
5. **项目总览**: `docs/PROJECT_OVERVIEW.md`

## 注意事项

### 已删除的内容
- ✅ 根目录 `sql/` 文件夹（已移至 `deploy/configs/`）
- ✅ `backend/sql/` 文件夹（已移至 `deploy/configs/`）
- ✅ 项目外的旧版本文件（已有Git管理，无需保留）
- ✅ 多余的Shell脚本（已整合为快捷命令）

### 配置文件位置
- SQL初始化脚本: `deploy/configs/*.sql`
- Systemd配置: `deploy/configs/*.service`
- Nginx配置: `deploy/configs/*.conf`
- 环境变量模板: `backend/.env.example`

### 日志文件
- 服务日志: `logs/backend.log`, `logs/frontend.log`
- 管理器日志: `logs/manager_YYYYMMDD.log`

### Git忽略
- `logs/` - 运行日志
- `.pids/` - 进程PID
- `data/*.xlsx` - 数据文件
- `backend/.env` - 数据库密码
- `node_modules/`, `venv/` - 依赖包

---

**📖 更多信息请查看各目录的README文件**
