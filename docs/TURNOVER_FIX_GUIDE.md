# 换手率修补功能使用指南

## 📋 功能说明

自动检测并修补换手率数据异常问题。当Excel文件中的换手率数据是小数形式（如 0.000989）而非百分比形式（如 9.89%）时，系统会自动检测并乘以 10000 进行修正。

### ✨ 核心特性

1. **自动检测**：导入时自动检测换手率异常
2. **自动修补**：检测到异常后自动修补（可配置）
3. **幂等性**：多次执行结果一致，不会重复修补
4. **可回滚**：支持撤销修补操作
5. **状态追踪**：所有修补操作都记录在状态文件中

## 🚀 使用方法

### 1. 自动修补（推荐）

**默认行为**：导入数据时自动检测和修补

```bash
# 正常导入，自动修补
python update_daily_data.py import
```

**导入日志示例**：
```
📂 正在导入: 20251117_data_sma_feature_color.xlsx
📊 读取到 5427 条记录
🔧 开始换手率数据检测...
⚠️  检测到换手率异常！平均值=0.000567, 中位数=0.000485
✅ 换手率已修补！影响行数=5427, 平均值: 0.000567 → 5.6700
```

### 2. 查看修补历史

```bash
# 查看所有修补记录
python update_daily_data.py fix --scan

# 只查看股票数据
python update_daily_data.py fix --scan --type stock
```

**输出示例**：
```
📊 股票数据修补历史：
======================================================================

📅 20251117:
   状态: ✅ 已修补
   倍数: 10000
   影响行数: 5427
   修补前平均: 0.000567
   修补后平均: 5.6700
   修补时间: 2025-11-17T18:30:15
```

### 3. 手动修补已导入的数据

适用场景：数据已经导入但未修补，或需要重新修补

```bash
# 预演模式（推荐先执行）
python update_daily_data.py fix --dates 20251117 --dry-run

# 执行修补
python update_daily_data.py fix --dates 20251117

# 修补多个日期
python update_daily_data.py fix --dates 20251117,20251116 --dry-run
python update_daily_data.py fix --dates 20251117,20251116
```

### 4. 回滚修补

撤销修补操作，恢复原始数据

```bash
# 预演回滚
python update_daily_data.py fix --rollback --dates 20251117 --dry-run

# 执行回滚
python update_daily_data.py fix --rollback --dates 20251117
```

## 🔧 配置管理

### 修补配置

配置存储在状态文件中：`data/data_import_state.json`

```json
{
  "fix_config": {
    "turnover_rate_fix": {
      "enabled": true,        // 是否启用修补
      "auto_fix": true,       // 是否自动修补
      "threshold": 0.01,      // 检测阈值（1%）
      "multiplier": 10000     // 修补倍数
    }
  }
}
```

### 禁用自动修补

**方法1**：编辑状态文件

```json
{
  "fix_config": {
    "turnover_rate_fix": {
      "enabled": false  // 禁用
    }
  }
}
```

**方法2**：导入后手动修补

```bash
# 1. 禁用自动修补（编辑配置文件）
# 2. 正常导入
python update_daily_data.py import

# 3. 需要时手动修补
python update_daily_data.py fix --dates 20251117
```

## 📊 检测逻辑

### 异常判断标准

系统认为换手率异常，当满足以下条件时：

1. **平均换手率 < 1%** (0.01)
2. **80% 以上的记录换手率 < 1%**

### 修补规则

- **触发条件**：检测到异常
- **修补方式**：乘以 10000
- **适用范围**：只修补低于阈值的记录（幂等性保证）

### 示例

```
原始数据：
- 股票A: 0.000989 → 异常
- 股票B: 0.000446 → 异常
- 股票C: 0.15     → 正常（不修补）

修补后：
- 股票A: 9.89     ✅
- 股票B: 4.46     ✅
- 股票C: 0.15     （保持不变）
```

## 🔄 幂等性保证

### 什么是幂等性？

多次执行相同操作，结果保持一致。

### 实现机制

1. **检测阈值**：只修补低于1%的换手率
2. **状态记录**：修补后记录在状态文件中
3. **跳过已修补**：检测到已修补的数据不再处理

### 验证

```bash
# 第一次修补
python update_daily_data.py fix --dates 20251117
# 输出：✅ 换手率已修补！影响行数=5427

# 第二次修补（幂等）
python update_daily_data.py fix --dates 20251117
# 输出：ℹ️  换手率数据正常，无需修补
```

## 🎯 典型工作流程

### 场景1：正常导入（自动修补）

```bash
# 1. 将Excel文件放入data目录
# 2. 执行导入（自动检测和修补）
python update_daily_data.py import

# 3. 查看修补历史
python update_daily_data.py fix --scan
```

### 场景2：修补错了需要回滚

```bash
# 1. 查看修补历史
python update_daily_data.py fix --scan

# 2. 预演回滚
python update_daily_data.py fix --rollback --dates 20251117 --dry-run

# 3. 执行回滚
python update_daily_data.py fix --rollback --dates 20251117
```

### 场景3：数据已导入但未修补

```bash
# 1. 检查数据状态
python update_daily_data.py fix --scan

# 2. 手动修补
python update_daily_data.py fix --dates 20251117
```

## 📝 状态文件示例

### 修补前

```json
{
  "imports": {
    "20251117": {
      "filename": "20251117_data_sma_feature_color.xlsx",
      "status": "success",
      "imported_count": 5427,
      "data_fixes": {}
    }
  }
}
```

### 修补后

```json
{
  "imports": {
    "20251117": {
      "filename": "20251117_data_sma_feature_color.xlsx",
      "status": "success",
      "imported_count": 5427,
      "data_fixes": {
        "turnover_rate_fix": {
          "applied": true,
          "fix_type": "multiply_by_multiplier",
          "multiplier": 10000,
          "affected_rows": 5427,
          "avg_before": 0.000567,
          "avg_after": 5.67,
          "detection_info": {
            "avg_turnover": 0.000567,
            "median_turnover": 0.000485,
            "threshold": 0.01,
            "is_anomaly": true
          },
          "fixed_at": "2025-11-17T18:30:15.123456"
        }
      }
    }
  },
  "fix_config": {
    "turnover_rate_fix": {
      "enabled": true,
      "auto_fix": true,
      "threshold": 0.01,
      "multiplier": 10000
    }
  }
}
```

## 🛠️ 故障排查

### 问题1：修补未生效

**症状**：执行修补命令后，数据库数据未变化

**可能原因**：
1. 数据不满足异常条件
2. 已经修补过（幂等性）

**解决**：
```bash
# 查看修补历史
python update_daily_data.py fix --scan

# 查看检测详情（开启DEBUG日志）
python update_daily_data.py fix --dates 20251117 --dry-run
```

### 问题2：修补错误需要回滚

**症状**：修补后数据不正确

**解决**：
```bash
# 1. 回滚修补
python update_daily_data.py fix --rollback --dates 20251117

# 2. 检查原因（可能需要调整配置）
# 3. 重新导入或修补
```

### 问题3：导入时没有自动修补

**可能原因**：修补功能被禁用

**解决**：
```bash
# 检查配置文件
cat data/data_import_state.json | grep "fix_config"

# 如果 enabled=false，改为 true
# 然后重新导入
```

## 🔍 高级用法

### 自定义修补倍数

编辑 `data/data_import_state.json`：

```json
{
  "fix_config": {
    "turnover_rate_fix": {
      "multiplier": 5000  // 改为 5000（默认10000）
    }
  }
}
```

### 调整检测阈值

```json
{
  "fix_config": {
    "turnover_rate_fix": {
      "threshold": 0.005  // 改为 0.5%（默认1%）
    }
  }
}
```

## 📚 相关命令

```bash
# 查看所有可用命令
python update_daily_data.py --help

# 查看fix命令帮助
python update_daily_data.py fix --help

# 导入数据
python update_daily_data.py import

# 删除数据
python update_daily_data.py delete --dates 20251117

# 清理孤儿数据
python update_daily_data.py clean
```

## ⚠️ 注意事项

1. **备份重要**：修补前确保有数据备份
2. **先预演**：执行修补前先用 `--dry-run` 预演
3. **检查结果**：修补后验证数据正确性
4. **幂等性**：可以安全地多次执行修补命令
5. **可回滚**：如有问题可以回滚修补
6. **向前兼容**：老版本会忽略新增的字段
7. **板块数据**：目前只支持股票数据，板块数据暂不支持

## 🎉 最佳实践

1. **定期检查**：定期查看修补历史
2. **自动修补**：保持自动修补功能开启
3. **数据验证**：导入后抽查几条数据验证
4. **记录保留**：保留修补日志以便审计
5. **配置版控**：将配置文件纳入版本控制
