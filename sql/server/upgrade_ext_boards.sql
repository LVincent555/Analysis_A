-- ============================================================
-- 外部板块模块 - 服务器升级脚本
-- 版本: v1.0.0
-- 日期: 2025-12-24
-- 说明: 补充 ext_boards.sql 中没有的表和字段
-- 
-- 执行顺序:
--   1. 先执行 ext_boards.sql（创建基础 ext_* 表）
--   2. 再执行本文件（补充缺失表和字段）
--   3. 最后导入数据
--
-- ⚠️ 重要：执行前请先备份数据库！
-- ============================================================

-- ============================================================
-- 1. board_blacklist 表 - 板块黑名单
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
COMMENT ON COLUMN board_blacklist.keyword IS '匹配关键词，支持模糊匹配';
COMMENT ON COLUMN board_blacklist.level IS 'BLACK=完全屏蔽, GRAY=降低权重';

-- ============================================================
-- 2. cache_stock_board_signal 表 - 个股板块信号缓存
-- ============================================================
CREATE TABLE IF NOT EXISTS cache_stock_board_signal (
    trade_date DATE NOT NULL,               -- 交易日期
    stock_code VARCHAR(10) NOT NULL,        -- 股票代码
    stock_name VARCHAR(50),                 -- 股票名称（冗余）
    market_rank INT,                        -- 市场排名
    total_score DECIMAL(10,4),              -- 原始总分
    signal_level VARCHAR(4),                -- 信号等级: S/A/B/NONE
    final_score DECIMAL(10,4),              -- 合成最终评分
    final_score_pct DECIMAL(10,8),          -- 最终评分百分位
    
    -- 最强驱动板块
    max_driver_board_id BIGINT,             -- 最强板块ID
    max_driver_name VARCHAR(100),           -- 最强板块名称
    max_driver_type VARCHAR(20),            -- 板块类型: industry/concept
    max_driver_heat_pct DECIMAL(10,8),      -- 最强板块热度百分位
    
    -- 主营行业
    primary_industry_id BIGINT,             -- 主营行业ID
    primary_industry_name VARCHAR(100),     -- 主营行业名称
    primary_industry_heat_pct DECIMAL(10,8),-- 主营行业热度百分位
    industry_safe BOOLEAN,                  -- 行业是否安全
    
    -- 板块共振
    board_exposure DECIMAL(10,6),           -- 板块曝光度
    board_count INT,                        -- 关联板块数量
    top_boards_json TEXT,                   -- TOP板块JSON
    dna_json TEXT,                          -- 完整DNA JSON
    
    -- 快照相关
    snap_date DATE,                         -- 快照寻址日期
    fallback_reason VARCHAR(100),           -- 回退原因（如果snap_date != trade_date）
    
    -- 时间戳
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    PRIMARY KEY (trade_date, stock_code)
);

COMMENT ON TABLE cache_stock_board_signal IS '个股板块信号缓存表 - 每日ETL计算后写入';
COMMENT ON COLUMN cache_stock_board_signal.signal_level IS '板块信号等级: S(顶级) A(优秀) B(良好) NONE(无信号)';
COMMENT ON COLUMN cache_stock_board_signal.final_score IS '合成评分 = w_stock*总分 + w_exposure*共振 + w_max*最强概念 (行业不安全时*惩罚系数)';
COMMENT ON COLUMN cache_stock_board_signal.industry_safe IS '主营行业热度是否达标(>= board_safe_pct)';
COMMENT ON COLUMN cache_stock_board_signal.snap_date IS '稀疏快照寻址日期，可能早于trade_date';

-- cache_stock_board_signal 索引
CREATE INDEX IF NOT EXISTS idx_cache_driver_board ON cache_stock_board_signal(trade_date, max_driver_board_id);
CREATE INDEX IF NOT EXISTS idx_cache_final_score ON cache_stock_board_signal(trade_date, final_score DESC);
CREATE INDEX IF NOT EXISTS idx_cache_market_rank ON cache_stock_board_signal(trade_date, market_rank);
CREATE INDEX IF NOT EXISTS idx_cache_signal_level ON cache_stock_board_signal(trade_date, signal_level);

-- ============================================================
-- 3. 扩展 ext_board_list 表
-- ============================================================
-- 添加宽基指数标记（区分 "沪深300成分股" 等宽指）
ALTER TABLE ext_board_list ADD COLUMN IF NOT EXISTS is_broad_index BOOLEAN DEFAULT FALSE;

COMMENT ON COLUMN ext_board_list.is_broad_index IS '是否宽基指数（如沪深300、中证500成分股等）';

-- ============================================================
-- 4. 扩展 ext_board_daily_snap 表
-- ============================================================
-- 添加贡献分数字段
ALTER TABLE ext_board_daily_snap ADD COLUMN IF NOT EXISTS contribution_score DECIMAL(20,8);

COMMENT ON COLUMN ext_board_daily_snap.contribution_score IS '该股票对板块的贡献分数';

-- 添加贡献分索引（用于热度计算）
CREATE INDEX IF NOT EXISTS idx_snap_contrib ON ext_board_daily_snap(board_id, date, contribution_score DESC);

-- ============================================================
-- 5. 扩展 ext_board_heat_daily 表
-- ============================================================
-- 添加分数标准差字段
ALTER TABLE ext_board_heat_daily ADD COLUMN IF NOT EXISTS score_stddev DECIMAL(10,4);

COMMENT ON COLUMN ext_board_heat_daily.score_stddev IS '板块内股票分数标准差（衡量分化程度）';

-- ============================================================
-- 6. 初始化 board_blacklist 数据
-- ============================================================
-- 常见需要过滤的板块关键词
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
-- 完成
-- ============================================================
SELECT '升级完成 - 请检查表结构' AS status;

-- 验证命令（取消注释执行）：
-- \d board_blacklist
-- \d cache_stock_board_signal
-- \d ext_board_list
-- \d ext_board_daily_snap
-- \d ext_board_heat_daily
