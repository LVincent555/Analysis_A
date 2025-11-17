# 数据删除功能使用指南

## 📋 功能说明

新增 `delete` 命令用于**主动删除**指定日期的数据，适用于以下场景：
- ✅ 数据源有问题（如今天的Excel文件数据错误）
- ✅ 需要重新导入某个日期的数据
- ✅ 强制删除任何状态的数据（包括 success、warning、rolled_back 等）

## 🚀 使用方法

### 1. 预演模式（推荐先执行）

查看将要删除什么数据，不会真正删除：

```bash
# 删除单个日期（股票+板块）
python update_daily_data.py delete --dates 20251117 --dry-run

# 删除多个日期
python update_daily_data.py delete --dates 20251117,20251116 --dry-run

# 只删除股票数据
python update_daily_data.py delete --dates 20251117 --type stock --dry-run

# 只删除板块数据
python update_daily_data.py delete --dates 20251117 --type sector --dry-run
```

### 2. 执行删除

**⚠️ 警告：此操作不可逆！**

```bash
# 删除单个日期
python update_daily_data.py delete --dates 20251117

# 删除多个日期
python update_daily_data.py delete --dates 20251117,20251116

# 只删除股票数据
python update_daily_data.py delete --dates 20251117 --type stock

# 只删除板块数据
python update_daily_data.py delete --dates 20251117 --type sector
```

### 3. 安全确认机制

执行删除时会要求确认：

**删除单个日期：**
```
确认删除？输入日期以确认 (或输入 no 取消): 20251117
```
- 必须输入完整的日期（如 `20251117`）才能确认
- 输入 `no` 或 `n` 取消操作

**删除多个日期：**
```
确认删除？输入日期以确认 (或输入 no 取消): yes
```
- 输入 `yes` 或 `y` 确认
- 输入 `no` 或 `n` 取消操作

## 📊 完整工作流程

### 场景：今天的数据有问题，需要重新导入

```bash
# 1. 预演删除，查看影响范围
python update_daily_data.py delete --dates 20251117 --dry-run

# 2. 确认无误后，执行删除
python update_daily_data.py delete --dates 20251117
# 输入日期确认: 20251117

# 3. 将正确的Excel文件放入 data/ 目录
# - 20251117_data_sma_feature_color.xlsx
# - 20251117_sector_data_sma_feature_color.xlsx

# 4. 重新导入数据
python update_daily_data.py import
```

## 🔍 与 clean 命令的区别

| 功能 | clean | delete |
|------|-------|--------|
| **用途** | 清理孤儿数据（warning状态） | 主动删除指定日期 |
| **触发条件** | 自动检测warning状态 | 手动指定日期 |
| **删除范围** | 只删除有问题的数据 | 删除所有指定日期的数据 |
| **状态要求** | 必须是warning状态 | 无状态要求（强制删除） |
| **使用场景** | 文件缺失、文件变更、导入失败残留 | 数据源错误、需要重新导入 |

## 📝 命令参数说明

### delete 命令

```bash
python update_daily_data.py delete [OPTIONS]
```

**必需参数：**
- `--dates DATES`: 要删除的日期，格式 YYYYMMDD
  - 单个日期：`--dates 20251117`
  - 多个日期：`--dates 20251117,20251116,20251115`

**可选参数：**
- `--dry-run`: 预演模式，不真正删除数据
- `--type {stock,sector,all}`: 数据类型，默认 `all`
  - `stock`: 只删除股票数据
  - `sector`: 只删除板块数据
  - `all`: 删除股票和板块数据

## ⚠️ 注意事项

1. **数据不可恢复**：删除后只能通过重新导入Excel文件恢复
2. **先预演后执行**：建议先用 `--dry-run` 查看影响范围
3. **备份重要数据**：删除前确保有Excel文件备份
4. **确认日期正确**：仔细检查要删除的日期
5. **状态会更新**：删除后导入状态会标记为 `deleted`

## 🛠️ 故障排查

### 问题：删除后无法重新导入

**原因**：导入状态仍然是 `deleted`

**解决**：
```bash
# 方法1：使用 --force 参数（如果支持）
python update_daily_data.py import --force

# 方法2：手动清理状态文件
# 编辑 data/data_import_state.json 或 data/sector_import_state.json
# 删除对应日期的记录
```

### 问题：删除失败

**可能原因**：
1. 数据库连接失败
2. 日期格式错误（必须是 YYYYMMDD）
3. 权限不足

**解决**：
- 检查数据库连接
- 确认日期格式正确
- 查看日志文件：`logs/update_data_*.log`

## 📚 相关命令

```bash
# 查看所有可用命令
python update_daily_data.py --help

# 查看 delete 命令帮助
python update_daily_data.py delete --help

# 扫描文件完整性
python update_daily_data.py scan

# 查看警告数据
python update_daily_data.py clean --scan

# 清理孤儿数据
python update_daily_data.py clean --dry-run
python update_daily_data.py clean
```

## 💡 最佳实践

1. **定期备份**：定期备份 `data/` 目录下的Excel文件
2. **先预演**：执行删除前先用 `--dry-run` 预演
3. **记录日志**：保存操作日志以便追溯
4. **小批量操作**：一次删除少量日期，避免大范围影响
5. **验证数据**：重新导入后验证数据正确性
