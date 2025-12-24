-- ============================================================
-- 股票分析系统 - V0.6.0 数据库升级脚本
-- ============================================================
-- 
-- 版本: v0.6.0
-- 日期: 2025-12-24
-- 功能: 外部板块多对多分析系统 + 板块热度ETL
--
-- ============================================================
-- 使用说明
-- ============================================================
-- 
-- 适用场景: 从 v0.5.x 升级到 v0.6.0
-- 前置条件: 
--   - 数据库已有 stocks, daily_stock_data, sectors, daily_sector_data
--   - 数据库已有 users, user_sessions, roles 等用户模块表
--
-- 执行方式:
--   psql -U postgres -d db_20251106_analysis_a -f V0.6.0_数据库升级脚本.sql
--   
-- 或在 Navicat 中直接打开执行
--
-- ⚠️ 重要: 执行前请先备份数据库！
--   pg_dump -U postgres -d db_20251106_analysis_a > backup_before_v0.6.0.sql
--
-- ============================================================
-- 本次升级内容
-- ============================================================
--
-- 🆕 新增表:
--   - ext_providers        : 外部数据源（东财/同花顺）
--   - ext_board_list       : 外部板块列表
--   - ext_board_daily_snap : 股票-板块每日快照（核心大表）
--   - ext_board_heat_daily : 板块每日热度数据
--   - ext_board_local_map  : 外部板块→本地板块映射
--   - board_blacklist      : 板块黑名单
--   - cache_stock_board_signal : 个股板块信号缓存
--
-- 🆕 新增视图:
--   - v_ext_board_full         : 板块完整信息
--   - v_ext_board_stocks_latest: 最新板块成分股
--   - v_ext_board_mapping      : 板块映射关系
--
-- ============================================================

-- 开始事务
BEGIN;

-- ============================================================
-- PART 1: 基础依赖检查
-- ============================================================

-- 确保 pg_trgm 扩展已启用
CREATE EXTENSION IF NOT EXISTS pg_trgm;

-- ============================================================
-- PART 2: ext_providers - 数据源表
-- ============================================================
CREATE TABLE IF NOT EXISTS ext_providers (
    id SERIAL PRIMARY KEY,
    code VARCHAR(20) NOT NULL UNIQUE,       -- 数据源代码: 'em', 'ths', 'wind'
    name VARCHAR(50) NOT NULL,              -- 显示名称: '东方财富', '同花顺'
    description TEXT,                       -- 备注说明
    api_source VARCHAR(100),                -- 数据获取方式: 'akshare', 'crawler'
    is_active BOOLEAN DEFAULT TRUE,         -- 是否启用
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 初始化数据源
INSERT INTO ext_providers (code, name, description, api_source) VALUES
    ('em', '东方财富', '东财行业/概念板块，通过AKShare获取', 'akshare'),
    ('ths', '同花顺', '同花顺概念板块，通过AKShare获取', 'akshare')
ON CONFLICT (code) DO UPDATE SET
    name = EXCLUDED.name,
    description = EXCLUDED.description,
    api_source = EXCLUDED.api_source;

-- ============================================================
-- PART 3: ext_board_list - 外部板块主表
-- ============================================================
CREATE TABLE IF NOT EXISTS ext_board_list (
    id BIGSERIAL PRIMARY KEY,
    provider_id INT NOT NULL REFERENCES ext_providers(id) ON DELETE CASCADE,
    board_code VARCHAR(50) NOT NULL,        -- 板块代码: 'BK0425', 'BK0493'
    board_name VARCHAR(200) NOT NULL,       -- 板块名称: '半导体', '人工智能'
    board_type VARCHAR(50),                 -- 板块类型: 'industry'(行业), 'concept'(概念)
    stock_count INT DEFAULT 0,              -- 成分股数量（冗余字段）
    is_active BOOLEAN DEFAULT TRUE,         -- 是否活跃
    is_broad_index BOOLEAN DEFAULT FALSE,   -- 是否宽基指数
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    CONSTRAINT uq_ext_board_source_code UNIQUE (provider_id, board_code)
);

-- ext_board_list 索引
CREATE INDEX IF NOT EXISTS idx_ext_board_provider ON ext_board_list(provider_id);
CREATE INDEX IF NOT EXISTS idx_ext_board_type ON ext_board_list(board_type);
CREATE INDEX IF NOT EXISTS idx_ext_board_name_trgm ON ext_board_list USING gin(board_name gin_trgm_ops);
CREATE INDEX IF NOT EXISTS idx_ext_board_updated ON ext_board_list(updated_at);

-- 补充可能缺失的字段（幂等）
ALTER TABLE ext_board_list ADD COLUMN IF NOT EXISTS is_broad_index BOOLEAN DEFAULT FALSE;

-- ============================================================
-- PART 4: ext_board_daily_snap - 股票-板块每日快照表
-- ============================================================
CREATE TABLE IF NOT EXISTS ext_board_daily_snap (
    stock_code VARCHAR(10) NOT NULL REFERENCES stocks(stock_code) ON DELETE CASCADE,
    board_id BIGINT NOT NULL REFERENCES ext_board_list(id) ON DELETE CASCADE,
    date DATE NOT NULL,
    board_rank INTEGER,                     -- 股票在板块内的排名
    weight DECIMAL(10, 6),                  -- 权重（指数成分股用）
    contribution_score DECIMAL(20, 8),      -- 贡献分数
    
    PRIMARY KEY (stock_code, board_id, date)
);

-- ext_board_daily_snap 索引
CREATE INDEX IF NOT EXISTS idx_ext_daily_query ON ext_board_daily_snap(board_id, date);
CREATE INDEX IF NOT EXISTS idx_ext_daily_stock_history ON ext_board_daily_snap(stock_code, date);
CREATE INDEX IF NOT EXISTS idx_ext_daily_date ON ext_board_daily_snap(date);
CREATE INDEX IF NOT EXISTS idx_snap_contrib ON ext_board_daily_snap(board_id, date, contribution_score DESC);

-- 补充可能缺失的字段（幂等）
ALTER TABLE ext_board_daily_snap ADD COLUMN IF NOT EXISTS contribution_score DECIMAL(20, 8);

-- ============================================================
-- PART 5: ext_board_heat_daily - 板块每日热度表
-- ============================================================
CREATE TABLE IF NOT EXISTS ext_board_heat_daily (
    trade_date DATE NOT NULL,
    board_id BIGINT NOT NULL REFERENCES ext_board_list(id) ON DELETE CASCADE,
    stock_count INT DEFAULT 0,
    b1_rank_sum DECIMAL(20, 8) DEFAULT 0,   -- 排名加权总和
    b2_rank_avg DECIMAL(20, 8) DEFAULT 0,   -- 排名平均
    c1_score_sum DECIMAL(20, 8) DEFAULT 0,  -- 分数加权总和
    c2_score_avg DECIMAL(20, 8) DEFAULT 0,  -- 分数平均
    heat_raw DECIMAL(20, 8) DEFAULT 0,      -- 原始热度值
    heat_pct DECIMAL(10, 8) DEFAULT 0,      -- 热度百分位
    needle_density DECIMAL(10, 4),          -- 龙头密度
    avg_volume DECIMAL(10, 2),              -- 平均成交量
    score_stddev DECIMAL(10, 4),            -- 分数标准差
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    PRIMARY KEY (trade_date, board_id)
);

-- ext_board_heat_daily 索引
CREATE INDEX IF NOT EXISTS idx_ext_heat_board ON ext_board_heat_daily(board_id);
CREATE INDEX IF NOT EXISTS idx_ext_heat_date ON ext_board_heat_daily(trade_date);
CREATE INDEX IF NOT EXISTS idx_ext_heat_pct ON ext_board_heat_daily(trade_date, heat_pct DESC);

-- 补充可能缺失的字段（幂等）
ALTER TABLE ext_board_heat_daily ADD COLUMN IF NOT EXISTS score_stddev DECIMAL(10, 4);

-- ============================================================
-- PART 6: ext_board_local_map - 外部→本地板块映射表
-- ============================================================
CREATE TABLE IF NOT EXISTS ext_board_local_map (
    ext_board_id BIGINT NOT NULL REFERENCES ext_board_list(id) ON DELETE CASCADE,
    local_sector_id BIGINT NOT NULL REFERENCES sectors(id) ON DELETE CASCADE,
    match_type VARCHAR(20) DEFAULT 'auto',  -- 匹配类型: 'auto', 'manual', 'fuzzy'
    confidence DECIMAL(5, 2),               -- 匹配置信度 (0-100)
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_by VARCHAR(50),                 -- 人工修改者
    
    PRIMARY KEY (ext_board_id, local_sector_id)
);

-- ext_board_local_map 索引
CREATE INDEX IF NOT EXISTS idx_ext_map_ext_board ON ext_board_local_map(ext_board_id);
CREATE INDEX IF NOT EXISTS idx_ext_map_local_sector ON ext_board_local_map(local_sector_id);

-- ============================================================
-- PART 7: board_blacklist - 板块黑名单
-- ============================================================
CREATE TABLE IF NOT EXISTS board_blacklist (
    id SERIAL PRIMARY KEY,
    keyword VARCHAR(50) UNIQUE NOT NULL,    -- 关键词（唯一）
    level VARCHAR(20) DEFAULT 'BLACK',      -- 级别: BLACK(完全屏蔽) / GRAY(降权)
    reason VARCHAR(100),                    -- 屏蔽原因
    is_active BOOLEAN DEFAULT TRUE,         -- 是否生效
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

COMMENT ON TABLE board_blacklist IS '板块黑名单 - 过滤不需要的板块';

-- 初始化黑名单数据
INSERT INTO board_blacklist (keyword, level, reason) VALUES
    ('ST', 'BLACK', 'ST/退市风险股'),
    ('退市', 'BLACK', '退市相关'),
    ('摘帽', 'GRAY', '摘帽股票风险较高'),
    ('注册制次新', 'GRAY', '次新股波动大'),
    ('昨日', 'BLACK', '时效性板块，无分析价值'),
    ('连板', 'BLACK', '时效性板块，无分析价值'),
    ('涨停', 'BLACK', '时效性板块，无分析价值'),
    ('跌停', 'BLACK', '时效性板块，无分析价值'),
    ('融资融券', 'GRAY', '功能性分类，非主题'),
    ('深股通', 'GRAY', '功能性分类，非主题'),
    ('沪股通', 'GRAY', '功能性分类，非主题'),
    ('MSCI', 'GRAY', '指数成分股，非主题'),
    ('富时罗素', 'GRAY', '指数成分股，非主题')
ON CONFLICT (keyword) DO NOTHING;

-- ============================================================
-- PART 8: cache_stock_board_signal - 个股板块信号缓存
-- ============================================================
CREATE TABLE IF NOT EXISTS cache_stock_board_signal (
    trade_date DATE NOT NULL,               -- 交易日期
    stock_code VARCHAR(10) NOT NULL,        -- 股票代码
    stock_name VARCHAR(50),                 -- 股票名称（冗余）
    market_rank INT,                        -- 市场排名
    total_score DECIMAL(10, 4),             -- 原始总分
    signal_level VARCHAR(4),                -- 信号等级: S/A/B/NONE
    final_score DECIMAL(10, 4),             -- 合成最终评分
    final_score_pct DECIMAL(10, 8),         -- 最终评分百分位
    
    -- 最强驱动板块
    max_driver_board_id BIGINT,             -- 最强板块ID
    max_driver_name VARCHAR(100),           -- 最强板块名称
    max_driver_type VARCHAR(20),            -- 板块类型
    max_driver_heat_pct DECIMAL(10, 8),     -- 最强板块热度百分位
    
    -- 主营行业
    primary_industry_id BIGINT,             -- 主营行业ID
    primary_industry_name VARCHAR(100),     -- 主营行业名称
    primary_industry_heat_pct DECIMAL(10, 8),
    industry_safe BOOLEAN,                  -- 行业是否安全
    
    -- 板块共振
    board_exposure DECIMAL(10, 6),          -- 板块曝光度
    board_count INT,                        -- 关联板块数量
    top_boards_json TEXT,                   -- TOP板块JSON
    dna_json TEXT,                          -- 完整DNA JSON
    
    -- 快照相关
    snap_date DATE,                         -- 快照寻址日期
    fallback_reason VARCHAR(100),           -- 回退原因
    
    -- 时间戳
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    PRIMARY KEY (trade_date, stock_code)
);

COMMENT ON TABLE cache_stock_board_signal IS '个股板块信号缓存表 - 每日ETL计算后写入';
COMMENT ON COLUMN cache_stock_board_signal.signal_level IS '板块信号等级: S(顶级) A(优秀) B(良好) NONE(无信号)';
COMMENT ON COLUMN cache_stock_board_signal.final_score IS '合成评分 = w_stock*总分 + w_exposure*共振 + w_max*最强概念';
COMMENT ON COLUMN cache_stock_board_signal.industry_safe IS '主营行业热度是否达标(>= board_safe_pct)';

-- cache_stock_board_signal 索引
CREATE INDEX IF NOT EXISTS idx_cache_driver_board ON cache_stock_board_signal(trade_date, max_driver_board_id);
CREATE INDEX IF NOT EXISTS idx_cache_final_score ON cache_stock_board_signal(trade_date, final_score DESC);
CREATE INDEX IF NOT EXISTS idx_cache_market_rank ON cache_stock_board_signal(trade_date, market_rank);
CREATE INDEX IF NOT EXISTS idx_cache_signal_level ON cache_stock_board_signal(trade_date, signal_level);

-- ============================================================
-- PART 9: 视图
-- ============================================================

-- 视图: 板块完整信息（含数据源名称）
CREATE OR REPLACE VIEW v_ext_board_full AS
SELECT 
    b.id,
    b.board_code,
    b.board_name,
    b.board_type,
    b.stock_count,
    b.is_active,
    b.is_broad_index,
    b.updated_at,
    p.code AS provider_code,
    p.name AS provider_name
FROM ext_board_list b
JOIN ext_providers p ON p.id = b.provider_id;

-- 视图: 今日板块成分股（最新日期）
CREATE OR REPLACE VIEW v_ext_board_stocks_latest AS
SELECT 
    b.board_name,
    b.board_type,
    p.code AS provider_code,
    s.stock_code,
    s.stock_name,
    s.industry,
    snap.board_rank,
    snap.contribution_score,
    snap.date
FROM ext_board_daily_snap snap
JOIN ext_board_list b ON b.id = snap.board_id
JOIN ext_providers p ON p.id = b.provider_id
JOIN stocks s ON s.stock_code = snap.stock_code
WHERE snap.date = (SELECT MAX(date) FROM ext_board_daily_snap);

-- 视图: 外部板块与本地板块的映射关系
CREATE OR REPLACE VIEW v_ext_board_mapping AS
SELECT 
    b.board_name AS ext_board_name,
    b.board_code AS ext_board_code,
    p.code AS provider_code,
    sec.sector_name AS local_sector_name,
    m.match_type,
    m.confidence
FROM ext_board_local_map m
JOIN ext_board_list b ON b.id = m.ext_board_id
JOIN ext_providers p ON p.id = b.provider_id
JOIN sectors sec ON sec.id = m.local_sector_id;

-- ============================================================
-- PART 10: 新增系统配置项
-- ============================================================

-- 板块热度相关配置
INSERT INTO system_configs (config_key, config_value, config_type, category, description) VALUES
    ('board_safe_pct', '0.3', 'float', 'board_heat', '行业安全阈值（热度百分位）'),
    ('board_weight_stock', '0.4', 'float', 'board_heat', '个股总分权重'),
    ('board_weight_exposure', '0.3', 'float', 'board_heat', '板块曝光度权重'),
    ('board_weight_max', '0.3', 'float', 'board_heat', '最强板块权重'),
    ('board_penalty_unsafe', '0.7', 'float', 'board_heat', '行业不安全惩罚系数'),
    ('board_top_n', '5', 'int', 'board_heat', 'TOP板块展示数量'),
    ('board_signal_s_pct', '0.95', 'float', 'board_heat', 'S级信号阈值'),
    ('board_signal_a_pct', '0.85', 'float', 'board_heat', 'A级信号阈值'),
    ('board_signal_b_pct', '0.70', 'float', 'board_heat', 'B级信号阈值'),
    ('board_sync_hour', '18', 'int', 'board_heat', '每日同步时间（小时）'),
    ('board_cache_ttl', '3600', 'int', 'board_heat', '热度缓存TTL（秒）'),
    ('board_snap_sparse_days', '7', 'int', 'board_heat', '稀疏快照回溯天数'),
    ('board_industry_types', '["industry"]', 'json', 'board_heat', '作为行业的板块类型'),
    ('board_concept_types', '["concept"]', 'json', 'board_heat', '作为概念的板块类型'),
    ('board_blacklist_enabled', 'true', 'bool', 'board_heat', '启用板块黑名单'),
    ('board_broad_index_filter', 'true', 'bool', 'board_heat', '过滤宽基指数板块')
ON CONFLICT (config_key) DO NOTHING;

-- ============================================================
-- PART 11: 添加表注释
-- ============================================================

COMMENT ON TABLE ext_providers IS '外部数据源表 - 东财/同花顺等';
COMMENT ON TABLE ext_board_list IS '外部板块主表 - 真实世界板块';
COMMENT ON TABLE ext_board_daily_snap IS '股票-板块每日快照 - 核心多对多关系表';
COMMENT ON TABLE ext_board_heat_daily IS '板块每日热度 - ETL计算结果';
COMMENT ON TABLE ext_board_local_map IS '外部板块→本地板块映射';

-- 提交事务
COMMIT;

-- ============================================================
-- 升级完成
-- ============================================================
SELECT '✅ V0.6.0 数据库升级完成！' AS status;

-- ============================================================
-- 后续操作提示
-- ============================================================
-- 
-- 如果需要从本地迁移数据，请执行:
--
-- 1. 从本地导出数据:
--    pg_dump -U postgres -h 192.168.182.128 -d db_20251106_analysis_a \
--        --data-only \
--        --table=ext_providers \
--        --table=ext_board_list \
--        --table=ext_board_daily_snap \
--        --table=ext_board_heat_daily \
--        --table=ext_board_local_map \
--        --table=board_blacklist \
--        --table=cache_stock_board_signal \
--        > ext_boards_data.sql
--
-- 2. 导入到服务器:
--    psql -U postgres -d db_20251106_analysis_a -f ext_boards_data.sql
--
-- 3. 修复序列值:
--    SELECT setval('ext_providers_id_seq', (SELECT MAX(id) FROM ext_providers));
--    SELECT setval('ext_board_list_id_seq', (SELECT MAX(id) FROM ext_board_list));
--    SELECT setval('board_blacklist_id_seq', (SELECT MAX(id) FROM board_blacklist));
--
-- 4. 验证数据:
--    SELECT 'ext_board_list' AS t, COUNT(*) FROM ext_board_list
--    UNION ALL SELECT 'ext_board_daily_snap', COUNT(*) FROM ext_board_daily_snap
--    UNION ALL SELECT 'cache_stock_board_signal', COUNT(*) FROM cache_stock_board_signal;
--
-- ============================================================
