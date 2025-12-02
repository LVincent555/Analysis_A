# Numpy 缓存中间件设计方案

> 版本: v1.1
> 日期: 2024-12-02
> 状态: 设计中
> 更新: 加入关键技术规范和二级缓存架构

---

## 一、现状分析

### 1.1 当前缓存架构

```
┌─────────────────────────────────────────────────────────────────┐
│                         Service Layer                            │
├──────────────┬──────────────┬──────────────┬───────────────────┤
│ analysis     │ stock        │ industry     │ rank_jump         │
│ service_db   │ service_db   │ detail_svc   │ service_db        │
│              │              │              │ steady_rise_svc   │
├──────────────┴──────────────┴──────────────┼───────────────────┤
│     MemoryCacheManager (Python ORM对象)     │   直接查询DB      │
│     ↓ 同时存储 ↓                            │                   │
│     NumpyStockCache (几乎未使用)            │                   │
└─────────────────────────────────────────────┴───────────────────┤
                              ↓                         ↓
                    ┌─────────────────────────────────────────────┐
                    │              PostgreSQL                      │
                    └─────────────────────────────────────────────┘
```

### 1.2 内存占用问题

| 缓存 | 存储内容 | 数据量 | 估算内存 |
|------|----------|--------|----------|
| `MemoryCacheManager.daily_data_by_date` | Python ORM对象 | 15万条 | ~200MB |
| `MemoryCacheManager.daily_data_by_stock` | Python ORM对象 | 15万条 | 同上(引用) |
| `NumpyStockCache.data_array` | Numpy数组 | 15万条 | ~8MB |
| `HotSpotsCache._cache` | Python字典 | ~3万条 | ~50MB |
| **合计** | | | **~260MB** |

**问题**: 数据被重复存储在 Python ORM 对象和 Numpy 数组中，但 Numpy 数组几乎未被使用。

### 1.3 数据库直接查询服务

以下服务仍直接查询数据库，未使用缓存：

| 服务 | 查询操作 | 频率 |
|------|----------|------|
| `rank_jump_service_db.py` | 最近2天数据JOIN查询 | 高 |
| `steady_rise_service_db.py` | 最近N天数据JOIN查询 | 高 |

---

## 二、目标架构

### 2.1 新架构设计

```
┌─────────────────────────────────────────────────────────────────┐
│                         Service Layer                            │
│  (analysis / stock / industry / rank_jump / steady_rise / ...)  │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│                    NumpyCacheMiddleware                          │
│            (统一缓存中间件 - 类Redis架构)                         │
├─────────────────────────────────────────────────────────────────┤
│  ┌──────────────┐  ┌──────────────┐  ┌────────────────────────┐ │
│  │ StockStore   │  │ DailyStore   │  │ SectorStore            │ │
│  │ (股票基础)    │  │ (每日数据)    │  │ (板块数据)              │ │
│  │ Python Dict  │  │ Numpy Array  │  │ Numpy Array            │ │
│  └──────────────┘  └──────────────┘  └────────────────────────┘ │
├─────────────────────────────────────────────────────────────────┤
│  索引层: stock_code_idx / date_idx / composite_idx              │
├─────────────────────────────────────────────────────────────────┤
│  查询接口: get() / get_batch() / get_by_date() / get_top_n()   │
└─────────────────────────────────────────────────────────────────┘
                              ↓ (启动时加载)
┌─────────────────────────────────────────────────────────────────┐
│                        PostgreSQL                                │
└─────────────────────────────────────────────────────────────────┘
```

### 2.2 内存优化目标

| 缓存 | 迁移前 | 迁移后 | 节省 |
|------|--------|--------|------|
| 股票每日数据 | ~200MB | ~12MB | 94% |
| 板块每日数据 | ~30MB | ~2MB | 93% |
| 股票基础信息 | ~5MB | ~5MB | - |
| 热点榜缓存 | ~50MB | ~10MB | 80% |
| **合计** | ~285MB | **~29MB** | **90%** |

---

## 三、Numpy 存储结构设计

### 3.1 股票每日数据 (DailyDataStore)

> ⚠️ **关键技术规范**

```python
# 核心字段 - 高频查询 (72字节/条)
# 
# 🔴 精度规范：
#   - 价格/金额/总分 → np.float64 (双精度，避免0.01误差导致排名错误)
#   - 其他指标(RSI/KDJ等) → np.float32 节省空间
# 
# 🔴 空值处理：
#   - Numpy int类型不支持NaN
#   - rank/volume有空值时必须填充默认值 (-1 或 0)
# 
# 🔴 字符串处理：
#   - 绝对禁止在Numpy数组中存储字符串
#   - 只存 stock_idx (int32)，通过IndexManager反查stock_code
#
core_dtype = np.dtype([
    ('stock_idx', np.int32),       # 4B - 股票索引 (非stock_code字符串!)
    ('date_idx', np.int32),        # 4B - 日期索引  
    ('rank', np.int32),            # 4B - 排名 (空值填-1)
    ('total_score', np.float64),   # 8B - 总分 ⚠️必须float64
    ('price_change', np.float64),  # 8B - 涨跌幅 ⚠️必须float64
    ('turnover_rate', np.float32), # 4B - 换手率
    ('volume', np.int64),          # 8B - 成交量 (空值填0)
    ('volatility', np.float32),    # 4B - 波动率
    ('close_price', np.float64),   # 8B - 收盘价 ⚠️必须float64
    ('open_price', np.float64),    # 8B - 开盘价 ⚠️必须float64
    ('high_price', np.float64),    # 8B - 最高价 ⚠️必须float64
    ('low_price', np.float64),     # 8B - 最低价 ⚠️必须float64
    ('market_cap', np.float64),    # 8B - 总市值 ⚠️必须float64
])  # 共72字节/条，15万条≈10.3MB

# 扩展字段 - 低频查询，按需加载 (约200字节/条)
extended_dtype = np.dtype([
    ('stock_idx', np.int32),
    ('date_idx', np.int32),
    # MACD相关
    ('macd_signal', np.float32),
    ('dif', np.float32),
    ('dem', np.float32),
    ('histgram', np.float32),
    ('macd_consec', np.int16),
    # KDJ相关
    ('slowkdj_signal', np.float32),
    ('slowk', np.float32),
    ('k_kdj', np.float32),
    # RSI/CCI
    ('rsi', np.float32),
    ('cci_neg_90', np.float32),
    ('cci_pos_90', np.float32),
    # BOLL
    ('lower_band', np.float32),
    ('middle_band', np.float32),
    ('upper_band', np.float32),
    # DMI
    ('adx', np.float32),
    ('plus_di', np.float32),
    # ... 其他80+字段
])
```

### 3.2 板块每日数据 (SectorDataStore)

```python
sector_dtype = np.dtype([
    ('sector_idx', np.int32),      # 4B - 板块索引
    ('date_idx', np.int32),        # 4B - 日期索引
    ('rank', np.int32),            # 4B - 排名
    ('total_score', np.float32),   # 4B - 总分
    ('price_change', np.float32),  # 4B - 涨跌幅
    ('turnover_rate', np.float32), # 4B - 换手率
    ('volume', np.int64),          # 8B - 成交量
    ('volatility', np.float32),    # 4B - 波动率
    ('close_price', np.float32),   # 4B - 收盘价
])  # 40字节/条
```

### 3.3 索引结构设计

```python
class IndexManager:
    """高性能索引管理器"""
    
    # 股票代码映射
    stock_code_to_idx: Dict[str, int]    # {'600000': 0, '000001': 1, ...}
    idx_to_stock_code: np.ndarray        # ['600000', '000001', ...]
    
    # 日期映射
    date_to_idx: Dict[date, int]         # {date(2024,11,27): 0, ...}
    idx_to_date: np.ndarray              # [date(...), date(...), ...]
    
    # 复合索引 (股票+日期) -> 行号 (O(1)查询)
    composite_idx: Dict[Tuple[int, int], int]  # {(stock_idx, date_idx): row_idx}
    
    # 日期分组索引 (某日期的所有数据起止行号)
    date_range_idx: Dict[int, Tuple[int, int]]  # {date_idx: (start_row, end_row)}
```

---

## 四、中间件接口设计

### 4.1 核心接口

```python
class NumpyCacheMiddleware:
    """Numpy缓存中间件 - 统一数据访问层"""
    
    # ========== 初始化与生命周期 ==========
    def load_from_db(self, days: int = 30) -> None:
        """从数据库加载数据到缓存"""
        
    def clear(self) -> None:
        """清空所有缓存"""
        
    def reload(self) -> None:
        """重新加载数据"""
    
    # ========== 股票基础信息查询 ==========
    def get_stock_info(self, stock_code: str) -> Optional[StockInfo]:
        """获取股票基础信息"""
        
    def get_all_stocks(self) -> Dict[str, StockInfo]:
        """获取所有股票"""
        
    def search_stocks(self, keyword: str, limit: int = 10) -> List[StockInfo]:
        """搜索股票（代码/名称模糊匹配）"""
    
    # ========== 每日数据查询（核心字段）==========
    def get_daily_data(
        self, 
        stock_code: str, 
        target_date: date
    ) -> Optional[DailyDataDict]:
        """获取单只股票单日数据"""
        
    def get_daily_data_batch(
        self, 
        stock_codes: List[str], 
        target_date: date
    ) -> Dict[str, DailyDataDict]:
        """批量获取多只股票单日数据"""
        
    def get_stock_history(
        self, 
        stock_code: str, 
        days: int = 30
    ) -> List[DailyDataDict]:
        """获取单只股票历史数据"""
        
    def get_top_n_by_rank(
        self, 
        target_date: date, 
        n: int = 100
    ) -> List[DailyDataDict]:
        """获取某日期排名前N的股票"""
        
    def get_all_by_date(
        self, 
        target_date: date
    ) -> List[DailyDataDict]:
        """获取某日期的所有数据"""
    
    # ========== 扩展字段查询（按需）==========
    def get_full_indicators(
        self, 
        stock_code: str, 
        target_date: date
    ) -> Optional[FullIndicatorsDict]:
        """获取完整的83个技术指标（低频查询）"""
    
    # ========== 聚合计算 ==========
    def get_market_volatility_summary(self, days: int = 3) -> Dict:
        """全市场波动率汇总"""
        
    def get_rank_statistics(self, target_date: date) -> Dict:
        """排名统计信息"""
    
    # ========== 板块数据查询 ==========
    def get_sector_info(self, sector_id: int) -> Optional[SectorInfo]:
        """获取板块基础信息"""
        
    def get_sector_daily_data(
        self, 
        sector_id: int, 
        target_date: date
    ) -> Optional[SectorDataDict]:
        """获取板块单日数据"""
        
    def get_top_n_sectors(
        self, 
        target_date: date, 
        n: int = 100
    ) -> List[SectorDataDict]:
        """获取某日期排名前N的板块"""
    
    # ========== 日期查询 ==========
    def get_available_dates(self) -> List[str]:
        """获取所有可用日期（字符串格式）"""
        
    def get_latest_date(self) -> Optional[date]:
        """获取最新日期"""
        
    def get_dates_range(self, n: int) -> List[date]:
        """获取最近N天日期"""
    
    # ========== 状态查询 ==========
    def get_memory_stats(self) -> Dict:
        """获取内存使用统计"""
        
    def is_loaded(self) -> bool:
        """检查缓存是否已加载"""
```

### 4.2 返回数据类型

```python
from typing import TypedDict

class DailyDataDict(TypedDict):
    """每日数据字典（核心字段）"""
    stock_code: str
    date: str  # YYYYMMDD
    rank: int
    total_score: float
    price_change: float
    turnover_rate: float
    volume: int
    volatility: float
    close_price: float
    open_price: float
    high_price: float
    low_price: float
    market_cap: float

class FullIndicatorsDict(DailyDataDict):
    """完整技术指标字典（83字段）"""
    macd_signal: float
    dif: float
    dem: float
    # ... 其他80个字段
```

---

## 五、迁移方案

### 5.1 文件改动清单

| 文件 | 改动类型 | 说明 |
|------|----------|------|
| `services/numpy_cache_middleware.py` | **新建** | 统一缓存中间件 |
| `services/numpy_stores/daily_store.py` | **新建** | 每日数据存储 |
| `services/numpy_stores/sector_store.py` | **新建** | 板块数据存储 |
| `services/numpy_stores/index_manager.py` | **新建** | 索引管理器 |
| `services/memory_cache.py` | **精简** | 仅保留stock字典，移除daily_data |
| `services/numpy_cache.py` | **删除** | 合并到新中间件 |
| `services/analysis_service_db.py` | **适配** | 改用中间件接口 |
| `services/stock_service_db.py` | **适配** | 改用中间件接口 |
| `services/rank_jump_service_db.py` | **重构** | 从DB查询改为缓存查询 |
| `services/steady_rise_service_db.py` | **重构** | 从DB查询改为缓存查询 |
| `services/signal_calculator.py` | **适配** | 改用中间件接口 |
| `services/hot_spots_cache.py` | **适配** | 改用中间件接口 |
| `services/sector_service_db.py` | **适配** | 改用中间件接口 |
| `services/industry_service_db.py` | **适配** | 改用中间件接口 |
| `services/industry_detail_service.py` | **适配** | 改用中间件接口 |

### 5.2 分阶段实施计划

#### Phase 1: 核心中间件 (预计2小时)

1. 创建 `numpy_stores/` 目录结构
2. 实现 `IndexManager` 索引管理器
3. 实现 `DailyDataStore` 每日数据存储
4. 实现 `NumpyCacheMiddleware` 中间件主类
5. 单元测试

#### Phase 2: 服务层适配 (预计2小时)

1. 适配 `analysis_service_db.py`
2. 适配 `stock_service_db.py`
3. 适配 `signal_calculator.py`
4. 适配 `hot_spots_cache.py`
5. 集成测试

#### Phase 3: 数据库查询服务迁移 (预计1.5小时)

1. 重构 `rank_jump_service_db.py` → 使用缓存
2. 重构 `steady_rise_service_db.py` → 使用缓存
3. 性能对比测试

#### Phase 4: 板块数据迁移 (预计1小时)

1. 实现 `SectorDataStore`
2. 适配 `sector_service_db.py`
3. 适配 `industry_service_db.py`
4. 适配 `industry_detail_service.py`

#### Phase 5: 清理与优化 (预计1小时)

1. 删除旧的 `numpy_cache.py`
2. 精简 `memory_cache.py`
3. 更新启动加载逻辑
4. 完整回归测试

---

## 六、接口映射表

### 6.1 MemoryCacheManager → NumpyCacheMiddleware

| 旧接口 | 新接口 | 说明 |
|--------|--------|------|
| `memory_cache.get_stock_info(code)` | `cache.get_stock_info(code)` | 无变化 |
| `memory_cache.get_all_stocks()` | `cache.get_all_stocks()` | 无变化 |
| `memory_cache.get_daily_data_by_date(date)` | `cache.get_all_by_date(date)` | 返回Dict列表 |
| `memory_cache.get_daily_data_by_stock(code, date)` | `cache.get_daily_data(code, date)` | 返回Dict |
| `memory_cache.get_stock_history(code, dates)` | `cache.get_stock_history(code, days)` | 参数简化 |
| `memory_cache.get_top_n_stocks(date, n)` | `cache.get_top_n_by_rank(date, n)` | 返回Dict列表 |
| `memory_cache.get_dates_range(n)` | `cache.get_dates_range(n)` | 无变化 |
| `memory_cache.get_latest_date()` | `cache.get_latest_date()` | 无变化 |
| `memory_cache.get_available_dates()` | `cache.get_available_dates()` | 无变化 |

### 6.2 特殊注意事项

1. **返回类型变化**: 旧接口返回 ORM 对象，新接口返回 Dict
2. **属性访问变化**: `data.price_change` → `data['price_change']`
3. **股票历史接口**: 旧接口传入日期列表，新接口传入天数

---

## 七、风险与回滚

### 7.1 风险点

| 风险 | 影响 | 缓解措施 |
|------|------|----------|
| 返回类型变化导致服务层报错 | 高 | 逐文件迁移，每次测试 |
| Numpy数据类型精度丢失 | 中 | 使用float32足够，价格最多6位小数 |
| 索引构建时间过长 | 低 | 启动时异步加载 |
| 内存不足导致数组分配失败 | 低 | 30天数据仅~12MB |

### 7.2 回滚方案

1. 保留旧代码在 `services/_deprecated/` 目录
2. 中间件提供 `use_legacy=True` 开关
3. 配置文件控制缓存模式

---

## 八、性能预期

### 8.1 内存优化

| 指标 | 迁移前 | 迁移后 | 改善 |
|------|--------|--------|------|
| 进程内存 | ~400MB | ~150MB | 62.5%↓ |
| 缓存占用 | ~285MB | ~29MB | 90%↓ |
| GC压力 | 高 | 低 | 显著降低 |

### 8.2 查询性能

| 操作 | 迁移前 | 迁移后 | 改善 |
|------|--------|--------|------|
| 单股票单日查询 | ~0.1ms | ~0.05ms | 2x |
| TOP100查询 | ~5ms | ~1ms | 5x |
| 排名跳变分析 | ~200ms(DB) | ~10ms | 20x |
| 稳步上升分析 | ~300ms(DB) | ~15ms | 20x |

---

## 九、测试清单

### 9.1 单元测试

- [ ] IndexManager 索引构建与查询
- [ ] DailyDataStore 数据存取
- [ ] SectorDataStore 数据存取
- [ ] NumpyCacheMiddleware 接口完整性

### 9.2 集成测试

- [ ] 热点分析功能
- [ ] 股票搜索功能
- [ ] 排名跳变分析
- [ ] 稳步上升分析
- [ ] 板块排名功能
- [ ] 信号计算功能

### 9.3 性能测试

- [ ] 启动加载时间 < 5秒
- [ ] 内存占用 < 50MB (缓存部分)
- [ ] TOP100查询 < 5ms
- [ ] 并发100请求响应时间

---

## 十、附录

### A. 目录结构

```
backend/app/services/
├── numpy_stores/                 # 新建
│   ├── __init__.py
│   ├── index_manager.py          # 索引管理
│   ├── daily_store.py            # 每日数据存储
│   └── sector_store.py           # 板块数据存储
├── numpy_cache_middleware.py     # 新建 - 统一中间件
├── memory_cache.py               # 精简 - 仅保留stocks字典
├── _deprecated/                  # 新建 - 旧代码备份
│   └── numpy_cache.py
└── ... (其他服务文件)
```

### B. 配置项

```python
# config.py
NUMPY_CACHE_CONFIG = {
    "enabled": True,              # 是否启用Numpy缓存
    "max_days": 30,               # 最大缓存天数
    "load_extended": False,       # 是否加载扩展字段
    "preload_hot_spots": True,    # 是否预加载热点榜
}
```

---

## 十一、关键技术规范 ⚠️

### 11.1 禁止 ORM 实例化

```python
# ❌ 错误做法 - 瞬间创建15万个Python对象，直接爆内存
daily_data_list = db.query(DailyStockData).all()

# ✅ 正确做法 - 使用 with_entities 只获取 Tuples
from sqlalchemy import func

rows = db.query(
    DailyStockData.stock_code,
    DailyStockData.date,
    DailyStockData.rank,
    DailyStockData.total_score,
    DailyStockData.price_change,
    DailyStockData.close_price,
    # ... 其他需要的字段
).filter(
    DailyStockData.date >= start_date
).all()  # 返回 List[Tuple]，内存占用极低

# ✅ 或者使用原生 SQL
from sqlalchemy import text
result = db.execute(text("""
    SELECT stock_code, date, rank, total_score, price_change, close_price
    FROM daily_stock_data
    WHERE date >= :start_date
"""), {"start_date": start_date})
rows = result.fetchall()  # 同样返回 Tuples
```

### 11.2 数据类型精度规范

| 字段类型 | Numpy dtype | 原因 |
|----------|-------------|------|
| 价格 (open/high/low/close) | `np.float64` | 避免0.01误差，影响排名 |
| 金额 (total_score/market_cap) | `np.float64` | 高精度计算 |
| 指标 (RSI/KDJ/MACD等) | `np.float32` | 节省空间，精度足够 |
| 整数 (rank/volume) | `np.int32/int64` | 空值填充-1或0 |
| 索引 (stock_idx/date_idx) | `np.int32` | 禁止存储字符串 |

### 11.3 空值处理规范

```python
def safe_int(value, default=-1):
    """安全转换为int，空值返回默认值"""
    if value is None:
        return default
    return int(value)

def safe_float(value, default=0.0):
    """安全转换为float，空值返回默认值"""
    if value is None:
        return default
    return float(value)

# 构建数组时使用
for i, row in enumerate(rows):
    data_array[i]['rank'] = safe_int(row.rank, -1)
    data_array[i]['volume'] = safe_int(row.volume, 0)
    data_array[i]['close_price'] = safe_float(row.close_price, 0.0)
```

### 11.4 字符串处理策略

```python
# ❌ 错误 - Numpy存字符串效率极低
dtype_bad = np.dtype([
    ('stock_code', 'U10'),  # 固定10字符，占用40字节/条！
    ...
])

# ✅ 正确 - 只存索引，通过IndexManager反查
dtype_good = np.dtype([
    ('stock_idx', np.int32),  # 只占4字节
    ...
])

# 查询时通过索引反查
stock_code = index_manager.get_stock_code(row['stock_idx'])
```

---

## 十二、二级缓存架构设计 (API响应缓存)

### 12.1 三层缓存架构

```
┌─────────────────────────────────────────────────────────────────┐
│                         API Layer (FastAPI)                      │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│                    L2 Cache: API响应缓存                          │
│              (Dogpile.cache + DiskCache 组合)                     │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐  │
│  │  Dogpile Lock   │  │   DiskCache     │  │    Memory       │  │
│  │  (防雪崩锁)      │→│   (磁盘LRU)      │→│    (热数据)      │  │
│  └─────────────────┘  └─────────────────┘  └─────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│                    L1 Cache: Numpy数据底座                        │
│                  (NumpyCacheMiddleware)                          │
│  ┌──────────────┐  ┌──────────────┐  ┌────────────────────────┐ │
│  │ StockStore   │  │ DailyStore   │  │ SectorStore            │ │
│  │ (Python Dict)│  │ (Numpy Array)│  │ (Numpy Array)          │ │
│  └──────────────┘  └──────────────┘  └────────────────────────┘ │
└─────────────────────────────────────────────────────────────────┘
                              ↓ (启动时加载)
┌─────────────────────────────────────────────────────────────────┐
│                        PostgreSQL                                │
└─────────────────────────────────────────────────────────────────┘
```

### 12.2 组件职责

| 组件 | 角色 | 职责 |
|------|------|------|
| **Numpy (L1)** | 原材料 | 数据底座，只做中间件IO，不参与API缓存 |
| **Dogpile.cache** | 交通指挥 | 防雪崩锁：缓存失效时拦住100个并发，只放1个计算 |
| **DiskCache** | 仓库管理 | 磁盘存储(SQLite) + LRU淘汰 + size_limit |
| **Memory (可选)** | 热数据快取 | 极热数据内存缓存，可选 |

### 12.3 为什么不用其他方案

| 方案 | 问题 |
|------|------|
| 纯Dogpile文件后端(DBM) | 不懂LRU，会把硬盘写满 |
| 纯DiskCache | 没有防雪崩锁，并发计算浪费资源 |
| Joblib | 适合大数组，不适合API响应；无锁 |
| Redis | 需要额外部署，小项目过重 |

### 12.4 实现方案 (已修正)

> ⚠️ **致命风险修正**

```python
# requirements.txt 新增
# dogpile.cache==1.3.1
# diskcache==5.6.3

# services/api_cache.py
from dogpile.cache import make_region
from diskcache import Cache
import threading
import logging

logger = logging.getLogger(__name__)

class APICache:
    """
    API响应二级缓存
    - DiskCache: 负责存储（LRU + size_limit）
    - threading.Lock: 负责防雪崩锁
    
    ⚠️ 注意1：此类包含同步阻塞操作，调用方必须使用普通 def，不能用 async def
    
    ⚠️ 注意2：Cache Key 内存泄漏风险
       - _locks 字典只增不减，Key过多会泄漏内存
       - ✅ 安全的Key：stock_code(5000个), date(30个), period(有限枚举)
       - ❌ 禁止的Key：随机ID、用户搜索原文、无限增长的参数组合
       - 只要Key是有限集合，此实现就是安全的
    """
    
    def __init__(self, cache_dir: str = ".api_cache", size_limit_gb: float = 1.0):
        # DiskCache 作为存储后端
        self.disk_cache = Cache(
            directory=cache_dir,
            size_limit=int(size_limit_gb * 1024 * 1024 * 1024),  # 1GB
            eviction_policy='least-recently-used',
        )
        
        # 简单的锁管理器
        # ⚠️ 警告：_locks只增不减，Cache Key必须是有限集合！
        self._locks: dict[str, threading.Lock] = {}
        self._locks_lock = threading.Lock()  # 保护_locks字典
    
    def _get_lock(self, key: str) -> threading.Lock:
        """获取或创建指定 key 的锁"""
        with self._locks_lock:
            if key not in self._locks:
                self._locks[key] = threading.Lock()
            return self._locks[key]
    
    def get_or_create(self, key: str, creator_func, ttl: int = 300):
        """
        获取缓存，不存在则创建
        使用锁防止并发穿透（防雪崩）
        
        Args:
            key: 缓存键
            creator_func: 创建数据的函数 (无参)
            ttl: 过期时间(秒)
        """
        # 1. 先查DiskCache（无锁）
        cached = self.disk_cache.get(key)
        if cached is not None:
            return cached
        
        # 2. 获取该key的锁，只让一个请求去计算
        lock = self._get_lock(key)
        with lock:
            # 双重检查（其他线程可能已经计算完毕）
            cached = self.disk_cache.get(key)
            if cached is not None:
                return cached
            
            # 3. 计算结果（加异常保护）
            try:
                result = creator_func()
            except Exception as e:
                logger.error(f"缓存计算失败 [{key}]: {e}")
                raise  # 重新抛出，锁会自动释放
            
            # 4. 存入DiskCache
            self.disk_cache.set(key, result, expire=ttl)
            return result
    
    def invalidate(self, pattern: str = None):
        """使缓存失效"""
        if pattern:
            # 按模式删除
            for key in list(self.disk_cache):
                if pattern in str(key):
                    del self.disk_cache[key]
        else:
            self.disk_cache.clear()
    
    def stats(self) -> dict:
        """获取统计信息"""
        return {
            "size_bytes": self.disk_cache.volume(),
            "size_mb": self.disk_cache.volume() / (1024 * 1024),
            "count": len(self.disk_cache),
        }

# 全局实例
api_cache = APICache()
```

### 12.5 使用示例 (已修正)

> 🚨 **FastAPI async 陷阱修正**
>
> 问题：`async def` + 同步阻塞操作(DiskCache读写/Numpy计算) 会卡死 Event Loop
>
> 后果：计算时其他用户请求进不来，服务假死
>
> 修正：去掉 `async`，让 FastAPI 自动把请求交给线程池

```python
# routers/analysis.py
from app.services.api_cache import api_cache
from app.services.numpy_cache_middleware import numpy_cache

# ⚠️ 正确：普通 def，FastAPI 会自动在线程池中运行
@router.get("/analyze/{period}")
def analyze_period(period: int, max_count: int = 100):  # ← 无 async
    # 构建缓存键
    cache_key = f"analyze:{period}:{max_count}:{numpy_cache.get_latest_date()}"
    
    # 使用缓存
    result = api_cache.get_or_create(
        key=cache_key,
        creator_func=lambda: analysis_service.analyze_period(period, max_count),
        ttl=300  # 5分钟
    )
    
    return result

# ❌ 错误：async def + 同步阻塞 = 服务假死
# @router.get("/analyze/{period}")
# async def analyze_period(...):
#     result = api_cache.get_or_create(...)  # DiskCache IO 会卡死 Event Loop!
```

### 12.6 现有TTL缓存迁移

| 现有位置 | 迁移方案 |
|----------|----------|
| `services/ttl_cache.py` | 废弃，改用 `api_cache` |
| `utils/ttl_cache.py` | 废弃，改用 `api_cache` |
| `utils/cache.py` | 废弃，改用 `api_cache` |
| 各服务的 `self.cache = {}` | 改用 `api_cache.get_or_create()` |

### 12.7 缓存失效策略

```python
# 数据更新后，清除相关缓存
def on_data_imported(imported_date: str):
    """数据导入后的缓存清理"""
    # 清除与该日期相关的所有API缓存
    api_cache.invalidate(pattern=imported_date)
    # 或清除所有
    api_cache.invalidate()
    
# 在 routers/sync.py 或数据导入逻辑中调用
```

---

## 十三、完整依赖列表

```txt
# requirements.txt 新增
numpy>=1.24.0
dogpile.cache>=1.3.0
diskcache>=5.6.0
```

---

## 十四、架构简化建议 (采纳)

### 14.1 合并 Core/Extended Dtype

**原设计**: 分离为 `core_dtype` (高频) 和 `extended_dtype` (低频)

**简化建议**: 合并为单一大 dtype

**理由**:
- 30天数据 × 15万条/天 = 450万条
- 单一 dtype ~120字节/条 ≈ **54MB**
- 在 1.6GB 内存中，54MB vs 10MB 区别不大
- 但分离会导致 **join两个数组的逻辑复杂性**、索引对齐问题
- **Simple is better**

```python
# 合并后的完整 dtype (~120字节/条)
UNIFIED_DTYPE = np.dtype([
    # === 索引字段 ===
    ('stock_idx', np.int32),       # 4B
    ('date_idx', np.int32),        # 4B
    
    # === 核心字段 (float64 高精度) ===
    ('rank', np.int32),            # 4B (空值填-1)
    ('total_score', np.float64),   # 8B
    ('price_change', np.float64),  # 8B
    ('close_price', np.float64),   # 8B
    ('open_price', np.float64),    # 8B
    ('high_price', np.float64),    # 8B
    ('low_price', np.float64),     # 8B
    ('market_cap', np.float64),    # 8B
    
    # === 交易数据 ===
    ('volume', np.int64),          # 8B (空值填0)
    ('turnover_rate', np.float32), # 4B
    ('volatility', np.float32),    # 4B
    ('volume_days', np.float32),   # 4B
    ('avg_volume_ratio_50', np.float32),  # 4B
    
    # === 技术指标 (float32 足够) ===
    ('macd_signal', np.float32),   # 4B
    ('dif', np.float32),           # 4B
    ('dem', np.float32),           # 4B
    ('rsi', np.float32),           # 4B
    ('slowk', np.float32),         # 4B
    ('adx', np.float32),           # 4B
    ('beta', np.float32),          # 4B
    ('correlation', np.float32),   # 4B
    # ... 其他指标按需添加
])
```

---

## 十五、完整接口设计 (通用+专用)

> 目标: 让后端 **99%情况下不访问数据库**，提供完善接口避免"设计好了没人用"

### 15.1 接口分类

```
┌─────────────────────────────────────────────────────────────────┐
│                      NumpyCacheMiddleware                        │
├─────────────────────────────────────────────────────────────────┤
│  通用接口 (Generic)              │  专用接口 (Specialized)        │
│  - 基础CRUD                      │  - 联表查询                    │
│  - 批量查询                      │  - 策略数据                    │
│  - 日期管理                      │  - 聚合计算                    │
└─────────────────────────────────────────────────────────────────┘
```

### 15.2 通用接口 (Generic API)

#### 15.2.1 日期管理

```python
# === 股票日期 ===
def get_available_dates() -> List[str]:
    """获取所有可用日期 (YYYYMMDD字符串列表, 降序)"""

def get_latest_date() -> Optional[date]:
    """获取最新日期"""

def get_dates_range(n: int) -> List[date]:
    """获取最近N天日期 (降序)"""

def has_date(target_date: date) -> bool:
    """检查日期是否有数据"""

# === 板块日期 ===
def get_sector_available_dates() -> List[str]:
    """获取板块所有可用日期"""

def get_sector_latest_date() -> Optional[date]:
    """获取板块最新日期"""

def get_sector_dates_range(n: int) -> List[date]:
    """获取板块最近N天日期"""
```

#### 15.2.2 股票基础信息

```python
def get_stock_info(stock_code: str) -> Optional[StockInfo]:
    """获取股票基础信息 (code, name, industry)"""

def get_all_stocks() -> Dict[str, StockInfo]:
    """获取所有股票 {code: StockInfo}"""

def get_stocks_batch(stock_codes: List[str]) -> Dict[str, StockInfo]:
    """批量获取股票信息"""

def search_stocks(keyword: str, limit: int = 10) -> List[StockInfo]:
    """搜索股票 (代码/名称模糊匹配)"""
```

#### 15.2.3 股票日数据查询

```python
def get_daily_data(stock_code: str, target_date: date) -> Optional[Dict]:
    """
    获取单股票单日数据
    
    Returns:
        {
            'stock_code': '600000',
            'date': '20251127',
            'rank': 1,
            'total_score': 98.5,
            'price_change': 5.2,
            'close_price': 10.5,
            ...
        }
    """

def get_daily_data_batch(
    stock_codes: List[str], 
    target_date: date
) -> Dict[str, Dict]:
    """
    批量获取多股票单日数据
    
    Returns:
        {'600000': {...}, '000001': {...}}
    """

def get_stock_history(
    stock_code: str, 
    days: int = 30,
    end_date: Optional[date] = None
) -> List[Dict]:
    """
    获取单股票历史数据 (按日期降序)
    
    Args:
        stock_code: 股票代码
        days: 返回天数
        end_date: 结束日期，默认最新日期
    """

def get_all_by_date(target_date: date) -> List[Dict]:
    """获取某日期的所有股票数据"""

def get_top_n_by_rank(target_date: date, n: int) -> List[Dict]:
    """获取某日期排名前N的股票 (按rank升序)"""

def get_stocks_by_industry(
    industry: str, 
    target_date: date
) -> List[Dict]:
    """获取某行业的所有股票数据"""
```

#### 15.2.4 板块基础信息

```python
def get_sector_info(sector_id: int) -> Optional[SectorInfo]:
    """获取板块基础信息"""

def get_all_sectors() -> Dict[int, SectorInfo]:
    """获取所有板块"""

def search_sectors(keyword: str) -> List[SectorInfo]:
    """搜索板块"""
```

#### 15.2.5 板块日数据查询

```python
def get_sector_daily_data(
    sector_id: int, 
    target_date: date
) -> Optional[Dict]:
    """获取板块单日数据"""

def get_sector_history(
    sector_id: int, 
    days: int = 30
) -> List[Dict]:
    """获取板块历史数据"""

def get_top_n_sectors(target_date: date, n: int) -> List[Dict]:
    """获取某日期排名前N的板块"""

def get_sector_all_by_date(target_date: date) -> List[Dict]:
    """获取某日期的所有板块数据"""
```

### 15.3 专用接口 (Specialized API)

#### 15.3.1 联表查询 (Stock + Daily Data)

```python
def get_stock_daily_full(
    stock_code: str, 
    target_date: date
) -> Optional[StockDailyFull]:
    """
    获取股票完整数据 (基础信息 + 日数据)
    
    Returns:
        StockDailyFull {
            stock_code: str
            stock_name: str
            industry: str
            date: str
            rank: int
            total_score: float
            price_change: float
            ... (所有日数据字段)
        }
    """

def get_stocks_daily_full_batch(
    stock_codes: List[str],
    target_date: date
) -> List[StockDailyFull]:
    """批量获取股票完整数据"""

def get_top_n_stocks_full(
    target_date: date, 
    n: int
) -> List[StockDailyFull]:
    """获取排名前N的股票完整数据 (已联表)"""
```

#### 15.3.2 联表查询 (Sector + Daily Data)

```python
def get_sector_daily_full(
    sector_id: int,
    target_date: date
) -> Optional[SectorDailyFull]:
    """获取板块完整数据 (名称 + 日数据)"""

def get_top_n_sectors_full(
    target_date: date,
    n: int
) -> List[SectorDailyFull]:
    """获取排名前N的板块完整数据"""
```

#### 15.3.3 策略分析专用数据

```python
def get_stock_data_for_strategy(
    stock_code: str,
    target_date: date,
    lookback_days: int = 30
) -> Optional[StrategyData]:
    """
    获取策略分析用的完整数据
    
    Returns:
        StrategyData {
            stock_code: str
            stock_name: str
            signal_date: str
            closes: List[float]      # 收盘价序列
            opens: List[float]       # 开盘价序列
            highs: List[float]       # 最高价序列
            lows: List[float]        # 最低价序列
            volumes: List[int]       # 成交量序列
            turnovers: List[float]   # 换手率序列
            ranks: List[int]         # 排名序列
            price_changes: List[float]  # 涨跌幅序列
            dates: List[str]         # 日期序列
        }
    """

def get_stocks_data_for_strategy_batch(
    stock_codes: List[str],
    target_date: date,
    lookback_days: int = 30
) -> Dict[str, StrategyData]:
    """批量获取策略数据"""
```

#### 15.3.4 聚合计算

```python
def get_market_volatility_summary(days: int = 3) -> Dict:
    """
    全市场波动率汇总
    
    Returns:
        {
            'current': 2.35,
            'days': [{'date': '20251127', 'avg_volatility': 2.35, 'stock_count': 5000}, ...],
            'trend': 'down',
            'stock_count': 5435
        }
    """

def get_industry_statistics(target_date: date) -> Dict[str, int]:
    """
    获取行业分布统计
    
    Returns:
        {'食品': 120, '建材': 85, ...}
    """

def get_rank_statistics(target_date: date) -> Dict:
    """
    获取排名统计信息
    
    Returns:
        {
            'total_stocks': 5000,
            'date': '20251127',
            'top100_avg_score': 95.2,
            'top100_avg_change': 3.5
        }
    """
```

### 15.4 返回数据类型定义

```python
from dataclasses import dataclass
from typing import List, Optional

@dataclass
class StockInfo:
    """股票基础信息"""
    stock_code: str
    stock_name: str
    industry: str

@dataclass
class SectorInfo:
    """板块基础信息"""
    sector_id: int
    sector_name: str

@dataclass
class StockDailyFull:
    """股票完整日数据 (联表结果)"""
    # 基础信息
    stock_code: str
    stock_name: str
    industry: str
    # 日数据
    date: str
    rank: int
    total_score: float
    price_change: float
    turnover_rate: float
    volume: int
    volatility: float
    close_price: float
    open_price: float
    high_price: float
    low_price: float
    market_cap: float
    # 技术指标
    macd_signal: Optional[float] = None
    rsi: Optional[float] = None
    # ... 其他字段

@dataclass
class StrategyData:
    """策略分析用数据"""
    stock_code: str
    stock_name: str
    signal_date: str
    closes: List[float]
    opens: List[float]
    highs: List[float]
    lows: List[float]
    volumes: List[int]
    turnovers: List[float]
    ranks: List[int]
    price_changes: List[float]
    dates: List[str]
```

### 15.5 API路由层async修正清单

> 所有使用 `api_cache` 或 `numpy_cache` 的路由必须改为普通 `def`

| 文件 | 函数 | 当前 | 修正后 |
|------|------|------|--------|
| `analysis.py` | `get_available_dates` | `async def` | `def` |
| `analysis.py` | `analyze_period` | `async def` | `def` |
| `analysis.py` | `get_hot_spots_full` | `async def` | `def` |
| `analysis.py` | `get_market_volatility_summary` | `async def` | `def` |
| `stock.py` | `get_stock_raw_data` | `async def` | `def` |
| `stock.py` | `search_stock_full` | `async def` | `def` |
| `stock.py` | `query_stock` | `async def` | `def` |
| `industry.py` | 全部函数 | `async def` | `def` |
| `industry_detail.py` | 全部函数 | `async def` | `def` |
| `sector.py` | 全部函数 | `async def` | `def` |
| `rank_jump.py` | `analyze_rank_jump` | `async def` | `def` |
| `steady_rise.py` | `analyze_steady_rise` | `async def` | `def` |
| `strategies.py` | 全部函数 | `async def` | `def` |

---

## 十六、修订历史

| 版本 | 日期 | 变更 |
|------|------|------|
| v1.0 | 2024-12-02 | 初始设计 |
| v1.1 | 2024-12-02 | 加入关键技术规范、二级缓存架构 |
| v1.2 | 2024-12-02 | 修正async陷阱、Dogpile锁、合并dtype、完整接口设计 |
