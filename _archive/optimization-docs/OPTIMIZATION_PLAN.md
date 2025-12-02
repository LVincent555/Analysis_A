# 性能优化方案

## 当前问题
- 内存占用过高（一次性加载所有数据）
- CPU计算密集（实时计算信号）
- 并发请求导致资源耗尽

## 方案1：内存优化（立即实施）

### 1.1 限制缓存数据范围
**当前**：加载所有历史数据
**优化**：只加载最近30天数据

```python
# memory_cache.py
class MemoryCacheManager:
    def __init__(self):
        self.max_days = 30  # 只保留30天数据
        
    def load_all_data(self):
        # 只加载最近30天
        latest_date = db.query(func.max(DailyStockData.date)).scalar()
        cutoff_date = latest_date - timedelta(days=self.max_days)
        
        daily_data_list = db.query(DailyStockData).filter(
            DailyStockData.date >= cutoff_date
        ).all()
```

**效果**：内存占用减少50-70%

### 1.2 延迟加载热点榜缓存
**当前**：启动时加载14天热点榜
**优化**：第一次访问时才加载

```python
# hot_spots_cache.py
@classmethod
def get_full_data(cls, date: str):
    if date not in cls._cache:
        cls._load_date(date)  # 按需加载
    return cls._cache[date]["data"]
```

**效果**：启动速度提升3-5倍，初始内存占用减少

### 1.3 添加限流中间件
防止并发请求过多

```python
# main.py
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter

# 限制每个IP每分钟最多60个请求
@app.middleware("http")
async def rate_limit_middleware(request: Request, call_next):
    # 实现限流逻辑
    pass
```

**效果**：防止单个用户耗尽资源

### 1.4 优化数据结构
使用更紧凑的数据结构

```python
# 使用__slots__减少内存
class CompactStockData:
    __slots__ = ['code', 'date', 'rank', 'score', 'price_change']
    
# 使用numpy数组替代Python对象（对于数值数据）
import numpy as np
self.ranks = np.array([...], dtype=np.int32)  # 比Python list省50%内存
```

**效果**：内存占用减少30-40%

## 方案2：使用Redis（中期方案）

### 2.1 Redis的优势
✅ **分布式**：多个worker共享缓存
✅ **持久化**：重启不丢失数据
✅ **内存管理**：自动LRU淘汰
✅ **过期策略**：自动清理旧数据

### 2.2 Redis的劣势
❌ **网络开销**：每次查询都要网络往返（1-5ms）
❌ **序列化开销**：Python对象 ↔ Redis格式转换
❌ **复杂度**：增加部署和维护成本

### 2.3 混合方案（推荐）

```
┌─────────────┐     ┌──────────────┐     ┌──────────────┐
│   Redis     │ ←→  │  L1 Cache    │ ←→  │   FastAPI    │
│ (持久化层)   │     │ (内存缓存)    │     │   (服务层)    │
└─────────────┘     └──────────────┘     └──────────────┘
      ↓                    ↓
  基础数据           热数据（最近7天）
  (不常变)            (频繁访问)
```

**架构**：
- **L1 Cache**（内存）：缓存最近7天的热数据
- **Redis**：存储完整的30天数据
- **PostgreSQL**：存储所有历史数据

**查询流程**：
1. 先查L1 Cache（内存）→ 命中率80%，<1ms
2. 未命中查Redis → 命中率95%，1-3ms
3. 未命中查数据库 → 5-20ms

```python
class HybridCache:
    def __init__(self):
        self.l1_cache = {}  # 内存缓存（7天）
        self.redis = Redis()
        
    def get(self, key):
        # L1缓存
        if key in self.l1_cache:
            return self.l1_cache[key]
        
        # Redis缓存
        value = self.redis.get(key)
        if value:
            self.l1_cache[key] = value  # 写入L1
            return value
        
        # 数据库查询
        value = self.db.query(key)
        self.redis.set(key, value, ex=3600)  # 1小时过期
        self.l1_cache[key] = value
        return value
```

## 方案3：计算优化

### 3.1 预计算信号
**当前**：每次请求都实时计算
**优化**：定时任务预计算，存储结果

```python
# 每天凌晨1点预计算所有股票信号
@scheduler.scheduled_job('cron', hour=1)
def precompute_signals():
    for stock_code in all_stocks:
        signals = calculator.calculate_signals(stock_code, latest_date)
        redis.set(f"signals:{stock_code}:{latest_date}", signals, ex=86400)
```

**效果**：API响应时间从50ms → 5ms

### 3.2 批量查询优化
使用数据库的批量查询

```python
# 当前：N次查询
for stock_code in codes:
    data = db.query(DailyStockData).filter_by(stock_code=stock_code).first()

# 优化：1次查询
data_list = db.query(DailyStockData).filter(
    DailyStockData.stock_code.in_(codes)
).all()
```

**效果**：查询时间减少90%

### 3.3 异步加载
使用后台任务加载数据

```python
from fastapi import BackgroundTasks

@app.on_event("startup")
async def startup_event():
    # 后台加载数据，不阻塞启动
    BackgroundTasks().add_task(memory_cache.load_all_data)
    
    # 立即返回，允许健康检查通过
    return {"status": "starting"}
```

## 推荐实施顺序

### 阶段1：紧急优化（1-2小时）
1. ✅ 限制缓存数据到最近30天
2. ✅ 添加API限流
3. ✅ 热点榜延迟加载

**预期效果**：内存占用减少60%，服务稳定运行

### 阶段2：性能优化（1-2天）
1. 优化数据结构（numpy数组）
2. 批量查询优化
3. 添加响应缓存

**预期效果**：API响应时间减少50%

### 阶段3：架构升级（1-2周）
1. 引入Redis（混合缓存）
2. 预计算每日信号
3. 添加分布式任务队列（Celery）

**预期效果**：支持10x并发，可水平扩展

## 成本对比

| 方案 | 实施时间 | 内存节省 | 性能提升 | 复杂度 |
|------|---------|---------|---------|--------|
| 方案1 | 2小时 | 60% | 20% | 低 |
| 方案2 | 1周 | 70% | 50% | 中 |
| 方案3 | 2周 | 80% | 300% | 高 |

## 立即可执行的代码

### 限制缓存天数
```python
# backend/app/services/memory_cache.py
# 在load_all_data方法开头添加：
from datetime import timedelta

latest_date = db.query(func.max(DailyStockData.date)).scalar()
if latest_date:
    cutoff_date = latest_date - timedelta(days=30)
    daily_data_list = db.query(DailyStockData).filter(
        DailyStockData.date >= cutoff_date
    ).all()
```

### 添加限流
```bash
pip install slowapi
```

```python
# backend/app/main.py
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

limiter = Limiter(key_func=get_remote_address, default_limits=["60/minute"])
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# 在每个路由上添加：
@router.get("/stock/{code}")
@limiter.limit("30/minute")  # 每分钟最多30次
async def get_stock(request: Request, code: str):
    ...
```

## 结论

**当前紧急情况**：建议先实施方案1（2小时内完成），稳定服务
**中期规划**：引入Redis混合缓存（1-2周）
**不推荐**：完全替换为Redis（网络开销太大，性价比低）

最佳方案是**内存 + Redis混合架构**，既快又稳。
