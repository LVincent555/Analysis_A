# RES-016: Operations 策略提供器收敛结果

**日期**: 2026-07-08
**状态**: [SOLVED]
**类型**: Infra / Backend / Architecture / Migration / Testing
**层级**: Backend
**关联**: DEC-002, SUG-003, RES-012, RES-015

---

## 结果摘要

已将旧 `app.services.policy_engine.PolicyEngine` 的真实实现迁入 `contexts.operations.infrastructure.policy_engine.CachedPolicyProvider`。旧 `app.services.policy_engine` 退为兼容入口，Identity 的登录/会话策略读取改为直接依赖 Operations 的策略提供器。

---

## 已完成改动

1. 新增 `contexts.operations.infrastructure.policy_engine.CachedPolicyProvider`：
   - 从 `UnifiedCache.config` 读取登录策略。
   - 从 `UnifiedCache.config` 读取会话策略。
   - 从 `UnifiedCache.config` 读取密码策略。
   - 保留配置 miss 限频告警和默认值兜底。
2. `contexts.identity.infrastructure.policy_provider` 改为调用 `CachedPolicyProvider`。
3. `app/services/policy_engine.py` 改为兼容入口：

```python
from ..contexts.operations.infrastructure.policy_engine import CachedPolicyProvider as PolicyEngine
```

4. 测试夹具同步 patch 新旧策略类，兼容旧测试入口。
5. 登录路由注释从 `PolicyEngine` 改为“策略提供器”。

---

## 测试与验证

后端单元测试：

```text
cd backend
uv run pytest
```

结果：

```text
79 passed, 212 warnings
```

API contract：

```text
126 routes
```

新增测试：

1. 策略提供器从配置缓存读取登录策略。
2. 用户设备数覆盖全局设备数。
3. 密码策略按缓存配置校验。

---

## 遗留项

1. 旧 `app.services.policy_engine.PolicyEngine` 仍保留兼容入口，待旧服务目录最终退场时删除。
2. `admin.py` 中数据导入/删除属于跨上下文 command，仍需后续结合 MarketData / Analysis 迁移处理。

---

## 后续建议

DEC-002 Level 2 的 Operations 主体迁移已经基本完成；下一步进入 Level 3：MarketData 与 Analysis 查询侧迁移。
