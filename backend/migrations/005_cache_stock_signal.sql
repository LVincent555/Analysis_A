-- ============================================================
-- 个股板块信号缓存表
-- 用途: 存储每日计算的个股板块信号，避免SQL视图在稀疏快照下的性能问题
-- 执行: psql -d your_db -f 005_cache_stock_signal.sql
-- 日期: 2025-12-11
-- 版本: V1.0
-- ============================================================

-- 1. 创建缓存表
CREATE TABLE IF NOT EXISTS cache_stock_board_signal (
    trade_date          DATE NOT NULL,
    stock_code          VARCHAR(10) NOT NULL,
    
    -- 个股基础数据（冗余存储避免 JOIN）
    stock_name          VARCHAR(50),
    market_rank         INT,              -- 当日全市场排名
    total_score         DECIMAL(10,4),    -- 个股总分
    
    -- 板块信号结果
    signal_level        VARCHAR(4),       -- 'S' | 'A' | 'B' | 'NONE'
    final_score         DECIMAL(10,4),    -- 合成分（股+板块共振）
    
    -- 最强驱动板块（冗余名称避免二次查询）
    max_driver_board_id BIGINT,
    max_driver_name     VARCHAR(100),     -- 如 "锂电池"
    max_driver_type     VARCHAR(20),      -- 'industry' | 'concept'
    max_driver_heat_pct DECIMAL(10,8),    -- 该板块的热度分位
    
    -- 行业防守状态
    primary_industry_id BIGINT,           -- 主营行业 board_id
    primary_industry_name VARCHAR(100),
    primary_industry_heat_pct DECIMAL(10,8),
    industry_safe       BOOLEAN,          -- 行业热度 > safe_pct?
    
    -- 板块共振详情（JSON存储，便于扩展）
    board_exposure      DECIMAL(10,6),    -- 板块共振强度 Σ(share * heat_pct)
    board_count         INT,              -- 该股关联板块数
    top_boards_json     TEXT,             -- 前N个最热板块JSON [{id, name, type, heat_pct}]
    
    -- 元数据
    snap_date           DATE,             -- 使用的快照日期（可能与trade_date不同）
    created_at          TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at          TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    PRIMARY KEY (trade_date, stock_code)
);

-- 2. 创建索引
CREATE INDEX IF NOT EXISTS idx_cache_signal_level ON cache_stock_board_signal(trade_date, signal_level);
CREATE INDEX IF NOT EXISTS idx_cache_final_score ON cache_stock_board_signal(trade_date, final_score DESC);
CREATE INDEX IF NOT EXISTS idx_cache_market_rank ON cache_stock_board_signal(trade_date, market_rank);
CREATE INDEX IF NOT EXISTS idx_cache_driver_board ON cache_stock_board_signal(trade_date, max_driver_board_id);

-- 3. 添加注释
COMMENT ON TABLE cache_stock_board_signal IS '个股板块信号缓存表 - 每日ETL计算后写入';
COMMENT ON COLUMN cache_stock_board_signal.signal_level IS '板块信号等级: S(顶级) A(优秀) B(良好) NONE(无信号)';
COMMENT ON COLUMN cache_stock_board_signal.final_score IS '合成评分 = w_stock*总分 + w_exposure*共振 + w_max*最强概念 (行业不安全时*惩罚系数)';
COMMENT ON COLUMN cache_stock_board_signal.industry_safe IS '主营行业热度是否达标(>= board_safe_pct)';
COMMENT ON COLUMN cache_stock_board_signal.snap_date IS '稀疏快照寻址日期，可能早于trade_date';

-- 4. 完成确认
DO $$
BEGIN
    RAISE NOTICE '============================================';
    RAISE NOTICE '✅ cache_stock_board_signal 表创建完成';
    RAISE NOTICE '--------------------------------------------';
    RAISE NOTICE '  用途: 存储个股板块信号计算结果';
    RAISE NOTICE '  写入: task_board_heat.py ETL 脚本';
    RAISE NOTICE '  查询: /api/board-heat/stock/{code}';
    RAISE NOTICE '============================================';
END $$;
