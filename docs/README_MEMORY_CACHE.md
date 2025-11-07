# 全量内存缓存方案

## 🎯 设计目标

启动时一次性将所有数据加载到内存，后续所有操作都走内存，**零数据库查询**。

---

## 📁 文件说明

| 文件 | 说明 |
|------|------|
| `app/services/memory_cache.py` | 全量内存缓存管理器（单例模式） |
| `test_memory_usage.py` | 内存占用测试脚本 |

---

## 🧪 测试内存占用

### 1. 安装依赖

```bash
pip install psutil
```

### 2. 运行测试

```bash
cd backend
python test_memory_usage.py
```

### 3. 查看结果

测试脚本会输出：
- ✅ 初始内存使用
- ✅ 数据加载后内存使用
- ✅ 数据占用内存（增量）
- ✅ 数据统计（股票数、记录数等）
- ✅ 性能测试（查询速度）
- ✅ 建议（是否适合全量缓存）

---

## 📊 内存占用估算

### 数据结构

```python
class MemoryCacheManager:
    self.stocks: Dict[str, Stock]                    # ~10KB（5000股票）
    self.daily_data_by_date: Dict[date, List[...]]  # 主要占用
    self.daily_data_by_stock: Dict[str, Dict[...]]  # 主要占用
    self.dates: List[date]                           # ~1KB（100天）
```

### 每条记录占用（估算）

假设每个 `DailyStockData` 对象包含：
- 83个数值字段（Decimal/Integer/BigInteger）
- 每个字段 ~8-16 bytes
- Python对象开销 ~40 bytes

**估算：** 每条记录 ~1KB

### 总占用计算

```
数据记录数 × 1KB = 总内存占用

示例：
- 20,000 条记录 ≈ 20MB
- 100,000 条记录 ≈ 100MB
- 500,000 条记录 ≈ 500MB
```

---

## 💡 使用建议

### ✅ 适合场景

| 数据量 | 内存占用 | 建议 |
|--------|----------|------|
| < 50万条 | < 500MB | ✅ 推荐全量缓存 |
| 50-100万条 | 500MB-1GB | ⚠️ 可以，但需2GB+内存 |
| > 100万条 | > 1GB | ❌ 考虑分页或懒加载 |

### 📈 性能对比

| 操作 | 数据库查询 | 内存缓存 | 提升 |
|------|-----------|----------|------|
| 获取日期列表 | ~10ms | < 1ms | **10x** |
| TOP 100股票 | ~50ms | < 1ms | **50x** |
| 股票历史 | ~100ms | < 1ms | **100x** |
| 周期分析 | ~500ms | < 10ms | **50x** |

---

## 🔧 集成到应用

### 方案1：修改 startup.py（推荐）

```python
# app/core/startup.py
from ..services.memory_cache import memory_cache

def preload_cache():
    """加载全量数据到内存"""
    memory_cache.load_all_data()
```

### 方案2：创建新的服务类

创建 `analysis_service_memory.py`，基于 `memory_cache` 重写所有服务。

---

## 🎯 数据结构设计

### 1. 按日期索引（快速获取某天所有数据）

```python
self.daily_data_by_date: Dict[date, List[DailyStockData]]

# 查询示例
data_20251106 = memory_cache.get_daily_data_by_date(date(2025, 11, 6))
```

### 2. 按股票+日期索引（快速获取股票历史）

```python
self.daily_data_by_stock: Dict[str, Dict[date, DailyStockData]]

# 查询示例
stock_data = memory_cache.get_daily_data_by_stock("000657", date(2025, 11, 6))
```

### 3. 日期列表（快速获取日期范围）

```python
self.dates: List[date]  # 降序，最新在前

# 查询示例
latest_10_days = memory_cache.get_dates_range(10)
```

---

## ⚡ 性能优化

### 1. 预排序

所有日期的数据在加载时已按 `rank` 排序，查询TOP N无需再排序。

### 2. 双索引

同时维护按日期和按股票的索引，支持两种查询模式。

### 3. 单例模式

全局只有一个实例，避免重复加载。

---

## 🔄 数据更新策略

### 选项1：重启应用

```bash
# 导入新数据后
python clear_cache.py
python -m uvicorn app.main:app --reload
```

### 选项2：热更新（需添加API）

```python
@app.post("/admin/reload")
def reload_data():
    memory_cache.load_all_data()
    return {"status": "reloaded"}
```

---

## 🐛 故障排查

### 问题1：内存不足

**症状：** `MemoryError` 或系统变慢

**解决：**
1. 检查数据量：`python test_memory_usage.py`
2. 增加服务器内存
3. 或改用懒加载

### 问题2：加载太慢

**症状：** 启动时卡很久

**原因：** 数据库查询慢

**解决：**
1. 检查数据库索引
2. 优化SQL查询
3. 使用SSD硬盘

### 问题3：数据不更新

**症状：** 导入新数据后前端没变化

**原因：** 内存缓存未刷新

**解决：** 重启应用或调用reload API

---

## 📝 对比分析

### 当前方案（数据库+缓存）

**优点：**
- ✅ 内存占用小
- ✅ 数据更新方便

**缺点：**
- ❌ 启动时预加载卡顿（18个并发查询）
- ❌ 首次访问慢（需查DB）
- ❌ 高并发时DB压力大

### 全量内存缓存

**优点：**
- ✅ 启动后瞬间响应（< 1ms）
- ✅ 零数据库压力
- ✅ 并发性能极佳

**缺点：**
- ❌ 内存占用大（~500MB）
- ❌ 数据更新需重启
- ❌ 单机扩展受限

---

## 🎉 总结

### 推荐方案

**如果你的数据量 < 50万条：**
- ✅ **使用全量内存缓存**
- 启动加载一次，后续飞快
- 内存占用可接受（< 500MB）

**如果你的数据量 > 100万条：**
- ❌ 不推荐全量缓存
- 考虑分页或按需加载
- 或使用Redis等外部缓存

---

## 📞 测试步骤

```bash
# 1. 测试内存占用
cd backend
python test_memory_usage.py

# 2. 查看输出
# 记录"数据占用"这一项

# 3. 决策
# < 500MB → 可以用
# > 500MB → 需要考虑
```

---

**💬 根据测试结果决定是否采用全量内存缓存！**
