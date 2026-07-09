# RES-004: 后端 uv 测试基线落地结果

**日期**: 2026-07-08
**状态**: [SOLVED]
**类型**: Infra / Backend / Testing / Baseline
**层级**: Backend
**关联**: PRB-003, SUG-003, DEC-002

---

## 执行摘要

为后续架构重构建立后端测试基线，已完成 `uv` + pytest 的最小落地。

本次只建立稳定单元测试集合，不把历史脚本式 API 测试、真实服务测试、真实市场数据测试纳入默认 pytest。

新增/调整内容：

1. `backend/pyproject.toml`
   - 定义后端项目依赖。
   - 定义 `analysis` optional extra，用于 Numpy、Pandas、OpenPyXL、Akshare、pywencai 等较重分析依赖。
   - 定义 `dev` dependency group，包含 `pytest`、`pytest-asyncio`。
   - 配置 pytest 默认只收集 `tests/unit`。

2. `backend/tests/README.md`
   - 说明默认测试命令和 legacy/integration 测试分流原则。

3. `backend/tests/unit/`
   - 新增 SQLite 内存库 fixture。
   - 新增认证会话生命周期测试。
   - 新增 session key 按设备隔离测试。

4. 包初始化副作用收敛
   - `backend/app/services/__init__.py` 改为懒加载，避免导入任意 `app.services.*` 时预加载分析依赖。
   - `backend/app/core/__init__.py` 改为懒加载，避免轻量核心导入触发启动预热和 Numpy 依赖。
   - `backend/app/routers/__init__.py` 改为懒加载，避免导入单个 router 时预加载全部分析 router。

5. `.env` 加载兼容
   - `backend/app/database.py.example` 支持通过 `PYTHON_DOTENV_DISABLED` 跳过真实 `.env`。
   - `.env` 读取支持 `utf-8-sig`、`utf-8`、`gbk` fallback，避免本地 GBK 编码文件导致 import 阶段失败。
   - 本地实际使用的 `backend/app/database.py` 被 `.gitignore` 忽略，已在当前工作区同步同类兼容逻辑，但不作为本轮可提交文件。

---

## 结果与证据

验证命令：

```powershell
cd backend
uv run pytest
```

验证结果：

```text
6 passed, 44 warnings in 1.06s
```

已覆盖测试点：

1. `session_key` 按 `user_id:device_id` 隔离。
2. 删除单设备 session key 不影响同用户其它设备。
3. 删除用户全部 session key 不影响其它用户。
4. 登录后数据库 `UserSession.expires_at` 使用 refresh 生命周期。
5. refresh 不再缩短数据库会话过期时间。
6. 已撤销会话会被 `get_current_user()` 拒绝。

补充 smoke 验证：

1. 使用 `uv run --extra analysis` 时，`from app.routers import analysis_router, ...` 可正常触发旧聚合路由懒加载。
2. 使用 `uv run --extra analysis` 时，`from app.services import DBDataLoader`、`from app.core import get_data_manager` 可正常触发旧聚合入口懒加载。

---

## 是否满足验收

- [x] 可以使用 `uv run pytest` 一键跑后端默认单元测试。
- [x] 默认 pytest 不收集历史脚本式真实服务测试。
- [x] 认证会话修复已有基础回归测试。
- [x] 测试环境不依赖真实 `.env` 编码和真实 PostgreSQL 连接。
- [x] 轻量单测不再被 Numpy/Pandas 分析依赖阻塞。
- [x] 旧聚合路由、服务和 core 入口的懒加载 smoke 验证通过。
- [ ] 尚未建立 integration marker/profile。
- [ ] 尚未建立 domain import boundary 自动检查。

**结论**：满足架构迁移前的最小测试基线要求。后续 Level 0 应补 integration 分层和 import boundary 检查。

---

## 遗留风险 / 后续行动

1. 当前 SQLite 单元测试不能覆盖 PostgreSQL 方言、索引和约束差异。
2. 直接调用 router 函数不能覆盖 FastAPI middleware 和依赖注入全链路。
3. 历史 `backend/tests/*.py` 中仍有真实服务、真实数据和脚本式测试，需要后续收编到 `tests/integration` 或 `tests/legacy`。
4. `datetime.utcnow()` 在 Python 3.12 下产生 deprecation warnings，后续可统一改为 timezone-aware UTC。
5. `backend/app/database.py` 被 `.gitignore` 忽略，fresh clone 需要手动从 `database.py.example` 复制；Level 0 应决定是否改为版本化配置模块加 `.env` 私密配置。
