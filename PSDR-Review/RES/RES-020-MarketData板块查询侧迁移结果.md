# RES-020: MarketData 板块查询侧迁移结果

**日期**: 2026-07-08
**状态**: [PARTIAL]
**类型**: Infra / Backend / Architecture / Migration / Testing
**层级**: Backend
**关联**: DEC-002, SUG-003, RES-019

---

## 结果摘要

已完成 DEC-002 Level 3 的第四批迁移：`routers/sector.py` 中的板块查询入口迁入 `contexts.market_data`，旧 router 退为兼容入口。

本次迁移重点处理了原先写在 router 内的 Numpy cache 查询、趋势计算和排名变化统计，并保留通用 `{sector_name}` 路由在最后注册，避免抢占 `/sectors/trend`、`/sectors/rank-changes` 等固定路径。

---

## 已完成改动

1. 新增 MarketData sector 查询 DTO：
   - `GetSectorRankingQuery`
   - `GetSectorRawDataQuery`
   - `SearchSectorsQuery`
   - `GetSectorTrendQuery`
   - `GetSectorRankChangesQuery`
   - `GetSectorDetailQuery`

2. 新增 application error：
   - `MarketDataNotFoundError`

3. 扩展 MarketData port：
   - `SectorQueryPort`

4. 新增 sector 查询用例：
   - `GetSectorAvailableDatesUseCase`
   - `GetSectorRankingUseCase`
   - `GetSectorRawDataUseCase`
   - `SearchSectorsUseCase`
   - `GetSectorTrendUseCase`
   - `GetSectorRankChangesUseCase`
   - `GetSectorDetailUseCase`

5. 新增 infrastructure adapter：
   - `contexts.market_data.infrastructure.sector_queries.LegacySectorQueryAdapter`
   - 将 raw-data、trend、rank-changes 中的 Numpy cache 计算从 router 下沉到 adapter。
   - ranking/search/detail 继续包装旧 `sector_service_db`。

6. 新增 API adapter：
   - `contexts.market_data.api.sector_router`

7. 旧 `app.routers.sector` 退为兼容入口。

---

## API 契约

保持以下路径不变：

```text
GET /api/sectors/dates
GET /api/sectors/ranking
GET /api/sector-ranking
GET /api/sectors/raw-data
GET /api/sectors/search/{keyword}
GET /api/sectors/trend
GET /api/sectors/rank-changes
GET /api/sectors/{sector_name}
GET /api/sector/{sector_name}
```

API contract 导出结果：

```text
126 routes
```

---

## 测试与验证

后端全量单元测试：

```powershell
cd backend
uv run pytest -q
```

结果：

```text
91 passed
```

新增测试：

1. sector use case 会完整委托给 port。
2. legacy sector adapter 会从 Numpy cache 构造 `/api/sectors/raw-data` 响应。
3. legacy sector adapter 会从 Numpy cache 构造 `/api/sectors/trend` 响应。
4. API contract 保持 126 routes，并确认 sector 固定路径与动态路径均注册到新 adapter。

---

## 遗留项

1. `sector_service_db.py` 仍位于旧 `app.services`，当前只通过 adapter 包装。
2. Level 3 仍需迁移：
   - `industry.py`
   - `industry_detail.py`
   - `strategies.py`
   - `/api/hot-spots/full`
3. `admin.py` 中股票/板块数据导入、删除仍属于后续 MarketData command 侧迁移。

---

## 后续建议

下一批建议处理 `industry.py` 与 `industry_detail.py`。其中 `industry_detail.py` 带较多信号增强和统计汇总，适合作为 Analysis query adapter；`industry.py` 更接近 MarketData 基础分组查询。
