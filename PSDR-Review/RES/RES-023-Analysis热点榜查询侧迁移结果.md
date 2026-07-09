# RES-023: Analysis 热点榜查询侧迁移结果

**日期**: 2026-07-08
**状态**: [SOLVED]
**类型**: Infra / Backend / Architecture / Migration / Testing
**层级**: Backend
**关联**: DEC-002, SUG-003, RES-022

---

## 结果摘要

已完成 DEC-002 Level 3 的收口迁移：`/api/hot-spots/full` 从旧 `app.routers.analysis` 中迁入 `contexts.analysis` 查询侧。

该接口依赖 `HotSpotsCache`、`numpy_cache` 和统一 API cache，不直接依赖外部板块热度表，因此归属 Analysis，而不是 BoardHeat。BoardHeat 后续只处理外部板块、热度计算、热度查询、同步任务与相关管理接口。

---

## 已完成改动

1. 新增 Analysis hot spots 查询 DTO：
   - `GetHotSpotsFullQuery`

2. 新增 application port：
   - `HotSpotsAnalysisQueryPort`

3. 新增查询用例：
   - `GetHotSpotsFullUseCase`

4. 新增 infrastructure adapter：
   - `LegacyHotSpotsAnalysisAdapter`

5. 新增 API adapter：
   - `contexts.analysis.api.hot_spots_router`

6. 旧 `app.routers.analysis` 继续作为兼容入口，只装配 Analysis 新 router。

---

## API 契约

保持以下路径不变：

```text
GET /api/hot-spots/full
```

API contract 导出结果：

```text
126 routes
```

端点归属已切换为：

```text
app.contexts.analysis.api.hot_spots_router.get_hot_spots_full
```

---

## 测试与验证

局部验证：

```powershell
cd backend
uv run pytest tests/unit/test_analysis_hot_spots_queries.py tests/unit/test_analysis_strategy_queries.py tests/unit/test_architecture_boundaries.py -q
```

结果：

```text
8 passed
```

新增测试：

1. hot spots use case 完整委托给 port。
2. legacy hot spots adapter 可使用最新日期、读取 `HotSpotsCache` 并写入统一 API cache。
3. 架构边界检查通过。
4. API contract 保持 126 routes，热点榜端点已切换到 `contexts.analysis.api.hot_spots_router`。

---

## 遗留项

1. `HotSpotsCache` 仍位于旧 `app.services`，当前只由 infrastructure adapter 包装。
2. `HotSpotsCache` 内部仍直接调用 `numpy_cache.index_mgr` 与 `get_top_n_by_rank()`，后续若要重构算法本体，应另开策略/缓存层专项。
3. Level 3 已收口，下一步进入 Level 4：BoardHeat 与同步导入迁移。
