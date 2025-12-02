# A股股票分析系统 - 项目完整概述 (Part 1: 架构)

**版本**: v0.2.5  
**最后更新**: 2025-11-09

---

## 📑 文档导航

- **Part 1 (本文)**: 项目总览、数据库、后端、前端架构
- **Part 2**: API接口、功能模块、数据流程、部署

---

## 1. 项目总览

### 1.1 项目简介

A股股票分析系统是一个**高性能的股票数据分析平台**，支持对5000+只股票和500+个板块进行多维度技术分析和趋势预测。

### 1.2 核心特性

- ⚡ **极致性能**: 三层缓存架构，查询速度提升30-150倍
- 📊 **多维分析**: 8大分析模块，涵盖个股、行业、板块、热点等
- 🎯 **智能算法**: 加权热度分析、排名跳变检测、稳步上升识别
- 🖥️ **现代UI**: React + TailwindCSS，响应式设计
- 🔄 **实时更新**: 每日数据自动导入，状态管理防止重复

### 1.3 技术栈

#### 后端
- **框架**: FastAPI 0.109+
- **ORM**: SQLAlchemy 2.0+
- **数据库**: PostgreSQL 14+
- **服务器**: Uvicorn (ASGI)
- **缓存**: 内存缓存 + TTL缓存
- **语言**: Python 3.12+

#### 前端
- **框架**: React 18
- **样式**: TailwindCSS 3.3+
- **图表**: Recharts 2.8+
- **图标**: Lucide React
- **HTTP**: Axios

#### 部署
- **Web服务器**: Nginx
- **进程管理**: systemd + serve
- **反向代理**: Nginx → :8000 (API), :3000 (Web)

---

## 2. 数据库架构

### 2.1 数据库概览

- **数据库**: PostgreSQL 14+
- **扩展**: pg_trgm (三字符组模糊查询)
- **总表数**: 4个
- **总字段数**: 340+

### 2.1.1 ⚠️ 重要：两套独立的数据系统

**系统划分**:

```
股票数据系统 (main.sql)
├─ 数据源: *_data_sma_feature_color.xlsx (~3MB)
├─ 表: stocks + daily_stock_data
├─ 数量: ~5,435只股票
└─ 特点: stocks.industry 字段存储板块分类 (如：退货、食品、建材)

板块数据系统 (sectors.sql)
├─ 数据源: *_allbk_sma_feature_color.xlsx (~300KB)  
├─ 表: sectors + daily_sector_data
├─ 数量: ~500个板块
└─ 特点: 独立的板块技术指标，无股票关联 (版权限制)
```

**⚠️ 关键理解**:
1. **两套数据完全独立**，无数据库外键关联
2. **股票的`industry`字段是板块分类**，可用于分组分析
3. **板块数据的板块名称**与股票的板块分类**不是同一套体系**
   - 股票板块：退货、食品、建材、化学、电气...
   - 独立板块：工程建设、社区团购、转基因...
4. **可以基于`stocks.industry`实现板块成分股分析**
5. **无法将股票数据关联到独立板块数据** (命名体系不同)

### 2.2 表结构详解

#### 表1: `stocks` - 股票主表

**数据源**: `*_data_sma_feature_color.xlsx` (股票Excel)

存储股票基本信息，消除冗余

```sql
CREATE TABLE stocks (
    stock_code VARCHAR(10) PRIMARY KEY,    -- 股票代码 (Excel'代码'列)
    stock_name VARCHAR(50) NOT NULL,       -- 股票名称 (Excel'名称'列)
    industry VARCHAR(100),                 -- ⭐板块分类 (Excel'行业'列)
    last_updated TIMESTAMP                 -- 最后更新时间
);
```

**⭐ `industry`字段说明**:
- Excel列名：'行业'
- 实际含义：**板块分类** (不是传统意义的行业)
- 示例值：退货、食品、建材、化学、电气、纺织、农业、机械...
- **用途**：可以基于此字段进行板块成分股分组分析

**索引**:
- `PRIMARY KEY`: stock_code
- `GIN索引`: stock_name (模糊查询)
- `GIN索引`: stock_code (模糊查询)

**数据规模**: ~5,435条

---

#### 表2: `daily_stock_data` - 每日股票数据表

存储所有83个技术指标的每日数据

**关键字段**:
```sql
id BIGSERIAL PRIMARY KEY
stock_code VARCHAR(10) REFERENCES stocks(stock_code)
date DATE NOT NULL
rank INTEGER NOT NULL
```

**技术指标** (共83个字段):

| 类别 | 主要字段 |
|------|---------|
| **基础** | total_score, open/high/low/close_price |
| **涨跌** | jump, price_change |
| **成交** | volume, turnover_rate_percent |
| **量能** | volume_days, avg_volume_ratio_50 |
| **波动** | volatility, volatile_consec |
| **市值** | market_cap_billions |
| **MACD** | dif, dem, histgram, macd_signal |
| **KDJ** | k_kdj, slowk, slowkdj_signal |
| **RSI** | rsi, rsi_consec |
| **CCI** | cci_neg_90, cci_pos_90 |
| **布林带** | bands_lower/middle/upper |
| **DMI** | adx, plus_di, pdi_adx |
| **OBV** | obv |

**索引**:
- `UNIQUE INDEX`: (stock_code, date) - 防止重复导入 ⚠️
- `INDEX`: (date, rank) - 优化排名查询

**数据规模**: ~27,145条 (5天数据)

---

#### 表3: `sectors` - 板块主表

**数据源**: `*_allbk_sma_feature_color.xlsx` (板块Excel)

存储板块基本信息（独立于股票数据）

```sql
CREATE TABLE sectors (
    id BIGSERIAL PRIMARY KEY,
    sector_name VARCHAR(100) NOT NULL UNIQUE  -- Excel'代码'列 ⚠️
);
```

**⚠️ 特殊说明**:
- **Excel'代码'列存储的是板块名称**，而非代码！
- 示例值：工程建设、社区团购、转基因、中药、疫苗...
- Excel'名称'列固定为`none`，不导入
- **与`stocks.industry`字段不是同一套分类体系**

**数据规模**: ~500+个板块

---

#### 表4: `daily_sector_data` - 每日板块数据表

**数据源**: `*_allbk_sma_feature_color.xlsx` (板块Excel)

存储板块的每日技术指标 (81个字段)

**关键特点**:
- 与股票表字段基本相同
- 无`jump`字段（板块无跳空概念）
- 无`market_cap_billions`字段（板块无市值）
- **独立的板块技术指标，无法追溯包含哪些股票**（版权限制）

**数据规模**: ~1,430条 (3天数据)

---

### 2.3 数据关系

```
═══════════════════════════════════════
股票数据系统 (可分组分析)
═══════════════════════════════════════
stocks (1) ----< (N) daily_stock_data
  ├─ stock_code (PK) ← stock_code (FK)
  └─ industry (板块分类) ← 可用于分组
     示例: "退货"、"食品"、"建材"


═══════════════════════════════════════
板块数据系统 (独立技术指标)
═══════════════════════════════════════
sectors (1) ----< (N) daily_sector_data
  └─ id (PK) ← sector_id (FK)
     sector_name: "工程建设"、"社区团购"


⚠️ 注意：两个系统完全独立，无外键关联
```

---

## 3. 后端架构

### 3.1 目录结构

```
backend/app/
├── main.py                    # FastAPI入口
├── config.py                  # 配置
├── database.py                # 数据库连接 (⚠️不提交)
├── db_models.py               # ORM模型
│
├── core/                      # 核心
│   ├── startup_checks.py     # 启动检查
│   └── preload_cache.py      # 预加载缓存
│
├── models/                    # API响应模型
│   ├── analysis.py
│   ├── industry.py
│   ├── sector.py
│   └── stock.py
│
├── routers/                   # API路由
│   ├── analysis.py           # 热点分析
│   ├── stock.py              # 股票查询
│   ├── industry.py           # 行业分析
│   ├── sector.py             # 板块分析
│   ├── rank_jump.py          # 排名跳变
│   ├── steady_rise.py        # 稳步上升
│   └── cache_mgmt.py         # 缓存管理
│
├── services/                  # 业务逻辑
│   ├── analysis_service_db.py
│   ├── industry_service_db.py
│   ├── sector_service_db.py
│   ├── stock_service_db.py
│   ├── rank_jump_service_db.py
│   ├── steady_rise_service_db.py
│   ├── memory_cache.py        # 内存缓存
│   └── db_data_loader.py      # 数据加载
│
└── utils/                     # 工具
    ├── cache.py
    ├── ttl_cache.py
    └── dedup.py
```

### 3.2 核心模块

#### 3.2.1 应用入口 (`main.py`)

**功能**:
- FastAPI应用初始化
- CORS中间件配置
- 路由注册
- 请求日志中间件
- 生命周期管理

**启动流程**:
1. 执行启动检查
2. 预加载缓存
3. 注册路由
4. 启动服务器

---

#### 3.2.2 服务层设计

**设计模式**: Service Layer Pattern

| 服务 | 职责 |
|------|------|
| `analysis_service_db.py` | 热点分析、周期分析 |
| `stock_service_db.py` | 股票查询、历史数据 |
| `industry_service_db.py` | 行业统计、趋势、加权分析 |
| `sector_service_db.py` | 板块排名、趋势、详情 |
| `rank_jump_service_db.py` | 排名跳变检测 |
| `steady_rise_service_db.py` | 稳步上升检测 |
| `memory_cache.py` | 全量内存缓存管理 |

---

### 3.3 缓存架构 (v0.2.5) ⭐

#### 三层缓存体系

```
L1: 内存缓存 (memory_cache)
├─ 全量股票基础信息 (5435条)
├─ 全量每日数据 (27145条)
├─ 全量板块数据 (1430条)
├─ 启动时加载，运行时只读
└─ 性能: <1ms

L2: TTL缓存 (TTLCache)
├─ 计算结果缓存 (30分钟TTL)
├─ 行业分析、排名跳变等
└─ 性能: <5ms

L3: 数据库 (PostgreSQL)
├─ 仅在启动时访问
├─ 运行时零数据库查询
└─ 性能: 50-1500ms (不访问)
```

#### 性能对比

| API | 优化前 | 优化后 | 提升 |
|-----|--------|--------|------|
| 获取日期 | 50ms | 2ms | 25x |
| 7日热点 | 1500ms | 10ms | 150x |
| 行业统计 | 1000ms | 30ms | 33x |
| 个股查询 | 100ms | 5ms | 20x |

---

## 4. 前端架构

### 4.1 目录结构

```
frontend/src/
├── App.js                     # 主应用
├── index.js                   # 入口
├── index.css                  # 全局样式
│
├── components/
│   ├── Header.js              # 顶部栏
│   ├── Sidebar.js             # 侧边栏
│   ├── ConfirmDialog.js       # 对话框
│   │
│   └── modules/               # 功能模块
│       ├── HotSpotsModule.js           # 最新热点
│       ├── StockQueryModule.js         # 股票查询
│       ├── IndustryWeightedModule.js   # 行业加权
│       ├── SectorTrendModule.js        # 板块趋势
│       ├── RankJumpModule.js           # 排名跳变
│       ├── SteadyRiseModule.js         # 稳步上升
│       └── index.js
│
├── constants/
│   └── config.js              # 配置 (API_BASE_URL)
│
└── utils/
    └── helpers.js             # 工具函数
```

### 4.2 主应用 (`App.js`)

**功能**:
- 整体布局管理
- 侧边栏状态
- 模块切换
- 暗色模式
- 移动端适配

**布局**:
```
┌────────────────────────────────────────┐
│  Header (顶部导航)                     │
├─────────┬──────────────────────────────┤
│         │                              │
│ Sidebar │  Module Content              │
│         │                              │
└─────────┴──────────────────────────────┘
```

### 4.3 功能模块

| 模块 | 文件 | 功能 |
|------|------|------|
| 最新热点 | `HotSpotsModule.js` | N日热点股票分析 |
| 股票查询 | `StockQueryModule.js` | 个股历史查询 |
| 行业加权 | `IndustryWeightedModule.js` | 加权热度分析 (新) |
| 板块趋势 | `SectorTrendModule.js` | 板块排名趋势 (新) |
| 排名跳变 | `RankJumpModule.js` | 排名剧烈跳变检测 |
| 稳步上升 | `SteadyRiseModule.js` | 稳步上升股票检测 |

### 4.4 配置管理

**API基础URL** (`constants/config.js`):
```javascript
export const API_BASE_URL = 
  process.env.NODE_ENV === 'development'
    ? 'http://localhost:8000'  // 开发
    : '';  // 生产 (Nginx代理)
```

**重要性**: 避免硬编码，支持环境切换 ⚠️

---

## 下一部分

请查看 **Part 2**: API接口、功能模块详解、数据流程、部署架构

---

**文档结束**
