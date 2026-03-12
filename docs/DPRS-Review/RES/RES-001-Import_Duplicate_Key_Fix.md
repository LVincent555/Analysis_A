# RES-002: Import Duplicate Key Fix (导入主键冲突修复)

**Version**: 1.0  
**Status**: ✅ **Implemented**  
**Date**: 2026-02-09  
**Related**: `import_data_robust.py`

---

## 1. 问题描述 (Problem)

在执行数据导入脚本 `import_data_robust.py` 时，当尝试重新导入某一天的 Excel 数据（如 `2026-02-06`），如果该数据已经部分存在于数据库中（但状态文件 `import_state.json` 丢失或记录不一致），会触发 **Unique Constraint Violation** (唯一性约束冲突)。

**错误日志**:
```
psycopg2.errors.UniqueViolation: duplicate key value violates unique constraint "idx_daily_stock_date_unique"
DETAIL: Key (stock_code, date)=(603069, 2026-01-30) already exists.
```

**原逻辑缺陷**:
脚本仅在 `status` 明确标记为 `deleted` 或 `rolled_back` 时才清理旧数据。对于"成功但需重跑"的情况（如手动删除状态文件），脚本未执行清理直接插入，导致主键冲突。

---

## 2. 解决方案 (Solution)

**强制幂等性 (Enforced Idempotency)**：
修改 `import_data_robust.py`，**移除条件判断，改为无条件清理**。
在导入任何文件之前，只要检测到数据库中存在该日期的记录，必须先执行 `DELETE`。

**代码变更**:
```python
# Before
if import_info.get("status") in ["deleted", "rolled_back"]:
    # conditionally delete ...

# After (Fix)
if True:  # Unconditional Check
    old_count = db_session.query(...).filter(...).scalar()
    if old_count > 0:
        logger.info(f"🔄 检测到 {old_count} 条旧数据，正在清理以确保幂等性...")
        db_session.query(...).delete()
        db_session.flush() # Ensure deletion is staged
```

---

## 3. 验证结果 (Verification)

1.  **执行操作**: 重新运行修复后的 `import_data_robust.py`。
2.  **观察结果**:
    *   日志显示：`✅ 已清理旧数据` (2026-02-06)。
    *   导入过程：成功导入 5455 条记录。
    *   最终状态：`✅ 导入任务完成！` (成功=68)。
3.  **结论**: 修复有效，脚本现在具备完全的幂等性，可安全重复运行。

---

## 4. 后续建议

*   在 `import_state_manager.py` 中增加对数据库实际状态的校验。
*   定期（每周）执行数据完整性检查脚本，确保 `DailyStockData` 无重复坏数。
