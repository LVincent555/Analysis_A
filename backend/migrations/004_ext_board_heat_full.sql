-- ============================================================
-- 外部板块多对多系统 - 完整脚本
-- 用途: 服务器端全新部署或合并
-- 执行: psql -d your_db -f 004_ext_board_heat_full.sql
-- 日期: 2025-12-11
-- 版本: V1.0
-- ============================================================

-- ============================================================
-- 第一部分：基础表（如果不存在则创建）
-- ============================================================

-- 1.1 板块清单表
CREATE TABLE IF NOT EXISTS ext_board_list (
    id              BIGSERIAL PRIMARY KEY,
    provider_id     INT NOT NULL DEFAULT 1,         -- 1=东财, 2=同花顺
    board_code      VARCHAR(20) NOT NULL,           -- 业务编码 (BK0XXX)
    board_name      VARCHAR(100) NOT NULL,          -- 板块名称
    board_type      VARCHAR(20) DEFAULT 'concept',  -- 'industry' | 'concept' | 'region'
    stock_count     INT DEFAULT 0,                  -- 成分股数量
    is_active       BOOLEAN DEFAULT TRUE,
    created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    UNIQUE (provider_id, board_code)
);

CREATE INDEX IF NOT EXISTS idx_ext_board_type ON ext_board_list(board_type);
CREATE INDEX IF NOT EXISTS idx_ext_board_provider ON ext_board_list(provider_id);

-- 1.2 板块成分股每日快照表
CREATE TABLE IF NOT EXISTS ext_board_daily_snap (
    stock_code      VARCHAR(10) NOT NULL,
    board_id        BIGINT NOT NULL REFERENCES ext_board_list(id) ON DELETE CASCADE,
    date            DATE NOT NULL,
    board_rank      INT,                            -- 股票在板块内排名
    weight          DECIMAL(10,6),                  -- 权重（预留）
    
    PRIMARY KEY (date, stock_code, board_id)
);

CREATE INDEX IF NOT EXISTS idx_snap_date ON ext_board_daily_snap(date);
CREATE INDEX IF NOT EXISTS idx_snap_board ON ext_board_daily_snap(date, board_id);
CREATE INDEX IF NOT EXISTS idx_snap_stock ON ext_board_daily_snap(date, stock_code);

-- 1.3 板块与本地板块映射表（可选）
CREATE TABLE IF NOT EXISTS ext_board_local_map (
    id              BIGSERIAL PRIMARY KEY,
    ext_board_id    BIGINT REFERENCES ext_board_list(id) ON DELETE CASCADE,
    local_sector_id BIGINT,                         -- 关联本地 sectors 表
    match_type      VARCHAR(20) DEFAULT 'name',     -- 'name' | 'manual' | 'auto'
    confidence      DECIMAL(5,4) DEFAULT 1.0,       -- 匹配置信度
    created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    UNIQUE (ext_board_id, local_sector_id)
);

-- ============================================================
-- 第二部分：热度聚合表（新增）
-- ============================================================

-- 2.1 板块热度聚合结果表
CREATE TABLE IF NOT EXISTS ext_board_heat_daily (
    trade_date      DATE NOT NULL,
    board_id        BIGINT NOT NULL REFERENCES ext_board_list(id) ON DELETE CASCADE,
    
    stock_count     INT DEFAULT 0,                  -- 当日成分股数量
    
    -- B/C 系聚合指标（基于 share_ij 分摊权重）
    b1_rank_sum     DECIMAL(20,8) DEFAULT 0,        -- 排名加权总热度 Σ(share * 1/rank^k)
    b2_rank_avg     DECIMAL(20,8) DEFAULT 0,        -- 排名加权密度 (B1 / count)
    c1_score_sum    DECIMAL(20,8) DEFAULT 0,        -- 总分加权总热度 Σ(share * total_score)
    c2_score_avg    DECIMAL(20,8) DEFAULT 0,        -- 总分加权密度 (C1 / count)
    
    -- 综合热度结果
    heat_raw        DECIMAL(20,8) DEFAULT 0,        -- 归一化合成后的原始热度
    heat_pct        DECIMAL(10,8) DEFAULT 0,        -- 当日全市场分位值 [0, 1]
    
    -- 预留字段（单针策略等）
    needle_density  DECIMAL(10,4),
    avg_volume      DECIMAL(10,2),
    
    created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    PRIMARY KEY (trade_date, board_id)
);

CREATE INDEX IF NOT EXISTS idx_ext_heat_date ON ext_board_heat_daily(trade_date);
CREATE INDEX IF NOT EXISTS idx_ext_heat_board ON ext_board_heat_daily(board_id);
CREATE INDEX IF NOT EXISTS idx_ext_heat_pct ON ext_board_heat_daily(trade_date, heat_pct DESC);

-- ============================================================
-- 第三部分：系统配置项
-- ============================================================

-- 3.1 确保 system_configs 表存在
CREATE TABLE IF NOT EXISTS system_configs (
    id              BIGSERIAL PRIMARY KEY,
    config_key      VARCHAR(100) UNIQUE NOT NULL,
    config_value    TEXT,
    config_type     VARCHAR(20) DEFAULT 'string',   -- 'string' | 'int' | 'float' | 'bool' | 'json'
    category        VARCHAR(50) DEFAULT 'general',
    description     TEXT,
    created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 3.2 插入板块相关配置项
INSERT INTO system_configs (config_key, config_value, config_type, category, description)
VALUES 
    -- 类型权重（热度守恒分摊）
    ('board_w_industry', '1.0', 'float', 'board', '类型权重：行业板块（防守主线）'),
    ('board_w_concept', '0.7', 'float', 'board', '类型权重：概念板块（进攻副线）'),
    ('board_w_region', '0.5', 'float', 'board', '类型权重：地域板块（点缀）'),
    
    -- 信号阈值
    ('board_safe_pct', '0.3', 'float', 'board', '防守线：行业分位低于此视为不安全'),
    ('board_hot_pct', '0.8', 'float', 'board', '进攻线：板块分位高于此算热门风口'),
    
    -- 综合评分权重
    ('board_w_stock', '1.0', 'float', 'board', '合成权重：个股自身评分'),
    ('board_w_exposure', '0.7', 'float', 'board', '合成权重：板块共振强度'),
    ('board_w_max_concept', '0.5', 'float', 'board', '合成权重：最强概念驱动'),
    ('board_penalty_unsafe', '0.5', 'float', 'board', '行业不安全惩罚系数'),
    
    -- 信号等级阈值
    ('board_signal_S_pct', '0.97', 'float', 'board', 'S级板块信号阈值'),
    ('board_signal_A_pct', '0.90', 'float', 'board', 'A级板块信号阈值'),
    ('board_signal_B_pct', '0.80', 'float', 'board', 'B级板块信号阈值'),
    
    -- 热度聚合权重 (α/β/γ/δ)
    ('board_heat_alpha', '0.4', 'float', 'board', '综合热度权重：B1排名加权'),
    ('board_heat_beta', '0.2', 'float', 'board', '综合热度权重：B2排名密度'),
    ('board_heat_gamma', '0.3', 'float', 'board', '综合热度权重：C2总分密度'),
    ('board_heat_delta', '0.1', 'float', 'board', '综合热度权重：本地板块嫁接')
ON CONFLICT (config_key) DO UPDATE SET
    config_value = EXCLUDED.config_value,
    description = EXCLUDED.description,
    updated_at = CURRENT_TIMESTAMP;

-- ============================================================
-- 第四部分：辅助视图（可选）
-- ============================================================

-- 4.1 个股板块信号视图（简化版，完整逻辑在Python中实现）
-- CREATE OR REPLACE VIEW v_stock_board_signal_daily AS
-- SELECT ... (复杂逻辑由后端Python Service实现)

-- ============================================================
-- 第五部分：完成确认
-- ============================================================

DO $$
DECLARE
    board_count INT;
    snap_count INT;
    config_count INT;
BEGIN
    SELECT COUNT(*) INTO board_count FROM ext_board_list;
    SELECT COUNT(*) INTO snap_count FROM ext_board_daily_snap;
    SELECT COUNT(*) INTO config_count FROM system_configs WHERE category = 'board';
    
    RAISE NOTICE '============================================';
    RAISE NOTICE '✅ 外部板块多对多系统 - 数据库部署完成';
    RAISE NOTICE '--------------------------------------------';
    RAISE NOTICE '  板块清单表 ext_board_list: % 条记录', board_count;
    RAISE NOTICE '  成分股快照表 ext_board_daily_snap: % 条记录', snap_count;
    RAISE NOTICE '  热度聚合表 ext_board_heat_daily: 已创建';
    RAISE NOTICE '  系统配置项 (board): % 条', config_count;
    RAISE NOTICE '============================================';
END $$;
