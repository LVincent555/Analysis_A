# 📊 Stock Analysis App - 项目完整说明文档

> **文档目的**: 为AI助手（Claude等）提供完整的项目上下文，便于快速理解项目结构和配置需求

---

## 🎯 项目概述

### 项目名称
**Stock Analysis App** - A股股票数据分析系统

### 版本信息
- **当前版本**: v0.7.0
- **最后更新**: 2026-07-09

### 项目目标
通过分析每日股票排名数据，识别：
1. **热点股票** - 在多天内持续出现在TOP 100的股票
2. **排名跳变** - 排名大幅上升的股票
3. **稳步上升** - 排名稳定上升的股票
4. **行业趋势** - 各行业股票数量变化

### 核心特性
- ✅ 基于PostgreSQL的数据存储
- ✅ 支持北交所板块筛选（920开头）
- ✅ 自动数据导入和状态管理
- ✅ 内存缓存优化
- ✅ Docker容器化部署
- ✅ 响应式Web界面

---

## 🏗️ 技术架构

### 技术栈

**后端**:
- Python 3.10+
- FastAPI (Web框架)
- SQLAlchemy (ORM)
- PostgreSQL 15 (数据库)
- Pandas (数据处理)
- Gunicorn + Uvicorn (ASGI服务器)

**前端**:
- React 18
- Recharts (图表库)
- TailwindCSS (样式)
- Lucide React (图标)

**部署**:
- Docker + Docker Compose
- Nginx (反向代理)

### 系统架构图

```
┌─────────────────────────────────────────────────┐
│                   用户浏览器                     │
└────────────────────┬────────────────────────────┘
                     │ HTTP :80
                     ▼
┌─────────────────────────────────────────────────┐
│              Nginx (stock_web)                  │
│  - 静态文件服务                                  │
│  - API反向代理                                   │
└────────────────────┬────────────────────────────┘
                     │
      ┌──────────────┼──────────────┐
      │ /            │ /api         │
      ▼              ▼              │
┌──────────┐   ┌──────────────────────────────┐
│  React   │   │   FastAPI (stock_api)       │
│  前端    │   │   - RESTful API              │
│  Build   │   │   - 数据分析服务              │
└──────────┘   │   - 缓存管理                  │
               └──────────────┬───────────────┘
                              │
                              ▼
                ┌──────────────────────────────┐
                │   PostgreSQL (stock_db)      │
                │   - 股票数据                  │
                │   - 每日排名                  │
                └──────────────────────────────┘
```

### 数据流

```
Excel文件 (.xlsx)
    │
    ▼
导入脚本 (import_data_robust.py)
    │
    ▼
数据库 (PostgreSQL)
    │
    ├─► 预加载到缓存 (启动时)
    │
    ▼
分析服务 (analysis_service_db.py)
    │
    ├─► 热点分析
    ├─► 排名跳变
    ├─► 稳步上升
    └─► 行业统计
    │
    ▼
API路由 (/api/...)
    │
    ▼
前端展示 (React)
```

---

## 📁 项目结构

```
stock_analysis_app/
├── backend/                      # 后端代码
│   ├── app/
│   │   ├── core/                # 核心功能
│   │   │   ├── data_manager.py  # 数据管理
│   │   │   └── startup.py       # 启动逻辑
│   │   ├── models/              # Pydantic模型
│   │   │   ├── analysis.py
│   │   │   ├── industry.py
│   │   │   └── stock.py
│   │   ├── routers/             # API路由
│   │   │   ├── analysis.py      # 热点分析
│   │   │   ├── industry.py      # 行业分析
│   │   │   ├── rank_jump.py     # 排名跳变
│   │   │   ├── steady_rise.py   # 稳步上升
│   │   │   └── stock.py         # 股票详情
│   │   ├── services/            # 业务逻辑
│   │   │   ├── analysis_service_db.py
│   │   │   ├── db_data_loader.py
│   │   │   ├── industry_service_db.py
│   │   │   ├── rank_jump_service_db.py
│   │   │   ├── steady_rise_service_db.py
│   │   │   └── stock_service_db.py
│   │   ├── utils/               # 工具函数
│   │   │   ├── board_filter.py  # 板块筛选
│   │   │   ├── cache.py         # 缓存管理
│   │   │   └── date_utils.py    # 日期工具
│   │   ├── config.py            # 配置文件
│   │   ├── database.py          # 数据库连接
│   │   ├── db_models.py         # SQLAlchemy模型
│   │   └── main.py              # FastAPI应用
│   ├── scripts/
│   │   └── import_data_robust.py # 数据导入脚本
│   ├── Dockerfile               # 后端镜像
│   ├── docker-entrypoint.sh     # 启动脚本
│   ├── requirements.txt         # Python依赖
│   └── clear_cache.py           # 缓存清理
├── frontend/                    # 前端代码
│   ├── src/
│   │   ├── App.js               # 主应用
│   │   ├── index.js             # 入口
│   │   └── index.css            # 样式
│   ├── public/
│   │   └── index.html
│   └── package.json             # Node依赖
├── docker/                      # Docker配置
│   └── nginx/
│       ├── Dockerfile           # Nginx镜像
│       ├── nginx.conf           # Nginx主配置
│       └── default.conf         # 站点配置
├── data/                        # 数据目录
│   ├── *.xlsx                   # Excel数据文件
│   └── data_import_state.json   # 导入状态
├── sql/                         # SQL脚本
│   └── init.sql                 # 数据库初始化
├── docker-compose.yml           # Docker编排
├── .env.example                 # 环境变量模板
├── deploy.sh                    # 部署脚本
├── backup.sh                    # 备份脚本
├── README_DEPLOY.md             # 部署文档
└── PROJECT_OVERVIEW.md          # 本文档
```

---

## 🗄️ 数据库设计

### 表结构

#### 1. stocks（股票基础信息）
```sql
CREATE TABLE stocks (
    stock_code VARCHAR(10) PRIMARY KEY,
    stock_name VARCHAR(100),
    industry VARCHAR(100),
    market_cap_billions FLOAT
);
```

#### 2. daily_stock_data（每日股票数据）
```sql
CREATE TABLE daily_stock_data (
    id SERIAL PRIMARY KEY,
    stock_code VARCHAR(10) REFERENCES stocks(stock_code),
    date DATE NOT NULL,
    rank INTEGER,
    total_score FLOAT,
    open_price FLOAT,
    close_price FLOAT,
    high_price FLOAT,
    low_price FLOAT,
    price_change FLOAT,
    turnover_rate_percent FLOAT,
    volume BIGINT,
    -- ... 更多技术指标字段
    UNIQUE(stock_code, date)  -- 唯一约束
);

CREATE INDEX idx_daily_stock_code ON daily_stock_data(stock_code);
CREATE INDEX idx_daily_date ON daily_stock_data(date);
CREATE INDEX idx_daily_rank ON daily_stock_data(rank);
```

### 数据来源

**Excel文件格式**: `YYYYMMDD_data_sma_feature_color.xlsx`

**示例**: `20251106_data_sma_feature_color.xlsx`

**字段映射** (部分重要字段):
```python
COLUMN_MAPPING = {
    'CODE2': 'stock_code',
    'NAME2': 'stock_name',
    '日期': 'date',
    '排名': 'rank',
    '综合得分': 'total_score',
    '涨跌幅2': 'price_change',
    '换手率%': 'turnover_rate_percent',
    '行业': 'industry',
    # ... 更多字段
}
```

---

## 🔧 核心功能详解

### 1. 热点分析 (Hot Analysis)

**API**: `GET /api/analysis/period`

**参数**:
- `period`: 分析周期（天数）
- `max_count`: 每天TOP N股票数
- `board_type`: 板块类型（all/main/bjs）

**算法逻辑**:
1. 获取最近N天的数据
2. 识别最新一天的TOP N股票作为"锚定股票"
3. 回溯这些股票在整个周期内的出现次数
4. 过滤出现次数≥2次的股票
5. 按出现次数降序排序

**关键代码**:
```python
# backend/app/services/analysis_service_db.py
def analyze_period(self, period: int = 3, max_count: int = 100, board_type: str = 'main'):
    # 1. 获取最近N天日期
    # 2. 查询最新一天的TOP N股票（锚定）
    # 3. 回溯锚定股票在所有日期的数据
    # 4. 统计每只股票出现次数
    # 5. 过滤并排序
    # 6. 应用板块筛选
```

### 2. 排名跳变 (Rank Jump)

**API**: `GET /api/rank-jump`

**参数**:
- `period`: 分析周期
- `board_type`: 板块类型

**算法逻辑**:
1. 获取最近2天数据
2. 计算排名变化: `jump = 前一天排名 - 最新排名`
3. 筛选 jump > 0 的股票（排名上升）
4. 按跳变幅度降序排序

### 3. 稳步上升 (Steady Rise)

**API**: `GET /api/steady-rise`

**参数**:
- `period`: 分析周期
- `board_type`: 板块类型

**算法逻辑**:
1. 获取最近N天数据
2. 对每只股票，计算排名趋势（线性回归）
3. 筛选趋势为负（排名变小=上升）的股票
4. 按趋势斜率排序

### 4. 行业趋势 (Industry Trend)

**API**: `GET /api/industry/trend`

**参数**:
- `period`: 分析周期（默认14天）
- `top_n`: 每天TOP N股票

**功能**:
- 统计每天各行业在TOP N中的股票数量
- 展示多日期行业分布变化

### 5. 板块筛选 (Board Filter)

**筛选规则**:
```python
def should_filter_stock(stock_code: str, board_type: str) -> bool:
    """
    board_type取值:
    - 'all': 不筛选，显示所有股票
    - 'main': 主板，排除3/68/920开头
    - 'bjs': 北交所，只显示920开头
    """
    if board_type == 'all':
        return False
    elif board_type == 'main':
        return stock_code.startswith(('3', '68', '920'))
    elif board_type == 'bjs':
        return not stock_code.startswith('920')
    return False
```

---

## 🔄 数据导入流程

### 导入脚本

**文件**: `backend/scripts/import_data_robust.py`

**流程**:
1. 扫描 `data/` 目录下的Excel文件
2. 检查导入状态文件 `data_import_state.json`
3. 跳过已成功导入的文件
4. 对新文件:
   - 读取Excel数据
   - 标准化股票代码（补齐6位）
   - 创建/更新 stocks 表
   - 批量插入 daily_stock_data 表
   - 更新状态文件
5. 失败时自动回滚

### 状态管理

**文件**: `data/data_import_state.json`

```json
{
  "20251106": {
    "filename": "20251106_data_sma_feature_color.xlsx",
    "status": "success",
    "file_hash": "abc123...",
    "imported_count": 5429,
    "start_time": "2025-11-06T10:00:00",
    "end_time": "2025-11-06T10:00:30"
  }
}
```

### 自动导入（Docker）

容器启动时自动检查并导入：
```bash
# backend/docker-entrypoint.sh
if [ 数据库为空 ]; then
    python scripts/import_data_robust.py
fi
```

---

## 🚀 部署架构

### Docker容器

#### 1. postgres (stock_db)
- **镜像**: postgres:15-alpine
- **端口**: 5432
- **内存**: 600MB
- **卷**: postgres_data

#### 2. backend (stock_api)
- **镜像**: 自定义（Python 3.10-slim）
- **端口**: 8000 (内部)
- **内存**: 500MB
- **卷**: ./data, ./cache

#### 3. nginx (stock_web)
- **镜像**: 自定义（nginx:alpine + React build）
- **端口**: 80
- **内存**: 100MB

### 网络

所有容器在 `stock_network` 网桥网络中通信。

### 持久化

- **数据库数据**: Docker卷 `postgres_data`
- **Excel文件**: 主机目录 `./data`
- **缓存状态**: 主机目录 `./backend/cache`

---

## 🔐 配置说明

### 环境变量

**.env文件**:
```env
DATABASE_NAME=stock_analysis
DATABASE_USER=stock_user
DATABASE_PASSWORD=your_strong_password
WEB_PORT=80
```

### 配置文件

**backend/app/config.py**:
```python
VERSION = "0.2.1"
DATABASE_URL = f"postgresql://{user}:{password}@{host}:{port}/{database}"
FILE_PATTERNS = ["*_data_sma_feature_color.xlsx"]
DEFAULT_MAX_STOCKS = 100
TOP_N_STOCKS = 1000
CACHE_ENABLED = True
```

---

## 📊 API端点列表

| 端点 | 方法 | 说明 | 参数 |
|------|------|------|------|
| `/api/dates` | GET | 获取可用日期 | - |
| `/api/analysis/period` | GET | 热点分析 | period, max_count, board_type |
| `/api/rank-jump` | GET | 排名跳变 | period, board_type |
| `/api/steady-rise` | GET | 稳步上升 | period, board_type |
| `/api/industry/top1000` | GET | 行业统计 | - |
| `/api/industry/trend` | GET | 行业趋势 | period, top_n |
| `/api/stock/{code}` | GET | 股票详情 | stock_code |
| `/docs` | GET | API文档 | - |

---

## 🎨 前端组件

### 主要模块

1. **热点分析** (Hot Analysis)
   - 期数选择：2/3/5/7/14天
   - 板块选择：全部/主板/北交所
   - 行业分布图表
   - 股票列表

2. **股票查询** (Stock Query)
   - 股票代码搜索
   - 历史数据表格
   - 排名趋势图
   - 技术指标图

3. **排名跳变** (Rank Jump)
   - 期数选择
   - 板块选择
   - 跳变幅度排序

4. **稳步上升** (Steady Rise)
   - 期数选择
   - 板块选择
   - 趋势斜率排序

5. **行业趋势分析** (Industry Trend)
   - 14天行业变化
   - TOP 1000股票
   - 多行业对比图

---

## ⚡ 性能优化

### 缓存策略

1. **内存缓存**: 
   - 使用字典存储查询结果
   - 启动时预加载常用周期

2. **缓存键设计**:
   ```python
   cache_key = f"analysis_{period}_{max_count}_{board_type}"
   ```

3. **缓存失效**:
   - 手动清理：`python clear_cache.py`
   - 容器重启自动清理

### 数据库优化

1. **索引优化**:
   - stock_code, date, rank字段建立索引

2. **查询优化**:
   - 使用 `filter(date.in_([...]))` 批量查询
   - 避免N+1查询问题

3. **连接池**:
   ```python
   engine = create_engine(
       DATABASE_URL,
       pool_size=5,
       max_overflow=10
   )
   ```

### 前端优化

1. **代码分割**: 使用React lazy loading
2. **图表优化**: Recharts按需渲染
3. **请求防抖**: 搜索输入防抖
4. **Nginx压缩**: Gzip静态资源

---

## 🐛 已知问题

### 当前限制

1. **数据量限制**: 
   - 当前只有4天数据
   - 行业趋势14天需要更多历史数据

2. **并发限制**:
   - 2核2G配置下建议并发用户<10

3. **实时性**:
   - 数据非实时，需手动导入Excel

### 未来改进

1. **自动数据采集**: 定时从数据源抓取
2. **Redis缓存**: 多实例部署支持
3. **WebSocket**: 实时数据推送
4. **用户系统**: 登录和个人收藏

---

## 📝 重要说明

### 给AI助手的提示

1. **代码风格**:
   - 后端使用 type hints
   - 遵循 PEP 8
   - 使用 FastAPI 最佳实践

2. **修改注意**:
   - 修改数据库结构需更新 `db_models.py`
   - 修改API需同步更新前端调用
   - 板块筛选逻辑集中在 `board_filter.py`

3. **测试建议**:
   - 先在本地测试
   - 使用 `clear_cache.py` 清除缓存
   - 检查 `data_import_state.json` 状态

4. **部署注意**:
   - 确保 `.env` 文件配置正确
   - 检查端口占用
   - 监控内存使用

---

## 📞 常见任务

### 添加新API端点

1. 在 `backend/app/models/` 创建Pydantic模型
2. 在 `backend/app/services/` 实现业务逻辑
3. 在 `backend/app/routers/` 创建路由
4. 在 `backend/app/main.py` 注册路由
5. 前端调用新API

### 修改板块筛选逻辑

编辑 `backend/app/utils/board_filter.py`:
```python
def should_filter_stock(stock_code: str, board_type: str) -> bool:
    # 修改筛选规则
    pass
```

### 添加新的技术指标

1. 确保Excel中有该字段
2. 在 `import_data_robust.py` 添加字段映射
3. 在 `db_models.py` 添加字段
4. 数据库迁移或重新导入

---

## 🎯 快速开始检查清单

部署前检查：
- [ ] Docker和Docker Compose已安装
- [ ] `.env` 文件已配置
- [ ] Excel数据文件已放入 `./data`
- [ ] 端口80未被占用
- [ ] 服务器至少2G内存

部署后检查：
- [ ] 所有容器运行正常 (`docker-compose ps`)
- [ ] 数据库健康 (`docker-compose exec postgres pg_isready`)
- [ ] API可访问 (`curl http://localhost/api/dates`)
- [ ] 前端可访问 (`curl http://localhost`)
- [ ] 数据已导入 (检查日志)

---

## 📚 相关文档

- **部署文档**: README_DEPLOY.md
- **API文档**: http://localhost/api/docs (部署后)
- **Git仓库**: [填写您的仓库地址]

---

**文档版本**: 1.0  
**最后更新**: 2025-11-06  
**维护者**: [您的名字]
