-- ============================================================
-- 外部板块数据扩展模块 - 完整表结构
-- 版本: v1.0.0
-- 日期: 2025-12-10
-- 说明: 引入真实世界板块数据（东财 EM / 同花顺 THS），无侵入式设计
--
-- 设计原则:
--   1. 不修改现有 stocks / daily_stock_data / sectors / daily_sector_data
--   2. 所有新表以 ext_ 前缀标识
--   3. 支持历史回溯（股票-板块关系按日期快照）
--   4. 可扩展（未来可加入 Wind / 聚宽等数据源）
--
-- 依赖:
--   - main.sql 中的 stocks 表 (stock_code 字段)
--   - sectors.sql 中的 sectors 表 (用于桥接映射)
--   - pg_trgm 扩展 (用于板块名称模糊查询)
-- ============================================================

-- 确保 pg_trgm 扩展已启用（main.sql 中已创建，这里做兼容检查）
CREATE EXTENSION IF NOT EXISTS pg_trgm;

-- ============================================================
-- 1. ext_providers - 数据源表
-- ============================================================
-- 用途: 区分不同数据来源（东财、同花顺、未来可扩展）
-- 数据量: 极小（2-5 条）
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
-- 2. ext_board_list - 外部板块主表
-- ============================================================
-- 用途: 存储真实世界的板块列表（东财/同花顺的行业、概念板块）
-- 数据量: 约 1000-2000 条（EM ~500 + THS ~500-1000）
CREATE TABLE IF NOT EXISTS ext_board_list (
    id BIGSERIAL PRIMARY KEY,
    provider_id INT NOT NULL REFERENCES ext_providers(id) ON DELETE CASCADE,
    board_code VARCHAR(50) NOT NULL,        -- 板块代码: 'BK0425', 'BK0493'
    board_name VARCHAR(200) NOT NULL,       -- 板块名称: '半导体', '人工智能'
    board_type VARCHAR(50),                 -- 板块类型: 'industry'(行业), 'concept'(概念), 'region'(地域)
    stock_count INT DEFAULT 0,              -- 成分股数量（冗余字段，方便查询）
    is_active BOOLEAN DEFAULT TRUE,         -- 是否活跃（有些板块可能被下架）
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    -- 唯一约束: 同一数据源下板块代码唯一
    CONSTRAINT uq_ext_board_source_code UNIQUE (provider_id, board_code)
);

-- 索引: 按数据源查询板块列表
CREATE INDEX IF NOT EXISTS idx_ext_board_provider 
    ON ext_board_list (provider_id);

-- 索引: 按板块类型过滤
CREATE INDEX IF NOT EXISTS idx_ext_board_type 
    ON ext_board_list (board_type);

-- 索引: 板块名称模糊查询（GIN + trigram）
CREATE INDEX IF NOT EXISTS idx_ext_board_name_trgm 
    ON ext_board_list USING gin (board_name gin_trgm_ops);

-- 索引: 按更新时间排序（检测僵尸板块）
CREATE INDEX IF NOT EXISTS idx_ext_board_updated 
    ON ext_board_list (updated_at);

-- ============================================================
-- 3. ext_board_daily_snap - 股票-板块关系每日快照表（核心大表）
-- ============================================================
-- 用途: 记录"某天、某股票、属于哪个板块"的历史关系
-- 数据量: 约 2-3 万条/天（500板块 × 50成分股平均）
-- 
-- 设计要点:
--   - 三元组主键 (stock_code, board_id, date) 保证幂等
--   - 外键关联 stocks 表，确保数据一致性
--   - board_rank / weight 预留扩展位（指数成分权重）
CREATE TABLE IF NOT EXISTS ext_board_daily_snap (
    stock_code VARCHAR(10) NOT NULL REFERENCES stocks(stock_code) ON DELETE CASCADE,
    board_id BIGINT NOT NULL REFERENCES ext_board_list(id) ON DELETE CASCADE,
    date DATE NOT NULL,
    board_rank INTEGER,                     -- 股票在板块内的排名（可选）
    weight DECIMAL(10, 6),                  -- 权重（指数/ETF成分股用，可选）
    
    -- 三元组主键: 保证同一天同一股票同一板块只有一条记录
    PRIMARY KEY (stock_code, board_id, date)
);

-- 索引: 查询某板块某天的所有成分股
CREATE INDEX IF NOT EXISTS idx_ext_daily_query 
    ON ext_board_daily_snap (board_id, date);

-- 索引: 查询某股票的历史板块归属
CREATE INDEX IF NOT EXISTS idx_ext_daily_stock_history 
    ON ext_board_daily_snap (stock_code, date);

-- 索引: 按日期清理/分析
CREATE INDEX IF NOT EXISTS idx_ext_daily_date 
    ON ext_board_daily_snap (date);

-- ============================================================
-- 4. ext_board_local_map - 外部板块与本地板块的桥接表
-- ============================================================
-- 用途: 将真实板块(ext_board_list)映射到Excel导入的板块(sectors)
-- 数据量: 约 300-500 条（仅 EM 板块中与 sectors 重名的部分）
--
-- 设计要点:
--   - 不修改 sectors 表结构
--   - 支持自动匹配(auto) 和 人工校正(manual)
--   - THS 板块可能没有对应的 sectors，此表记录为空是正常的
CREATE TABLE IF NOT EXISTS ext_board_local_map (
    ext_board_id BIGINT NOT NULL REFERENCES ext_board_list(id) ON DELETE CASCADE,
    local_sector_id BIGINT NOT NULL REFERENCES sectors(id) ON DELETE CASCADE,
    match_type VARCHAR(20) DEFAULT 'auto',  -- 匹配类型: 'auto'(自动), 'manual'(人工), 'fuzzy'(模糊)
    confidence DECIMAL(5, 2),               -- 匹配置信度 (0-100)
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_by VARCHAR(50),                 -- 人工修改者
    
    -- 复合主键: 一个外部板块可以映射到多个本地板块（反之亦然）
    PRIMARY KEY (ext_board_id, local_sector_id)
);

-- 索引: 根据外部板块查找本地板块
CREATE INDEX IF NOT EXISTS idx_ext_map_ext_board 
    ON ext_board_local_map (ext_board_id);

-- 索引: 根据本地板块查找外部板块
CREATE INDEX IF NOT EXISTS idx_ext_map_local_sector 
    ON ext_board_local_map (local_sector_id);

-- ============================================================
-- 5. 辅助视图 - 方便日常查询
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
-- 6. 常用操作示例（注释形式保留）
-- ============================================================

/*
-- 自动生成板块映射（按名称精确匹配）
INSERT INTO ext_board_local_map (ext_board_id, local_sector_id, match_type, confidence)
SELECT b.id, s.id, 'auto', 100.00
FROM ext_board_list b
JOIN ext_providers p ON p.id = b.provider_id AND p.code = 'em'
JOIN sectors s ON s.sector_name = b.board_name
ON CONFLICT DO NOTHING;

-- 查询某板块某天的成分股及其技术指标
SELECT 
    s.stock_code,
    s.stock_name,
    d.close_price,
    d.price_change,
    d.total_score,
    d.rank
FROM ext_board_daily_snap snap
JOIN ext_board_list b ON b.id = snap.board_id
JOIN stocks s ON s.stock_code = snap.stock_code
JOIN daily_stock_data d ON d.stock_code = snap.stock_code AND d.date = snap.date
WHERE b.board_name = '人工智能'
  AND snap.date = '2025-01-10'
ORDER BY d.rank;

-- 查询某股票历史所属板块
SELECT 
    snap.date,
    b.board_name,
    b.board_type,
    p.name AS provider
FROM ext_board_daily_snap snap
JOIN ext_board_list b ON b.id = snap.board_id
JOIN ext_providers p ON p.id = b.provider_id
WHERE snap.stock_code = '000001'
ORDER BY snap.date DESC, b.board_name;

-- ETL: 删除某天数据后重新导入（幂等）
DELETE FROM ext_board_daily_snap WHERE date = '2025-01-10';
-- 然后 INSERT 新数据...

-- 统计各数据源板块数量
SELECT 
    p.name AS provider,
    b.board_type,
    COUNT(*) AS board_count
FROM ext_board_list b
JOIN ext_providers p ON p.id = b.provider_id
GROUP BY p.name, b.board_type
ORDER BY p.name, b.board_type;
*/

-- ============================================================
-- 完成
-- ============================================================
-- 执行后验证:
-- SELECT COUNT(*) FROM ext_providers;       -- 应该是 2
-- SELECT COUNT(*) FROM ext_board_list;      -- 初始为 0，等待 ETL 填充
-- SELECT COUNT(*) FROM ext_board_daily_snap;-- 初始为 0，等待 ETL 填充
-- SELECT COUNT(*) FROM ext_board_local_map; -- 初始为 0，等待映射
