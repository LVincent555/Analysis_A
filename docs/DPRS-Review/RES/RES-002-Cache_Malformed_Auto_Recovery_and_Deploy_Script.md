# RES-002: Cache "database disk image is malformed" 修复与一键部署加固

**Version**: 1.0
**Status**: ✅ **Implemented**
**Date**: 2026-03-12
**Related**: `admin.py`, `store.py`, `一键部署.sh`

---

## 1. 问题描述 (Problem)

服务器导入完成后，日志出现：

```text
⚠️ 缓存重载失败: database disk image is malformed
```

表现特征：

- Numpy 一级缓存加载成功；
- 热点榜预加载成功；
- 在管理员导入后的缓存重载阶段抛出 diskcache/SQLite 损坏异常；
- 业务接口仍可用，但导入日志持续告警。

---

## 2. 根因分析 (Root Cause)

统一缓存系统的 L2 磁盘缓存由 `diskcache` 驱动，底层是 SQLite：

- 位置：`backend/app/.cache/api/cache.db` 与 `backend/app/.cache/reports/cache.db`
- 当 `cache.db` 文件损坏时，`cache.clear_api_cache()` 或 `manager.api().clear()` 会触发
  `database disk image is malformed`。

导入流程中先执行 `preload_cache()`，再做清理，且未对损坏缓存做自动恢复，导致该异常暴露到导入日志。

---

## 3. 修复方案 (Fix)

### A. 运行期自动恢复（代码级）

在 `backend/app/core/caching/store.py` 的 `FileStore` 增加：

1. 损坏特征识别：
   - `database disk image is malformed`
   - `file is not a database`
   - `malformed database schema`
2. 自动重建：检测损坏后，关闭 cache、删除缓存目录、重建目录并重试一次。
3. 覆盖操作：`get / set / delete / clear / stats` 全部接入恢复逻辑。

### B. 管理端缓存重载顺序优化

在 `backend/app/routers/admin.py` 三处重载逻辑统一调整为：

1. `cache.clear_api_cache()`
2. `HotSpotsCache.clear_cache()`
3. `preload_cache()`

即先清旧缓存，再预热新缓存，避免“先预热后清空”。

### C. 一键部署脚本加固（运维级）

在 `一键部署.sh` 新增磁盘缓存重建步骤：

- 备份旧 `cache.db` 到部署备份目录；
- 删除并重建 `backend/app/.cache/api` 与 `backend/app/.cache/reports`。

该步骤可在每次部署时主动清理潜在损坏缓存，降低线上复发概率。

---

## 4. 验证结果 (Verification)

验证口径：

1. 执行导入并触发缓存重载；
2. 观察导入日志不再出现 `database disk image is malformed`；
3. `GET /admin/import-status`、`GET /api/dates` 等接口正常；
4. 服务重启后可正常完成缓存预热。

---

## 5. 后续建议

- 保留当前自动恢复机制，避免单点损坏放大；
- 每次部署继续使用 `一键部署.sh`（一键清理 + 一键启动）；
- 如后续仍出现同类损坏，增加磁盘健康与 inode/IO 错误巡检。
