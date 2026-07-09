# RES-021: Analysis 行业查询侧迁移结果

**日期**: 2026-07-08
**状态**: [PARTIAL]
**类型**: Infra / Backend / Architecture / Migration / Testing
**层级**: Backend
**关联**: DEC-002, SUG-003, RES-020

---

## 结果摘要

已完成 DEC-002 Level 3 的第五批迁移：`industry.py` 与 `industry_detail.py` 迁入 `contexts.analysis`，旧 router 退为兼容入口。

本次迁移将行业统计、行业趋势、TOP 行业、加权行业统计、行业成分股、行业详情、行业趋势详情和行业对比统一收束到 Analysis 查询侧。旧 `industry_service_db`、`industry_detail_service`、Numpy cache、统一缓存与信号计算链路保持兼容。

---

## 已完成改动

1. 新增 Analysis industry 查询 DTO：
   - `GetIndustryStatsQuery`
   - `GetIndustryTrendQuery`
   - `GetTopIndustryQuery`
   - `GetWeightedIndustryQuery`

2. 新增 Analysis industry detail 查询 DTO：
   - `IndustryDetailSignalThresholdSettings`
   - `GetIndustryStocksQuery`
   - `GetIndustryDetailQuery`
   - `GetIndustryDetailTrendQuery`
   - `CompareIndustriesQuery`

3. 新增 application port：
   - `IndustryAnalysisQueryPort`
   - `IndustryDetailAnalysisQueryPort`

4. 新增查询用例：
   - `GetIndustryStatsUseCase`
   - `GetIndustryTrendUseCase`
   - `GetTopIndustryUseCase`
   - `GetWeightedIndustryUseCase`
   - `GetIndustryStocksUseCase`
   - `GetIndustryDetailUseCase`
   - `GetIndustryDetailTrendUseCase`
   - `CompareIndustriesUseCase`

5. 新增 infrastructure adapter：
   - `LegacyIndustryAnalysisAdapter`
   - `LegacyIndustryDetailAnalysisAdapter`

6. 新增 API adapter：
   - `contexts.analysis.api.industry_router`
   - `contexts.analysis.api.industry_detail_router`

7. 旧 `app.routers.industry` 与 `app.routers.industry_detail` 退为兼容入口。

---

## API 契约

保持以下路径不变：

```text
GET /api/industry/stats
GET /api/industry/trend
GET /api/industry/top1000
GET /api/industry/weighted
GET /api/industry/{industry_name}/stocks
GET /api/industry/{industry_name}/detail
GET /api/industry/{industry_name}/trend
POST /api/industry/compare
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
95 passed
```

新增测试：

1. industry use case 会完整委托给 port。
2. legacy industry adapter 会从 Numpy cache 构造行业趋势响应。
3. industry detail use case 会完整委托给 port。
4. legacy industry detail adapter 会转换信号阈值与行业对比参数。
5. API contract 保持 126 routes，并确认行业详情动态路由与 `POST /api/industry/compare` 均迁入新 adapter。

---

## 遗留项

1. `industry_service_db.py` 与 `industry_detail_service.py` 仍位于旧 `app.services`，当前只通过 adapter 包装。
2. `industry_detail_service.get_industry_trend()` 内部使用局部 `TTLCache` 名称，历史代码中疑似缺少显式导入；当前默认单测未触发真实路径，后续建议单独修复或在迁移算法本体时一并处理。
3. Level 3 仍需迁移：
   - `strategies.py`
   - `/api/hot-spots/full`

---

## 后续建议

下一批建议处理 `strategies.py`。该文件包含策略算法调用、异步线程池和较重的 router 内编排，应只先做 query use case + legacy strategy adapter，避免同时重写策略算法。
