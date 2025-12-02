# BUG修复 - 原版排序优先级未生效

**日期**: 2025-11-11 14:15  
**严重性**: 中等  
**状态**: ✅ 已修复

---

## 🐛 问题描述

用户选择**"最新热点TOP信号（原版）"**后，期望按**信号数量**优先排序（多信号共振），但实际仍按**信号强度**优先排序。

### 复现步骤
1. 打开配置面板
2. 选择"最新热点TOP信号（原版）"
3. 查看板块详情页面的TOP 10成分股
4. 发现排序仍然是按信号强度，而不是信号数量

### 期望行为
- **原版（v1）**: 优先按信号数量排序（3个信号 > 2个信号 > 1个信号）
- **新版（v2）**: 优先按信号强度排序（50% > 40% > 30%）

### 实际行为
- 无论选择哪个版本，都按信号强度排序

---

## 🔍 根本原因

在`industry_detail_service.py`的`_sort_stocks`方法中，`sort_mode="signal"`时，排序逻辑是**硬编码**的，始终优先按信号强度排序：

```python
elif sort_mode == "signal":
    # 硬编码：强度 > 数量
    return sorted(stocks, key=lambda x: (
        -x.signal_strength,  # 第1优先级：信号强度
        -x.signal_count,     # 第2优先级：信号数量
        x.rank
    ))
```

**问题**: 没有根据`hot_list_version`参数动态调整排序优先级。

---

## ✅ 修复方案

### 1. 传递`signal_thresholds`参数

**修改位置**: `industry_detail_service.py` 第161行

```python
# 修改前
stocks_list = self._sort_stocks(stocks_list, sort_mode)

# 修改后
stocks_list = self._sort_stocks(stocks_list, sort_mode, signal_thresholds)
```

### 2. 更新`_sort_stocks`方法签名

**修改位置**: `industry_detail_service.py` 第181行

```python
# 修改前
def _sort_stocks(self, stocks: List[StockSignalInfo], sort_mode: str) -> List[StockSignalInfo]:

# 修改后
def _sort_stocks(
    self, 
    stocks: List[StockSignalInfo], 
    sort_mode: str, 
    signal_thresholds: Optional[SignalThresholds] = None
) -> List[StockSignalInfo]:
```

### 3. 根据版本动态调整排序逻辑

**修改位置**: `industry_detail_service.py` 第205-222行

```python
elif sort_mode == "signal":
    # 根据版本决定排序优先级
    if signal_thresholds and signal_thresholds.hot_list_version == "v1":
        # 原版：数量 > 强度 > 排名（多信号共振）
        return sorted(stocks, key=lambda x: (
            -x.signal_count,     # 第1优先级：信号数量
            -x.signal_strength,  # 第2优先级：信号强度
            x.rank               # 第3优先级：原始排名
        ))
    else:
        # 新版（默认）：强度 > 数量 > 排名（质量优先）
        return sorted(stocks, key=lambda x: (
            -x.signal_strength,  # 第1优先级：信号强度
            -x.signal_count,     # 第2优先级：信号数量
            x.rank               # 第3优先级：原始排名
        ))
```

---

## 🎯 修复效果

### 原版（v1）排序示例

**修复前**（按强度排序）:
```
#1 粤桂股份  1个信号  40%  ❌ 强度高但信号少
#2 云南能投  1个信号  38%
#3 常山北明  2个信号  37%  ✅ 信号多但排后面
```

**修复后**（按数量排序）:
```
#1 常山北明  2个信号  37%  ✅ 信号多排前面
#2 粤桂股份  1个信号  40%
#3 云南能投  1个信号  38%
```

### 新版（v2）排序示例

保持不变，仍然按强度优先：
```
#1 粤桂股份  1个信号  40%
#2 云南能投  1个信号  38%
#3 常山北明  2个信号  37%
```

---

## 📊 对比总结

| 版本 | 排序优先级 | 适用场景 | 修复前 | 修复后 |
|-----|-----------|---------|-------|-------|
| **原版v1** | 数量 > 强度 | 多信号共振 | ❌ 按强度 | ✅ 按数量 |
| **新版v2** | 强度 > 数量 | 质量优先 | ✅ 按强度 | ✅ 按强度 |

---

## ✅ 测试验证

### 测试步骤
1. 重启后端服务
2. 打开配置面板，选择"最新热点TOP信号（原版）"
3. 查看板块详情，确认按信号数量排序
4. 切换到"最新热点TOP信号（新版）"
5. 确认按信号强度排序

### 预期结果
- ✅ 原版：3个信号的股票排在1个信号的股票前面（即使强度略低）
- ✅ 新版：40%强度的股票排在37%强度的股票前面（即使信号少）

---

## 📝 相关文档

- `v0.3.1-三种信号模式切换.md` - 完整功能说明
- `v0.3.0-档位倍数和排序优化.md` - 档位倍数调整

---

**修复人员**: AI Assistant  
**修复日期**: 2025-11-11 14:15  
**影响范围**: 板块详情页面的股票排序
