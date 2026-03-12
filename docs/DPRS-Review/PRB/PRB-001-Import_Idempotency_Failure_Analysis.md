# PRB-001: Import Idempotency Failure Analysis

**Date**: 2026-02-09
**Status**: [RESOLVED]
**Component**: Data Import & State Management
**Related**: `import_data_robust.py`, `data_fixer.py`

---

## 1. Description (Problem)

**Symptom**:
The data import script (`import_data_robust.py`) repeatedly re-imports data for the same date (e.g., `2026-02-06`) even after a successful completion. The expected behavior is to skip already imported files based on the state file (`import_state.json`), ensuring idempotency.

**Observation**:
1.  Run 1: Import completes successfully. Logs show `✅ 导入成功` and `✅ 修补信息已记录`.
2.  Run 2: Script detects `5455` old records, cleans them up, and re-imports. It does **not** log `[跳过] 文件（已成功导入）`.
3.  This indicates that `state_manager.should_reimport` is returning `True`, meaning the status in `import_state.json` is **not** "success".

---

## 2. Root Cause Analysis (RCA)

**The "Stale State Overwrite" Race Condition**:

1.  **Init (`import_data_robust.py`)**:
    *   `state_manager` (Main) is initialized.
    *   It marks the task as `in_progress` in memory and executes `_save_state()`.

2.  **Fixer Init (`import_excel_file` loop)**:
    *   `turnover_fixer = TurnoverRateFixer(date_str)` is created.
    *   **CRITICAL**: `TurnoverRateFixer.__init__` created its **own independent** `self.state_manager = ImportStateManager()`.
    *   This new instance read the current state from disk -> Status was `in_progress`.

3.  **Import Success (`import_excel_file` end)**:
    *   Main `state_manager` called `mark_success(...)`.
    *   It updated the state in memory to `success` and saved to disk.
    *   **Disk State**: `success`.

4.  **Fix Recording (`import_excel_file` post-success)**:
    *   Script called `turnover_fixer.record_fix_to_state(info)`.
    *   `TurnoverRateFixer` used its **internal (stale)** `state_manager`.
    *   It updated `data_fixes` on its memory copy (where Status is still `in_progress`).
    *   It called `self.state_manager.save()`.
    *   **Disk State**: Overwritten with `in_progress`.

**Result**:
The Next Run reads the state file, sees `in_progress` (or a non-success state), and correctly decides to re-import.

---

## 3. Resolution

**Fix Implemented**:
1.  **Dependency Injection**: Modified `TurnoverRateFixer` (`data_fixer.py`) to accept an external `state_manager` instance.
2.  **Pass Singleton**: Updated `import_data_robust.py` to pass the global `state_manager` to `TurnoverRateFixer`.

```python
# data_fixer.py
def __init__(self, date_str, state_manager=None):
    if state_manager:
        self.state_manager = state_manager
    else:
        self.state_manager = ImportStateManager(...)

# import_data_robust.py
turnover_fixer = TurnoverRateFixer(date_str, state_manager=state_manager)
```

**Verification**:
1.  **Run 1**: Successfully imported `2026-02-06`. Logs confirmed success.
2.  **Run 2**: Script correctly detected "success" status and logged `[跳过] 文件（已成功导入）`.
3.  **Idempotency Restored**.
