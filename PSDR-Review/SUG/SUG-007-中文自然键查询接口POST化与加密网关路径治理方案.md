# SUG-007: 中文自然键查询接口 POST 化与加密网关路径治理方案

**日期**: 2026-07-09
**状态**: [PROPOSED]
**类型**: Infra / Backend / Frontend / API / Security / Refactor
**层级**: Backend + frontend-client
**关联**: SUG-004, SUG-005, DEC-002, DEC-004, RES-013, RES-034

---

## 结论摘要

建议保留当前加密网关 path canonicalize 修复，并在此基础上，把“中文自然键 + 参数较多”的板块详情查询接口逐步新增为固定路径 POST 查询接口。

推荐新增接口：

```text
POST /api/industry/detail/query
POST /api/industry/stocks/query
POST /api/industry/trend/query
```

旧接口先保留兼容：

```text
GET /api/industry/{industry_name}/detail
GET /api/industry/{industry_name}/stocks
GET /api/industry/{industry_name}/trend
```

核心判断：

1. 当前外层传输已经是 `POST /api/secure`，问题不是“HTTP GET 裸传”，而是加密网关内部签名对动态 path 的编码形态敏感。
2. 副手已修复的 `canonical_gateway_path()` 是必要修复，不应回退；即使板块详情改成 POST，其他动态路径也可能遇到编码问题。
3. 中文板块名这类自然键不适合长期放在 path segment 中，尤其在加密网关、签名、ASGI 内部转发、React encodeURIComponent 多方共同参与时，维护成本偏高。
4. 对板块详情、成分股、趋势这种 read-heavy 查询，POST query endpoint 是可以接受的工程折中：固定 ASCII path，中文和复杂参数进入 JSON body，body hash 参与内部签名。

---

## 背景

副手定位到中文板块详情失败的根因：

```text
客户端内部 path:
/api/industry/%E5%8D%8A%E5%AF%BC%E4%BD%93/detail

后端 middleware 校验 path:
/api/industry/半导体/detail
```

签名时两边参与 HMAC 的 path 字符串不同，因此后端拒绝：

```text
403 无效的加密网关内部签名
```

当前已推送修复：

```text
eb42a9b fix: canonicalize secure gateway signed paths
```

修复点：

- `backend/app/shared/gateway_signing.py`
- 对签名 path 执行 `unquote()`，使编码路径和解码路径在签名前归一。

该修复解决当前 bug，但暴露出一个更一般的问题：动态 path segment 中放中文、文件名、自然名称等非稳定标识，会让签名、转发、路由匹配和前端编码形成隐性耦合。

---

## 当前链路事实

### 1. 外层已经是 POST

`frontend-client/src/services/secureApi.js` 当前所有业务请求都会发到：

```text
POST /api/secure
```

加密 payload 中包含：

```json
{
  "path": "/api/industry/%E5%8D%8A%E5%AF%BC%E4%BD%93/detail",
  "method": "GET",
  "params": {},
  "body": null,
  "timestamp": 1783519000000,
  "nonce": "..."
}
```

因此，“改成 POST”如果只是从浏览器角度看，外层已经是 POST；真正要改的是加密 payload 中的内部业务方法和内部业务路径。

### 2. 内部网关签名绑定 method、path、timestamp、body hash

内部签名大致绑定：

```text
METHOD
canonical_path
timestamp
sha256(body)
```

这意味着 body 是安全参与签名的。把中文板块名放到 body 后，不会降低内部签名完整性。

### 3. 当前板块详情接口使用中文 path 参数

后端：

```text
GET /api/industry/{industry_name}/detail
GET /api/industry/{industry_name}/stocks
GET /api/industry/{industry_name}/trend
```

前端至少存在以下调用：

```text
frontend-client/src/pages/IndustryDetailPage.js
frontend-client/src/components/dialogs/IndustryDetailDialog.js
frontend-client/src/components/modules/IndustryQueryModule.js
```

典型调用：

```js
apiClient.get(`/api/industry/${encodeURIComponent(industryName)}/detail`)
```

---

## 目标

1. 降低加密网关对 URL 编码细节的敏感度。
2. 避免中文自然键长期出现在 path segment 中。
3. 保持已有 GET 接口兼容，避免一次性破坏前端入口。
4. 让复杂查询参数集中进入 JSON body，便于前后端类型化和测试。
5. 为后续板块查询扩展更多筛选条件、信号阈值、版本参数预留稳定接口形态。

---

## 非目标

1. 不推翻 `/api/secure` 加密网关。
2. 不回退 `eb42a9b` 的 path canonicalize 修复。
3. 不要求全项目所有 GET 查询都改 POST。
4. 不重写行业详情 use case、repository 或数据库查询。
5. 不改变当前业务响应结构。

---

## 方案选项

### 选项 A：只保留 path canonicalize 修复

做法：

- 保留 `canonical_gateway_path(path) -> unquote(path)`。
- 不新增接口。
- 前端继续使用 `GET /api/industry/{encodeURIComponent(name)}/detail`。

优点：

1. 成本最低。
2. 当前 bug 已被修复。
3. API 契约不变。

缺点：

1. 中文自然键仍在 path segment 中。
2. 未来其他编码字符、斜杠类字符、文件名类 path 仍可能触发类似边界。
3. 复杂筛选参数继续分散在 path + query params 中。

适用：

- 只想快速稳定当前页面，不做接口治理。

### 选项 B：新增 POST 查询接口，旧 GET 保留兼容

做法：

- 新增固定路径 POST endpoint：

```text
POST /api/industry/detail/query
POST /api/industry/stocks/query
POST /api/industry/trend/query
```

- body 承载中文板块名和参数：

```json
{
  "industry_name": "半导体",
  "date": "20260709",
  "sort_mode": "signal",
  "calculate_signals": true,
  "hot_list_mode": "frequent",
  "hot_list_version": "v2",
  "hot_list_top": 100,
  "rank_jump_min": 2000,
  "steady_rise_days": 3,
  "price_surge_min": 5.0,
  "volume_surge_min": 10.0,
  "volatility_surge_min": 10.0
}
```

- 前端新代码切到 POST。
- 旧 GET endpoint 暂时保留，内部复用同一查询构造函数。

优点：

1. 固定 path 为 ASCII，网关签名更稳。
2. 中文自然键进入 body，避免编码/解码路径差异。
3. 参数多的查询更容易类型化。
4. 向后兼容，迁移风险可控。
5. 符合当前项目“加密网关下的内部命令/查询 envelope”风格。

缺点：

1. 需要新增 request model。
2. 前端需要改 3 个左右调用点。
3. REST 纯粹性略下降：查询使用 POST。

适用：

- 推荐采用。

### 选项 C：全项目动态中文 path 全部改 POST

做法：

- 扫描所有中文名、文件名、自然键 path。
- 统一改为固定 path + body。

优点：

1. 一次性治理彻底。
2. 可以形成统一 API 规范。

缺点：

1. 范围过大。
2. 容易与当前前端重构、后端缓存治理、安全网关治理交叉。
3. 当前已知问题只集中在板块详情类接口，没必要扩大战场。

适用：

- 后续做 API v2 契约治理时再考虑。

---

## 推荐方案

采用选项 B：新增 POST 查询接口，旧 GET 保留兼容。

理由：

1. 当前 bug 的直接修复已经完成，不需要为了 bug 本身大改。
2. 板块详情类接口参数多、中文名是自然键，确实更适合 body。
3. POST query endpoint 不影响外层 `/api/secure`，只改变内部业务 envelope。
4. 可以小范围落地，验证成本低。
5. 旧 GET 可继续服务历史入口，避免引入兼容性回归。

---

## 目标接口设计

### 1. 板块详情

```text
POST /api/industry/detail/query
```

Request:

```json
{
  "industry_name": "半导体",
  "date": "20260709",
  "k": 0.618
}
```

Response:

沿用 `IndustryDetailResponse`。

### 2. 板块成分股

```text
POST /api/industry/stocks/query
```

Request:

```json
{
  "industry_name": "半导体",
  "date": "20260709",
  "sort_mode": "signal",
  "calculate_signals": true,
  "hot_list_mode": "frequent",
  "hot_list_version": "v2",
  "hot_list_top": 100,
  "rank_jump_min": 2000,
  "steady_rise_days": 3,
  "price_surge_min": 5.0,
  "volume_surge_min": 10.0,
  "volatility_surge_min": 10.0
}
```

Response:

沿用 `IndustryStocksResponse`。

### 3. 板块趋势

```text
POST /api/industry/trend/query
```

Request:

```json
{
  "industry_name": "半导体",
  "period": 7,
  "k": 0.618
}
```

Response:

沿用 `IndustryTrendResponse`。

---

## 后端改动范围

### 1. 新增 request model

建议放在：

```text
backend/app/models/industry_detail.py
```

新增模型：

```text
IndustryDetailQueryRequest
IndustryStocksQueryRequest
IndustryTrendQueryRequest
```

字段默认值应与现有 GET query 参数保持一致。

### 2. 拆出内部查询构造函数

建议在：

```text
backend/app/contexts/analysis/api/industry_detail_router.py
```

抽出私有函数：

```text
_get_industry_detail(...)
_get_industry_stocks(...)
_get_industry_trend(...)
```

GET endpoint 和 POST endpoint 都调用同一内部函数，避免双份业务逻辑。

### 3. 新增 POST endpoint

新增：

```text
@router.post("/detail/query")
@router.post("/stocks/query")
@router.post("/trend/query")
```

注意路由顺序：

- 固定路径 `/detail/query`、`/stocks/query`、`/trend/query` 应放在 `/{industry_name}/...` 动态路由之前。
- 避免 `detail` 被错误匹配为 `industry_name`。

### 4. 保留旧 GET endpoint

旧接口标记为兼容入口，暂不删除：

```text
GET /api/industry/{industry_name}/detail
GET /api/industry/{industry_name}/stocks
GET /api/industry/{industry_name}/trend
```

可在注释或文档中标记：

```text
Compatibility endpoint. Prefer POST /query endpoint for new frontend calls.
```

---

## 前端改动范围

### 1. 新增 service 封装

建议在现有前端架构下新增或扩展：

```text
frontend-client/src/services/industryDetailService.js
```

提供：

```js
getIndustryDetail({ industryName, date, k })
getIndustryStocks({ industryName, date, sortMode, signalThresholds })
getIndustryTrend({ industryName, period, k })
```

内部统一调用：

```js
apiClient.post('/api/industry/detail/query', payload)
apiClient.post('/api/industry/stocks/query', payload)
apiClient.post('/api/industry/trend/query', payload)
```

### 2. 替换页面直接拼 path

优先替换：

```text
frontend-client/src/pages/IndustryDetailPage.js
frontend-client/src/components/dialogs/IndustryDetailDialog.js
frontend-client/src/components/modules/IndustryQueryModule.js
```

从：

```js
apiClient.get(`/api/industry/${encodeURIComponent(industryName)}/detail`, ...)
```

改为：

```js
industryDetailService.getIndustryDetail({ industryName, date: selectedDate })
```

### 3. 保留 apiClient 能力

`apiClient.get/post` 和 `secureApi.request` 不需要大改。

这次不建议在通用 `apiClient` 层自动做 path canonicalization，因为：

1. 当前后端签名层已做 canonicalize。
2. 通用层改动影响所有接口。
3. 本问题更适合通过业务 endpoint 形态治理。

---

## 测试计划

### 后端单元测试

建议新增或扩展：

```text
backend/tests/unit/test_industry_detail_post_queries.py
```

覆盖：

1. POST detail query 接受中文 `industry_name`。
2. POST stocks query 参数默认值与 GET 兼容。
3. POST trend query 参数默认值与 GET 兼容。
4. 固定 POST 路由不会被 `/{industry_name}` 动态路由抢占。

### 安全网关测试

保留并扩展：

```text
backend/tests/unit/test_security_level_1_5.py
```

覆盖：

1. 编码 path 与解码 path 签名兼容。
2. 固定 POST path + 中文 body 时，body tamper 会导致签名失败。
3. method 从 GET 改为 POST 后，method tamper 仍会失败。

### 前端验证

建议手工验证：

1. 登录后点击中文板块详情，例如“半导体”。
2. 详情页、成分股、趋势 tab 都正常加载。
3. Network 中外层仍为 `POST /api/secure`。
4. 加密 payload 内部 path 为固定 ASCII：

```text
/api/industry/detail/query
/api/industry/stocks/query
/api/industry/trend/query
```

---

## 实施计划

### Phase 1：后端兼容接口

1. 新增 request model。
2. 抽出路由内部复用函数。
3. 新增 3 个 POST query endpoint。
4. 保留旧 GET endpoint。
5. 补后端单测。

验收：

```powershell
cd backend
uv run pytest -q tests/unit/test_security_level_1_5.py tests/unit/test_industry_detail_post_queries.py
uv run pytest -q tests/unit
```

### Phase 2：前端调用迁移

1. 新增或扩展 industry detail service。
2. 替换 3 个直接拼中文 path 的调用点。
3. 保留旧 GET 作为后端兼容，不再由新前端主动调用。

验收：

1. 中文板块详情页可打开。
2. 成分股列表可加载。
3. 趋势 tab 可加载。

### Phase 3：观察与退场

1. 观察一段时间旧 GET endpoint 是否仍被调用。
2. 若后续建立 API v2，可考虑废弃旧 GET。
3. 当前不建议立即删除旧 GET。

---

## 风险与注意事项

1. POST 查询接口不应被误认为有副作用，应在命名中保留 `/query`。
2. FastAPI 路由顺序必须处理好，固定路径应写在动态路径前。
3. 请求模型默认值必须和现有 GET Query 默认值保持一致。
4. 前端迁移时不要遗漏弹窗、模块页、详情页三个入口。
5. `canonical_gateway_path()` 仍然必须保留，它解决的是通用网关签名问题。

---

## 最终建议

本方案建议进入执行队列，但不需要签发 DEC。原因是：

1. 不改变整体架构方向。
2. 不改变 `/api/secure` 加密网关设计。
3. 不删除旧接口。
4. 属于 API 形态治理与前后端兼容迁移。

若后续要扩大到全项目 API v2、统一废弃动态自然键 path，再另行签发 DEC。
