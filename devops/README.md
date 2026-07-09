# DevOps 脚本目录

`devops` 用来集中存放原本散落在项目根目录和旧 `scripts/` 目录里的运维脚本。

根目录 `../一键部署.sh` 仍然保留，继续作为服务器部署入口；服务启停等生命周期命令转交给本目录下脚本。

## 常用命令

在仓库根目录执行：

```bash
bash devops/start_all.sh dev
bash devops/start_all.sh
bash devops/stop.sh
bash devops/restart.sh
bash devops/status.sh
bash devops/logs.sh backend
bash devops/update_daily_data.sh
```

Windows 辅助脚本：

```bat
devops\update_daily_data.bat
devops\switch_to_http.bat
devops\switch_to_ghost.bat
```

## 目录说明

- `start*.sh`、`stop.sh`、`restart.sh`、`status.sh`、`logs.sh`：服务生命周期脚本。
- `deploy*.sh`、`deploy.bat`、`service.sh`：部署与服务管理封装。
- `update_daily_data.*`：每日数据更新入口。
- `certs/`：证书生成脚本，生成结果写入 `backend/certs`。
- `optimization/`：历史优化与诊断脚本。
- `tests/`：历史临时 API / 数据测试脚本。

`backend/scripts` 与 `deploy/scripts` 保留在原位，因为它们是后端或部署模块内部实现脚本，不属于散落运维入口。
