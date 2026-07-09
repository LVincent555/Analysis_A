# RES-035: DevOps 脚本归拢与部署入口审核结果

**日期**: 2026-07-09
**状态**: [SOLVED]
**类型**: Infra / DevOps / Documentation
**关联**: DEC-001, RES-034

---

## 执行摘要

本次按“根目录保持干净、服务器部署入口保留”的原则，对 `stock_analysis_app` 的脚本进行归拢：

1. 根目录 `一键部署.sh` 保留原位，继续作为服务器部署入口。
2. 根目录散落的启动、停止、重启、状态、日志、部署、数据更新脚本迁移到 `devops/`。
3. 旧 `scripts/` 下的证书、优化、临时测试脚本迁移到 `devops/`。
4. `backend/scripts` 与 `deploy/scripts` 保持原位，因为它们属于后端或部署模块内部实现。
5. 迁移后修正脚本定位项目根、前端目录、启动入口、Nginx 模板和日更入口的路径。

---

## 主要改动

- 新增 `.gitattributes`，固定 `.sh` 使用 LF、`.bat` 使用 CRLF，降低 Linux 部署脚本换行符风险。
- 新增 `devops/README.md` 作为脚本索引。
- `一键部署.sh` 改为调用 `devops/stop.sh`、`devops/start_all.sh`、`backend/scripts/init_users.py`。
- `devops/start_all.sh`、`devops/start_backend.sh`、`devops/start_frontend.sh` 改为从 `devops/..` 定位项目根。
- 前端相关脚本从旧 `frontend` 切换到当前主用 `frontend-client`。
- `devops/update_daily_data.py` 改为从项目根定位 `logs/`、`backend/`、`backend/scripts/`。
- `devops/certs/generate_certs.*` 的输出目录改为 `backend/certs`。
- `deploy/scripts/service_manager.py`、`deploy/scripts/deploy_smart.py`、`deploy/scripts/prepare_linux_deploy.py` 改为从脚本位置向上两级定位项目根。
- `deploy/scripts/setup_linux.sh` 重建为干净的 Linux 准备脚本，不再生成根目录启动脚本，统一提示使用 `devops/*`。
- `deploy_smart.py` 不再硬编码历史数据库密码，并保留已有 `.env` 中的 `DB_PASSWORD`。
- `deploy/scripts/git_commit_push.py` 的旧 `frontend` 忽略路径更新为 `frontend-client`。

---

## 迁移范围

已迁移到 `devops/`：

- `deploy.*`
- `deploy_server.sh`
- `start*.sh` / `start*.py`
- `stop.sh` / `restart.sh` / `status.sh` / `logs.sh` / `service.sh`
- `update_daily_data.*`
- `scripts/certs`
- `scripts/optimization`
- `scripts/tests`
- `scripts/switch_to_http.bat`
- `scripts/switch_to_ghost.bat`

保留在原位置：

- `一键部署.sh`
- `backend/scripts`
- `deploy/scripts`

---

## 验证结果

- 通过：`python -m py_compile deploy/scripts/prepare_linux_deploy.py deploy/scripts/deploy_smart.py deploy/scripts/service_manager.py deploy/scripts/git_commit_push.py devops/update_daily_data.py devops/start_backend.py devops/start_frontend.py devops/start_all.py devops/optimization/database_服务器优化版.py`
- 通过：`git diff --check`
- 未完成：`bash -n` shell 语法检查。本机没有 `bash` / `sh` / `shellcheck`，WSL 命令入口存在但未安装 Linux 发行版。

---

## 遗留风险

1. `devops/tests` 与 `devops/optimization` 多为历史临时脚本，本次只做路径归拢与明显硬编码收敛，未逐个执行验证。
2. 若服务器上仍有 crontab 或手工习惯调用根目录 `update_daily_data.sh`、`start_all.sh`，需要切换为 `devops/update_daily_data.sh`、`devops/start_all.sh`。
3. `docs/_archive` 等归档文档中仍可能提到旧根脚本路径或旧 `frontend` 目录，本次未做历史文档大扫除。
