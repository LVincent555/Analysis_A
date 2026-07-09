# SUG-004: HTTP 环境登录加密与安全网关加固方案

**日期**: 2026-07-08
**状态**: [ACCEPTED / IMPLEMENTED]
**类型**: Infra / Backend / Frontend / Security / Architecture
**层级**: Backend + frontend-client
**关联**: DEC-002, DEC-003, SUG-001, RES-003, RES-005, RES-012, RES-013

---

## 结论摘要

基于本轮关于 HTTP、应用层 AES、公私钥和 JWT 的讨论，结论如下：

1. 没有 HTTPS 时，现有 `/api/secure` 只能保护登录后的业务请求，不能保护 `/api/auth/login` 的用户名和密码。
2. 登录阶段必须增加公钥信封，并且 Electron 客户端必须固定服务端公钥或公钥指纹；否则中间人可以替换公钥。
3. JWT 不需要马上从 HS256 换成非对称算法，但必须移除默认 secret 兜底，改成强随机 `JWT_SECRET_KEY`。
4. `x-secure-gateway: 1` 不能继续作为可信内部标记，必须升级为服务端 HMAC 内部签名。
5. 本方案是“无 HTTPS 环境的应用层加固”，不是 TLS 的完整替代；后续公网化仍建议上 HTTPS。

本 SUG 已被纳入 DEC-002 Level 1.5 并完成第一阶段实现，结果见 RES-013。

---

## 背景

当前项目是个人 Electron 项目，部署环境可能暂时没有 HTTPS。已有 `/api/secure` AES-GCM 加密网关，业务请求在登录后可以走应用层加密，但仍存在几类系统性风险：

1. 登录阶段 `/api/auth/login` 仍以 HTTP 明文提交用户名和密码。
2. JWT 和 master key 仍存在默认密钥兜底，若运行环境未设置真实密钥，会导致 token 可伪造或主密钥可预测。
3. `x-secure-gateway: 1` 是客户端也能伪造的普通 header，不能作为可信内部请求标记。
4. `/api/secure` 只有 5 分钟 timestamp 校验，未对 nonce 做服务端去重，存在短时间重放风险。
5. access token、refresh token、session key 仍主要放在 renderer 可访问的 `localStorage`。

说明：Identity 迁移后，session key 已经按 `user_id + device_id` 存储，早期“多设备覆盖 session key”的问题已被修复，不再作为本 SUG 的主要问题。

---

## 威胁模型

本方案面向的现实目标：

1. 在没有 HTTPS 的情况下，降低被动抓包者直接看到用户名、密码、refresh token、session key 的风险。
2. 防止默认 JWT secret / master key 造成的 token 伪造和密钥预测。
3. 防止外部客户端伪造 secure gateway 内部转发 header。
4. 防止 5 分钟窗口内重放已捕获的加密请求。

本方案不承诺解决：

1. 客户端机器已经被恶意软件控制。
2. Electron 包被攻击者替换或公钥 pin 被篡改。
3. 服务端私钥泄漏。
4. 互联网级别的完整传输安全替代。正式公网环境仍建议上 HTTPS。

---

## 推荐方案

采用 **登录公钥信封 + 强制真实密钥 + secure gateway 防重放 + 内部 header 加固**。

### 1. 登录阶段增加公钥信封

新增安全登录端点：

```text
POST /api/auth/secure-login
```

同时新增安全刷新端点：

```text
POST /api/auth/secure-refresh
```

保留旧 `/api/auth/login` 与 `/api/auth/refresh` 作为开发兼容入口，但在 `REQUIRE_SECURE_LOGIN=true` 时禁用明文登录，前端也只在 `REACT_APP_ALLOW_PLAINTEXT_LOGIN=true` 时回退明文登录/刷新。

推荐 V1 方案使用 RSA-OAEP + AES-GCM hybrid envelope，原因是 Web/Electron 兼容性好，前后端实现成本低：

1. 服务端生成长期 RSA-OAEP 密钥对。
2. 服务端私钥只放后端环境变量或安全文件。
3. 服务端公钥和 `key_id` 固定写入 Electron 客户端构建产物。
4. 客户端登录时生成一次性 AES-GCM key。
5. 客户端用 AES-GCM 加密登录 payload。
6. 客户端用服务端 RSA-OAEP public key 加密一次性 AES key。
7. 服务端解出 AES key，再解出登录 payload。
8. 服务端校验 timestamp + nonce，成功后用同一 AES key 加密登录响应。

请求结构建议：

```json
{
  "key_id": "login-rsa-2026-07",
  "encrypted_key": "base64(rsa-oaep(aes_key))",
  "iv": "base64(12 bytes)",
  "nonce": "base64(16-32 bytes)",
  "timestamp": 1783519000000,
  "data": "base64(aes-gcm(login_payload))"
}
```

登录 payload：

```json
{
  "username": "...",
  "password": "...",
  "device_id": "...",
  "device_name": "...",
  "timestamp": 1783519000000,
  "nonce": "same-or-inner-random"
}
```

响应结构建议：

```json
{
  "iv": "base64(12 bytes)",
  "data": "base64(aes-gcm(login_response))"
}
```

字段约定：

1. 请求 `iv` 用于登录 payload 加密。
2. 响应 `iv` 单独生成，不复用请求 `iv`。
3. `data` 建议存放 `ciphertext + tag` 的 base64 编码。
4. AES-GCM AAD 建议绑定 `key_id + timestamp + nonce`，避免信封元信息被替换后仍可解密。
5. 登录响应中的 `token / refresh_token / session_key / user` 不再明文返回。

公钥 pin 约定：

1. 前端固定 `key_id`、public key PEM 和 public key fingerprint。
2. fingerprint 使用 SPKI DER 的 SHA-256，显示格式建议为 base64url 或 hex。
3. 客户端发起登录前必须本地校验 pinned fingerprint 与内置公钥一致。
4. 后端收到未知 `key_id` 时拒绝请求。

可选 V2：后续如需要更强前向安全性，可改为 Ed25519 签名的临时 X25519 握手 + HKDF + AES-GCM。但 V1 已足够解决当前 HTTP 明文登录的主要风险。

### 2. 禁止生产环境默认密钥

后端启动时必须检查：

1. `JWT_SECRET_KEY`
2. `MASTER_ENCRYPTION_KEY`
3. `LOGIN_PRIVATE_KEY`
4. `LOGIN_PUBLIC_KEY_ID`

规则：

1. 未设置真实密钥时，生产/正常模式直接启动失败。
2. 只有显式设置 `ALLOW_INSECURE_DEV_KEYS=true` 时才允许使用开发默认值。
3. `JWT_SECRET_KEY` 至少 32 字节随机强度。
4. `MASTER_ENCRYPTION_KEY` 必须是 32 字节 key 的 base64。
5. 增加脚本生成本地密钥，例如：

```powershell
cd backend
uv run python scripts/generate_security_secrets.py
```

JWT 当前已经迁到 `contexts.identity.infrastructure.jwt_tokens`，本阶段不优先更换算法，先禁止默认 secret。HS256 在强随机 secret 下可以继续使用。后续如需要多 key 轮换，再增加 `kid` 和 key ring。

当前代码事实：

1. `backend/app/contexts/identity/infrastructure/jwt_tokens.py` 已成为 JWT 发行与验证 adapter。
2. 该文件仍有默认 `JWT_SECRET_KEY` 兜底，本 SUG 阶段必须修掉。
3. 旧 `backend/app/auth/jwt_handler.py` 已是兼容入口，不应再新增 JWT 规则。

### 3. 修复 secure gateway 内部 header 信任

当前 `AuthMiddleware` 通过 `x-secure-gateway: 1` 判断内部网关转发，这个 header 外部客户端也能伪造。

建议改为：

1. 外部请求携带 `x-secure-gateway` 时默认拒绝或剥离。
2. `/api/secure` 内部 ASGI 转发时附带服务端私有 header：

```text
x-secure-gateway: 1
x-secure-gateway-ts: unix_ms
x-secure-gateway-sig: HMAC(server_internal_secret, method + path + timestamp + body_hash)
```

3. `AuthMiddleware` 只认可 HMAC 校验通过的内部请求。
4. `INTERNAL_GATEWAY_SECRET` 未设置时，生产模式启动失败。

这样即使攻击者知道 JWT，也不能仅靠伪造 `x-secure-gateway: 1` 绕过 secure gateway 强制策略。

### 4. `/api/secure` 增加 nonce 去重

服务端对每个已解密请求记录：

```text
secure_nonce:{user_id}:{device_id}:{nonce}
```

规则：

1. TTL 与 timestamp 窗口一致，建议 5 分钟。
2. 同一用户、同一设备、同一 nonce 只能使用一次。
3. nonce 重复返回 400 或 409。
4. 记录可放入 `UnifiedCache` 新 region，例如 `secure_nonces`，开发期可用内存 fallback。

这能阻止抓包者在 5 分钟窗口内重放加密请求。

### 5. 前端本地密钥存储分级

短期可继续使用 `localStorage`，但需要明确风险边界。建议分两级：

1. 第一阶段：保持现状，只做登录加密、nonce 和 secret 加固。
2. 第二阶段：Electron 下把 token / refresh token / session key 迁到 main process，通过 IPC 调用，并优先使用 Electron `safeStorage` 或 OS keychain。

如果用户确认本地 Electron 密钥不会泄漏，则第二阶段可以延期，但不应影响前三项服务端安全加固。

---

## 实施计划

### 阶段 A：密钥治理

后端：

1. 移除生产默认 `JWT_SECRET_KEY` 兜底。
2. 移除生产默认 `MASTER_ENCRYPTION_KEY` 兜底。
3. 增加 `LOGIN_PRIVATE_KEY` / `LOGIN_PUBLIC_KEY_ID`。
4. 增加 `INTERNAL_GATEWAY_SECRET`。
5. 增加密钥生成脚本和 `.env.example` 示例。

前端：

1. 增加登录公钥 pin 配置。
2. 标明 key id 和 fingerprint。

验收：

1. 未设置密钥时，非开发模式后端启动失败。
2. `ALLOW_INSECURE_DEV_KEYS=true` 时本地开发仍可启动。

### 阶段 B：secure-login

后端：

1. 新增登录信封解密 use case / adapter。
2. 新增 `/api/auth/secure-login`。
3. 旧 `/api/auth/login` 在 `REQUIRE_SECURE_LOGIN=true` 时拒绝。
4. 登录响应加密返回。
5. 登录 nonce 使用独立仓储去重，避免重复登录信封被重放。

前端：

1. `authService.login()` 改为优先调用 `/api/auth/secure-login`。
2. 登录 payload 带 timestamp + nonce + device_id。
3. 解密登录响应后再落本地 token/session key。
4. 仅在 `REACT_APP_ALLOW_PLAINTEXT_LOGIN=true` 时允许回退明文登录。
5. `authService.refreshAccessToken()` 改为优先调用 `/api/auth/secure-refresh`。

验收：

1. HTTP 抓包看不到明文用户名、密码、token、session key。
2. 公钥 pin 不匹配时客户端拒绝登录。
3. timestamp 过期或 nonce 重复时登录失败。

### 阶段 C：secure gateway 防重放与内部转发加固

后端：

1. 新增 secure nonce repository。
2. `/api/secure` 解密后校验 nonce 唯一性。
3. `AuthMiddleware` 不再信任裸 `x-secure-gateway: 1`。
4. 内部 ASGI 转发改为 HMAC 内部标记。

验收：

1. 同一个加密请求重放失败。
2. 外部直接请求普通 API 并伪造 `x-secure-gateway: 1` 失败。
3. `/api/secure` 内部转发仍正常。

### 阶段 D：Electron 本地存储收敛

前端：

1. token / refresh token / session key 从 renderer localStorage 迁到 main process。
2. Electron 使用 `safeStorage` 或 OS keychain。
3. renderer 只通过 IPC 获取短期调用能力。

验收：

1. localStorage 中不再保存三件套。
2. 退出登录会清理 main process 存储。

---

## 测试建议

后端单元测试：

1. 未设置密钥时启动配置校验失败。
2. `secure-login` 可解密合法信封并返回加密响应。
3. `secure-login` 拒绝过期 timestamp。
4. `secure-login` 拒绝重复 nonce。
5. `/api/secure` 拒绝重复 nonce。
6. `AuthMiddleware` 拒绝外部伪造 `x-secure-gateway`。
7. 强制安全登录模式下 `/api/auth/login` 返回 403/404。

前端测试：

1. 登录信封加密结果不包含明文用户名/密码。
2. 公钥 fingerprint 不匹配时拒绝发送登录请求。
3. secure-login 响应可正确解密并初始化 session key。

手动验证：

1. 用抓包工具确认 HTTP 登录请求中没有明文密码。
2. 重放同一 `/api/secure` 请求，第二次失败。
3. 伪造 `x-secure-gateway: 1` 直接请求管理 API，失败。

---

## 执行拆分

后端包：

1. `shared/security` 或 `core/security_settings`：统一密钥读取、dev fallback 开关、HMAC 内部签名。
2. `contexts.identity.infrastructure.login_envelope`：RSA-OAEP 解密、AES-GCM 登录信封解密/响应加密。
3. `contexts.identity.api.auth_router`：新增 `/secure-login`，并在强制模式下禁用明文 `/login`。
4. `routers.secure`：解密后写入 nonce 去重，内部 ASGI 转发增加 HMAC header。
5. `middleware.auth_middleware`：拒绝裸 `x-secure-gateway`，只认可 HMAC 校验通过的内部请求。

前端包：

1. `frontend-client/src/services/authService.js`：优先走 secure-login。
2. `frontend-client/src/utils/crypto.js` 或新增 `loginEnvelope.js`：复用现有 node-forge 能力实现 RSA-OAEP + AES-GCM 信封。
3. 新增 pinned key 配置：`key_id`、public key PEM、fingerprint。
4. 保持 localStorage 兼容，Electron main process 安全存储作为后续第二阶段。

测试包：

1. 后端新增 secure-login、nonce、gateway HMAC、默认密钥治理测试。
2. 前端新增信封加密与 fingerprint 校验测试。
3. API contract 因新增 `/api/auth/secure-login` 与 `/api/auth/secure-refresh` 增加 2 条路由，并在 RES 中记录。

---

## 实施结果

本 SUG 第一阶段已经按 DEC-002 Level 1.5 落地，详见 RES-013。

当前验证：

```text
uv run pytest -q --disable-warnings -> exited 0
uv run pytest --collect-only -> 106 tests collected
API contract -> 126 routes
frontend-client production build -> success with existing warnings (RES-013 阶段验证)
```

说明：Level 1.5 的后端安全回归位于 `backend/tests/unit/test_security_level_1_5.py`；前端当前完成 secure-login 构建验证与公钥 fingerprint 校验，独立前端单测后续补齐。

---

## 采纳建议

建议将本 SUG 合并为 DEC-002 的安全加固子轨，放在 Identity 与 Operations 之间优先执行。

理由：

1. 该问题跨前端、Identity、secure gateway 和配置治理，不适合只作为某个小 bug 修复。
2. JWT 默认密钥和明文登录属于基础安全风险，优先级高于继续迁移 read-heavy 分析接口。
3. 本方案不改变 DEC-002 的架构方向，只是在 Identity/Platform/Operations 边界上补齐安全执行计划。
