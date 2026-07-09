# RES-024: BoardHeat 与同步导入迁移结果

**日期**: 2026-07-08
**状态**: [SOLVED]
**类型**: Infra / Backend / Architecture / Migration / Testing
**层级**: Backend
**关联**: DEC-002, SUG-003, RES-023

---

## 结果摘要

已完成 DEC-002 Level 4：BoardHeat、外部板块同步、客户端离线同步、数据导入/删除等接口迁入对应上下文。

本次迁移仍保留既有脚本和 SQL 行为，不重写外部同步、热度计算和 Excel 导入算法。主要变化是把 router 中的任务状态、子进程执行、raw SQL 查询、文件导入/删除编排收束到 `contexts/*/infrastructure` adapter，再由 application use case 统一调度。

---

## 已完成范围

1. BoardHeat 查询侧迁入 `contexts.board_heat`。
2. 外部板块管理与热度计算任务迁入 `contexts.board_heat`。
3. 客户端离线同步 `/api/sync/*` 迁入 `contexts.market_data`。
4. `/admin` 数据文件、导入、删除、已导入日期迁入 `contexts.market_data`。
5. `/admin/login-history` 迁入 `contexts.identity`。
6. 旧 `app.routers.board_heat`、`app.routers.ext_board_mgmt`、`app.routers.sync`、`app.routers.admin` 均退为兼容入口。

---

## 验证

```powershell
cd backend
uv run pytest -q --disable-warnings
uv run python scripts/export_api_contract.py
```

结果：

```text
full pytest exited 0
106 tests collected
126 routes
```

---

## 遗留项

1. `core/data_manager.py` 仍是启动检查兼容入口，直接调用历史导入脚本；它不暴露 API，本轮作为 startup compatibility 保留。
2. `scripts/import_*`、`scripts/sync_ext_boards.py`、`scripts/task_board_heat.py` 仍是脚本入口；现在由 infrastructure adapter 调用。
3. BoardHeat 查询仍使用 raw SQL adapter，没有强行 ORM/DDD 化。
4. 数据导入/删除后的缓存重载顺序保持历史行为：清 API cache、清 HotSpotsCache、执行 preload。

---

## 结论

DEC-002 Level 4 已完成。下一步进入 Level 5：composition root 改为直接装配 context router，并补齐最终退场 RES。
