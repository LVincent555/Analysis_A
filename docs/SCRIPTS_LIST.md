# 🔧 项目脚本清单

## 📍 启动脚本（根目录）

| 脚本 | 说明 | 用途 |
|------|------|------|
| `start_backend.py` | 启动后端 | 开发/测试 |
| `start_frontend.py` | 启动前端 | 开发/测试 |
| `start_all.py` | 一键启动所有 | 开发/测试 |

## 🔧 工具脚本（deploy/scripts/）

| 脚本 | 说明 | 用途 |
|------|------|------|
| `deploy_smart.py` | 智能部署 | 部署 |
| `service_manager.py` | 服务管理 | 运维 |
| `git_commit_push.py` | Git提交 | 开发 |
| `clean_git_history.py` | Git历史清理 | 维护 |
| `prepare_linux_deploy.py` | 部署检查 | 部署 |
| `setup_linux.sh` | Linux环境配置 | 部署 |
| `cleanup_and_organize.py` | 项目清理 | 维护 |
| `cleanup_old_files.py` | 清理旧文件 | 维护 |
| `cleanup_redundant_files.py` | 清理冗余文件 | 维护 |
| `reorganize_project.py` | 项目重组 | 维护 |

## ⚡ 快捷命令（根目录 .sh）

| 命令 | 说明 | 等同于 |
|------|------|--------|
| `./service.sh` | 服务管理 | `python3 deploy/scripts/service_manager.py` |
| `./deploy.sh` | 智能部署 | `python3 deploy/scripts/deploy_smart.py` |
| `./start.sh` | 启动服务 | `service_manager.py start all` |
| `./stop.sh` | 停止服务 | `service_manager.py stop all` |
| `./restart.sh` | 重启服务 | `service_manager.py restart all` |
| `./status.sh` | 查看状态 | `service_manager.py status` |
| `./logs.sh` | 查看日志 | `service_manager.py logs` |

## 🎯 使用建议

### 开发阶段
- 使用 `start_*.py` 启动服务
- 使用 `test_backend.py` 测试后端

### 部署阶段
- 使用 `deploy/scripts/deploy_smart.py` 智能部署
- 使用 `deploy/scripts/service_manager.py` 管理服务

### 维护阶段
- 使用 `.sh` 快捷命令日常管理
- 使用工具脚本进行维护清理

---

**💡 提示**: 所有 `.sh` 文件都是快捷命令，实际调用 `deploy/scripts/` 中的Python脚本。
