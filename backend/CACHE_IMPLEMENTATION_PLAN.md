# 基于现有CacheManager的缓存实施方案

## 📋 现状分析

### ✅ 已有基础设施
```python
# app/utils/cache.py - 已存在
class CacheManager:
    """线程安全的缓存管理器"""
    - get(key)
    - set(key, value)
    - clear(key=None)
    - has(key)
    - cache_result(key) - 装饰器
```

### ✅ 已使用缓存的服务
1. **RankJumpServiceDB** - 排名跳变分析
   - ✅ 已实现：`self.cache = {}`
   - ✅ 缓存key：`rank_jump_{threshold}_{board_type}_{sigma}_{date}`

2. **SteadyRiseServiceDB** - 稳步上升分析
   - ✅ 已实现：`self.cache = {}`
   - ✅ 缓存key：`steady_rise_{period}_{board_type}_{improvement}_{sigma}_{date}`

### ❌ 未使用缓存的服务
1. **AnalysisServiceDB** - 热点分析 ⭐⭐⭐⭐⭐
2. **IndustryServiceDB** - 行业分析 ⭐⭐⭐⭐⭐
3. **SectorServiceDB** - 板块分析 ⭐⭐⭐⭐
4. **StockServiceDB** - 个股查询 ⭐⭐

---

## 🎯 实施方案

### 方案A：扩展现有CacheManager（推荐）

为CacheManager添加TTL支持：

```python
# app/utils/cache.py
from datetime import datetime, timedelta

class CacheManager:
    """线程安全的缓存管理器（带TTL）"""
    
    def __init__(self):
        self._cache: Dict[str, tuple] = {}  # {key: (value, expiry)}
        self._lock = threading.Lock()
    
    def get(self, key: str) -> Optional[Any]:
        """获取缓存（自动过期）"""
        with self._lock:
            if key in self._cache:
                value, expiry = self._cache[key]
                if expiry is None or datetime.now() < expiry:
                    return value
                else:
                    # 已过期，删除
                    del self._cache[key]
            return None
    
    def set(self, key: str, value: Any, ttl_seconds: Optional[int] = None) -> None:
        """设置缓存（可选TTL）"""
        with self._lock:
            expiry = None
            if ttl_seconds:
                expiry = datetime.now() + timedelta(seconds=ttl_seconds)
            self._cache[key] = (value, expiry)
    
    def clear(self, key: Optional[str] = None, pattern: Optional[str] = None) -> None:
        """清除缓存（支持模式匹配）"""
        with self._lock:
            if key:
                self._cache.pop(key, None)
            elif pattern:
                # 清除匹配模式的所有key
                keys_to_delete = [k for k in self._cache.keys() if pattern in k]
                for k in keys_to_delete:
                    del self._cache[k]
            else:
                self._cache.clear()
    
    def get_stats(self) -> Dict[str, Any]:
        """获取缓存统计"""
        with self._lock:
            total = len(self._cache)
            expired = sum(1 for _, expiry in self._cache.values() 
                         if expiry and datetime.now() >= expiry)
            return {
                "total_keys": total,
                "expired_keys": expired,
                "active_keys": total - expired
            }
```

---

## 📝 具体实施步骤

### 第1步：升级CacheManager（10分钟）

**文件**: `app/utils/cache.py`

**改动**: 添加TTL支持（如上方案A代码）

---

### 第2步：AnalysisServiceDB 添加缓存（15分钟）⭐⭐⭐⭐⭐

**文件**: `app/services/analysis_service_db.py`

```python
class AnalysisServiceDB:
    """热点分析服务（数据库版）"""
    
    def __init__(self):
        self.cache = {}
        self._dates_cache = None  # 日期列表缓存
        self._dates_cache_time = None
    
    def get_available_dates(self) -> List[str]:
        """获取可用日期列表（带缓存）"""
        # 缓存1小时
        if (self._dates_cache is not None and 
            self._dates_cache_time and 
            (datetime.now() - self._dates_cache_time).seconds < 3600):
            return self._dates_cache
        
        db = self.get_db()
        try:
            dates = db.query(DailyStockData.date)\
                .distinct()\
                .order_by(desc(DailyStockData.date))\
                .all()
            
            result = [d[0].strftime('%Y%m%d') for d in dates]
            self._dates_cache = result
            self._dates_cache_time = datetime.now()
            return result
        finally:
            db.close()
    
    def analyze_period(
        self,
        period: int = 3,
        max_count: int = 100,
        board_type: str = 'main',
        target_date: Optional[str] = None
    ) -> AnalysisResult:
        """周期热点分析（带缓存）"""
        # 生成缓存key
        cache_key = f"analyze_{period}_{max_count}_{board_type}_{target_date}"
        if cache_key in self.cache:
            logger.info(f"✨ 缓存命中: {cache_key}")
            return self.cache[cache_key]
        
        logger.info(f"🔄 计算中: {cache_key}")
        
        # ... 原有计算逻辑 ...
        
        # 缓存结果
        self.cache[cache_key] = result
        return result
```

---

### 第3步：IndustryServiceDB 添加缓存（20分钟）⭐⭐⭐⭐⭐

**文件**: `app/services/industry_service_db.py`

**关键接口**:
1. `get_industry_trend()` - 行业趋势
2. `get_industry_weighted()` - 加权统计（最重要！）
3. `get_top1000_industry()` - TOP1000统计

```python
class IndustryServiceDB:
    """行业分析服务（数据库版）"""
    
    def __init__(self):
        self.cache = {}
    
    def get_industry_weighted(
        self,
        target_date: Optional[str] = None,
        k: float = 0.618,
        top_n_industries: int = 15
    ):
        """加权行业统计（带缓存）"""
        # 缓存key - k值保留2位小数
        k_str = f"{k:.2f}"
        cache_key = f"weighted_{target_date}_{k_str}_{top_n_industries}"
        
        if cache_key in self.cache:
            logger.info(f"✨ 缓存命中: weighted k={k}")
            return self.cache[cache_key]
        
        logger.info(f"🔄 计算加权统计: k={k}")
        
        # ... 原有计算逻辑（5000+股票聚合）...
        
        self.cache[cache_key] = result
        return result
    
    def get_industry_trend(self, period: int, top_n: int, target_date: Optional[str]):
        """行业趋势（带缓存）"""
        cache_key = f"trend_{period}_{top_n}_{target_date}"
        
        if cache_key in self.cache:
            return self.cache[cache_key]
        
        # ... 原有逻辑 ...
        
        self.cache[cache_key] = result
        return result
    
    def get_top1000_industry(self, limit: int, target_date: Optional[str]):
        """TOP统计（带缓存）"""
        cache_key = f"top_{limit}_{target_date}"
        
        if cache_key in self.cache:
            return self.cache[cache_key]
        
        # ... 原有逻辑 ...
        
        self.cache[cache_key] = result
        return result
```

---

### 第4步：SectorServiceDB 添加缓存（15分钟）⭐⭐⭐⭐

**文件**: `app/services/sector_service_db.py`

**关键接口**:
1. `get_sector_trend()` - 板块趋势
2. `get_sector_rank_changes()` - 排名变化
3. `get_available_dates()` - 日期列表

```python
class SectorServiceDB:
    """板块分析服务（数据库版）"""
    
    def __init__(self):
        self.cache = {}
        self._dates_cache = None
        self._dates_cache_time = None
    
    def get_available_dates(self) -> List[str]:
        """获取可用日期（带缓存）"""
        if (self._dates_cache and self._dates_cache_time and
            (datetime.now() - self._dates_cache_time).seconds < 3600):
            return self._dates_cache
        
        # ... 查询逻辑 ...
        
        self._dates_cache = result
        self._dates_cache_time = datetime.now()
        return result
    
    def get_sector_trend(self, days: int, limit: int, target_date: Optional[str]):
        """板块趋势（带缓存）"""
        cache_key = f"sector_trend_{days}_{limit}_{target_date}"
        if cache_key in self.cache:
            return self.cache[cache_key]
        
        # ... 原有逻辑 ...
        
        self.cache[cache_key] = result
        return result
    
    def get_sector_rank_changes(self, target_date: Optional[str], compare_days: int):
        """排名变化（带缓存）"""
        cache_key = f"rank_changes_{target_date}_{compare_days}"
        if cache_key in self.cache:
            return self.cache[cache_key]
        
        # ... 原有逻辑 ...
        
        self.cache[cache_key] = result
        return result
```

---

### 第5步：添加缓存管理接口（10分钟）

**文件**: `app/routers/cache.py`（新建）

```python
"""
缓存管理API
"""
from fastapi import APIRouter
from ..services.analysis_service_db import analysis_service_db
from ..services.industry_service_db import industry_service_db
from ..services.sector_service_db import sector_service_db
from ..services.rank_jump_service_db import rank_jump_service_db
from ..services.steady_rise_service_db import steady_rise_service_db

router = APIRouter(prefix="/api/cache", tags=["cache"])

@router.post("/clear")
async def clear_cache(date: str = None):
    """清除缓存"""
    if date:
        # 清除特定日期的缓存
        pattern = f"_{date}"
        analysis_service_db.cache = {k: v for k, v in analysis_service_db.cache.items() if pattern not in k}
        industry_service_db.cache = {k: v for k, v in industry_service_db.cache.items() if pattern not in k}
        sector_service_db.cache = {k: v for k, v in sector_service_db.cache.items() if pattern not in k}
        rank_jump_service_db.cache = {k: v for k, v in rank_jump_service_db.cache.items() if pattern not in k}
        steady_rise_service_db.cache = {k: v for k, v in steady_rise_service_db.cache.items() if pattern not in k}
        return {"message": f"已清除日期 {date} 的缓存"}
    else:
        # 清除所有缓存
        analysis_service_db.cache.clear()
        industry_service_db.cache.clear()
        sector_service_db.cache.clear()
        rank_jump_service_db.cache.clear()
        steady_rise_service_db.cache.clear()
        return {"message": "已清除所有缓存"}

@router.get("/stats")
async def get_cache_stats():
    """获取缓存统计"""
    return {
        "analysis": len(analysis_service_db.cache),
        "industry": len(industry_service_db.cache),
        "sector": len(sector_service_db.cache),
        "rank_jump": len(rank_jump_service_db.cache),
        "steady_rise": len(steady_rise_service_db.cache),
        "total": (len(analysis_service_db.cache) + 
                 len(industry_service_db.cache) + 
                 len(sector_service_db.cache) +
                 len(rank_jump_service_db.cache) +
                 len(steady_rise_service_db.cache))
    }
```

**注册路由**: 在 `app/main.py` 中添加
```python
from app.routers import cache as cache_router
app.include_router(cache_router.router)
```

---

## 📈 预期效果

### 性能提升
| 接口 | 当前耗时 | 缓存后耗时 | 提升倍数 |
|------|----------|------------|----------|
| `/api/dates` | 50-100ms | **5-10ms** | 10x |
| `/api/analyze/7` | 800-1500ms | **10-50ms** | 50x |
| `/api/industry/weighted` | 2000-3000ms | **10-50ms** | 100x |
| `/api/industry/trend` | 500-1000ms | **10-50ms** | 30x |
| `/api/sectors/trend` | 800-1200ms | **10-50ms** | 40x |

### 用户体验
- ✅ 切换参数几乎无延迟
- ✅ 页面加载速度大幅提升
- ✅ 并发能力显著增强

---

## ⚙️ 运维管理

### 定时清理脚本

**文件**: `scripts/clear_old_cache.py`

```python
"""
清理旧日期缓存
每日数据入库后运行
"""
from datetime import datetime, timedelta
from app.services.analysis_service_db import analysis_service_db
from app.services.industry_service_db import industry_service_db
from app.services.sector_service_db import sector_service_db
from app.services.rank_jump_service_db import rank_jump_service_db
from app.services.steady_rise_service_db import steady_rise_service_db

# 获取昨天的日期
yesterday = (datetime.now() - timedelta(days=1)).strftime('%Y%m%d')

# 清除昨天及更早的缓存（因为今天有新数据了）
services = [
    analysis_service_db,
    industry_service_db,
    sector_service_db,
    rank_jump_service_db,
    steady_rise_service_db
]

for service in services:
    old_count = len(service.cache)
    service.cache = {k: v for k, v in service.cache.items() 
                     if yesterday not in k}
    new_count = len(service.cache)
    print(f"✅ {service.__class__.__name__}: 清理 {old_count - new_count} 条缓存")

print(f"🎉 缓存清理完成！")
```

---

## 🚀 实施优先级

### 立即实施（第1天）⭐⭐⭐⭐⭐
1. ✅ 升级CacheManager（可选，不升级也能用）
2. ✅ AnalysisServiceDB 添加缓存
3. ✅ IndustryServiceDB 添加缓存（重点！）

### 第2天 ⭐⭐⭐⭐
4. ✅ SectorServiceDB 添加缓存
5. ✅ 添加缓存管理接口

### 观察与优化
- 监控缓存命中率
- 调整TTL时间
- 优化缓存key设计

---

## 💡 最佳实践

1. **缓存key命名规范**
   ```
   {service}_{method}_{param1}_{param2}_{date}
   例如：analyze_period_7_100_main_20251107
   ```

2. **缓存更新策略**
   - 每日数据入库后，清除相关日期缓存
   - 服务重启时自动清空所有缓存

3. **内存管理**
   - 设置最大缓存条目数（例如1000条）
   - 超过限制时使用LRU淘汰

---

## ✅ 实施检查清单

- [ ] 1. 阅读并理解现有CacheManager
- [ ] 2. 为AnalysisServiceDB添加缓存
- [ ] 3. 为IndustryServiceDB添加缓存（重点）
- [ ] 4. 为SectorServiceDB添加缓存
- [ ] 5. 添加缓存管理API
- [ ] 6. 测试缓存效果
- [ ] 7. 监控内存使用
- [ ] 8. 添加定时清理脚本
