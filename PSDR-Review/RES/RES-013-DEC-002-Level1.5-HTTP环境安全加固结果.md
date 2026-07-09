# RES-013: DEC-002 Level 1.5 HTTP 环境安全加固结果

**日期**: 2026-07-08
**状态**: [SOLVED]
**类型**: Infra / Backend / Frontend / Security / Architecture / Testing
**层级**: Backend + frontend-client
**关联**: DEC-002, SUG-004, SUG-003, RES-012

---

## 结果摘要

已完成 DEC-002 Level 1.5 / SUG-004 的第一阶段实现：在暂时没有 HTTPS 的前提下，登录与刷新链路改为应用层公钥信封，secure gateway 增加 nonce 防重放，内部转发 header 改为 HMAC 签名，JWT 与 master key 默认密钥改为显式开发模式兜底。

本次实现不把该方案声明为 HTTPS 替代品。公网环境仍建议启用 HTTPS；Electron 本地 token/session key 迁移到 main process + safeStorage 仍作为后续第二阶段。

---

## 已完成改动

### Backend

1. 新增 `app/core/security_settings.py`：
   - `JWT_SECRET_KEY`、`MASTER_ENCRYPTION_KEY`、`LOGIN_PRIVATE_KEY`、`LOGIN_PUBLIC_KEY_ID`、`INTERNAL_GATEWAY_SECRET` 统一读取。
   - 默认密钥只在 `ALLOW_INSECURE_DEV_KEYS=true` 时允许。
   - 应用启动阶段执行 `validate_runtime_security_config()`。
2. JWT 发行 adapter `contexts.identity.infrastructure.jwt_tokens` 不再使用旧默认 secret。
3. master key 加密器 `crypto.aes_handler` 不再静默使用生产默认 master key。
4. 新增 `contexts.identity.infrastructure.login_envelope`：
   - RSA-OAEP + AES-GCM hybrid envelope。
   - timestamp 校验。
   - nonce 去重。
   - 响应独立 IV 加密返回。
5. 新增 `/api/auth/secure-login`：
   - 登录 payload 加密传输。
   - 登录响应中的 token、refresh token、session key、user 加密返回。
6. 新增 `/api/auth/secure-refresh`：
   - refresh token 不再需要通过明文 `/api/auth/refresh` 发送。
   - 旧 refresh 入口保留兼容。
7. `/api/auth/login` 在 `REQUIRE_SECURE_LOGIN=true` 时拒绝明文登录。
8. `/api/secure` 增加 `user_id + device_id + nonce` 五分钟窗口去重。
9. secure gateway 内部 ASGI 转发改为 `x-secure-gateway-ts` + `x-secure-gateway-sig` HMAC 签名。
10. `AuthMiddleware` 不再信任外部裸传 `x-secure-gateway: 1`。
11. 新增 `scripts/generate_security_secrets.py`，用于生成后端 `.env` 与前端 `.env` 所需密钥。
12. `.env.example` 增加安全配置示例。

### frontend-client

1. 新增 `src/utils/loginEnvelope.js`：
   - 固定登录公钥、`key_id` 与 fingerprint。
   - 本地校验公钥 fingerprint。
   - 生成 RSA-OAEP + AES-GCM 登录/刷新信封。
   - 解密 secure-login / secure-refresh 响应。
2. `authService.login()` 优先调用 `/api/auth/secure-login`。
3. `authService.refreshAccessToken()` 优先调用 `/api/auth/secure-refresh`。
4. 只有 `REACT_APP_ALLOW_PLAINTEXT_LOGIN=true` 时才回退旧明文登录/刷新。

---

## 测试与验证

后端单元测试：

```text
cd backend
uv run pytest
```

结果：

```text
71 passed, 208 warnings
```

新增覆盖：

1. secure-login 合法信封解密并返回加密响应。
2. secure-login 重复 nonce 返回 409。
3. secure-refresh 返回加密 access token。
4. 内部网关 HMAC 签名校验。
5. 外部伪造 `x-secure-gateway: 1` 被拒绝。
6. 默认 JWT secret 需要显式开发开关。

API contract：

```text
126 routes
```

新增路由：

```text
POST /api/auth/secure-login
POST /api/auth/secure-refresh
```

前端构建：

```text
node node_modules/react-scripts/scripts/build.js
```

结果：构建成功。仍存在原项目已有 ESLint warnings，包括未使用变量、BOM、hook dependency、Browserslist 过期提示；本次新增 secure-login 模块未引入构建错误。

前端公钥 fingerprint：

```text
cbffTkg1lSQUfA56sBVNFdF1HIfyUgST4hDUdr-wlyk
```

已用 Node + node-forge 验证与后端 SPKI SHA-256 结果一致。

后续全量回归更新：

```text
uv run pytest -q --disable-warnings -> exited 0
uv run pytest --collect-only -> 106 tests collected
API contract -> 126 routes
```

---

## 验收对照

| 验收项 | 结果 |
|------|------|
| HTTP 登录请求不含明文用户名/密码 | 已完成，`authService.login()` 默认走 secure-login |
| 登录响应不明文返回 token/refresh token/session key | 已完成，响应信封加密 |
| refresh token 不通过明文 refresh 暴露 | 已补强，新增 secure-refresh 并默认使用 |
| 默认 JWT/master key 不再静默兜底 | 已完成，仅 `ALLOW_INSECURE_DEV_KEYS=true` 允许开发兜底 |
| `/api/secure` nonce 防重放 | 已完成 |
| 外部伪造 `x-secure-gateway: 1` 不能绕过网关 | 已完成 |
| 前端公钥 pin/fingerprint 校验 | 已完成 |
| 密钥生成脚本 | 已完成 |

---

## 遗留项

1. 旧 `/api/auth/login` 与 `/api/auth/refresh` 仍保留兼容入口；生产/正式模式应设置 `REQUIRE_SECURE_LOGIN=true` 且前端不设置 `REACT_APP_ALLOW_PLAINTEXT_LOGIN=true`。
2. nonce store 当前是进程内内存实现；多 worker / 多实例部署时需要迁到 Redis 或统一缓存的跨进程 region。
3. Electron renderer 仍使用 `localStorage` 保存 token、refresh token 和 session key；迁到 main process + `safeStorage` 是后续第二阶段。
4. 本方案仍不替代 HTTPS，正式公网部署应增加 TLS。
5. 前端 secure-login 独立单元测试尚未补齐；当前前端验收基于生产构建和公钥 fingerprint 校验。

---

## 后续建议

DEC-002 下一步回到 Level 2：继续 Operations 迁移，优先处理 `cache_mgmt.py`、`core/audit.py` 与 `PolicyEngine` 边界收敛。
