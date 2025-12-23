-- ============================================================
-- 外部板块多对多系统 - 增量更新脚本
-- 用途: 当前测试环境快速更新
-- 执行: psql -d your_db -f 004_ext_board_heat_update.sql
-- 日期: 2025-12-11
-- ============================================================

-- 1. 创建板块热度聚合表（如果不存在）
CREATE TABLE IF NOT EXISTS ext_board_heat_daily (
    trade_date  DATE NOT NULL,
    board_id    BIGINT NOT NULL REFERENCES ext_board_list(id) ON DELETE CASCADE,
    
    stock_count INT DEFAULT 0,              -- 当日成分股数量
    
    -- B/C 系聚合指标（基于 share_ij 分摊权重）
    b1_rank_sum    DECIMAL(20,8) DEFAULT 0, -- 排名加权总热度 Σ(share * 1/rank^k)
    b2_rank_avg    DECIMAL(20,8) DEFAULT 0, -- 排名加权密度 (B1 / count)
    c1_score_sum   DECIMAL(20,8) DEFAULT 0, -- 总分加权总热度 Σ(share * total_score)
    c2_score_avg   DECIMAL(20,8) DEFAULT 0, -- 总分加权密度 (C1 / count)
    
    -- 综合热度结果
    heat_raw       DECIMAL(20,8) DEFAULT 0, -- 归一化合成后的原始热度
    heat_pct       DECIMAL(10,8) DEFAULT 0, -- 当日全市场分位值 [0, 1]
    
    -- 预留字段（单针策略等）
    needle_density DECIMAL(10,4),
    avg_volume     DECIMAL(10,2),
    
    created_at     TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at     TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    PRIMARY KEY (trade_date, board_id)
);

-- 2. 创建索引（如果不存在）
CREATE INDEX IF NOT EXISTS idx_ext_heat_date ON ext_board_heat_daily(trade_date);
CREATE INDEX IF NOT EXISTS idx_ext_heat_board ON ext_board_heat_daily(board_id);
CREATE INDEX IF NOT EXISTS idx_ext_heat_pct ON ext_board_heat_daily(trade_date, heat_pct DESC);

-- 3. 添加板块相关系统配置项（如果不存在）
INSERT INTO system_configs (config_key, config_value, config_type, category, description)
VALUES 
    ('board_w_industry', '1.0', 'float', 'board', '类型权重：行业板块'),
    ('board_w_concept', '0.7', 'float', 'board', '类型权重：概念板块'),
    ('board_w_region', '0.5', 'float', 'board', '类型权重：地域板块'),
    ('board_safe_pct', '0.3', 'float', 'board', '防守线：行业分位低于此不安全'),
    ('board_hot_pct', '0.8', 'float', 'board', '进攻线：板块分位高于此算风口'),
    ('board_w_stock', '1.0', 'float', 'board', '合成权重：个股自身分'),
    ('board_w_exposure', '0.7', 'float', 'board', '合成权重：板块共振'),
    ('board_w_max_concept', '0.5', 'float', 'board', '合成权重：最强驱动'),
    ('board_penalty_unsafe', '0.5', 'float', 'board', '行业不安全惩罚系数'),
    ('board_signal_S_pct', '0.97', 'float', 'board', 'S级信号阈值'),
    ('board_signal_A_pct', '0.90', 'float', 'board', 'A级信号阈值'),
    ('board_signal_B_pct', '0.80', 'float', 'board', 'B级信号阈值'),
    ('board_heat_alpha', '0.4', 'float', 'board', '综合热度权重：B1'),
    ('board_heat_beta', '0.2', 'float', 'board', '综合热度权重：B2'),
    ('board_heat_gamma', '0.3', 'float', 'board', '综合热度权重：C2'),
    ('board_heat_delta', '0.1', 'float', 'board', '综合热度权重：本地板块')
ON CONFLICT (config_key) DO NOTHING;

-- 4. 完成提示
DO $$
BEGIN
    RAISE NOTICE '✅ 增量更新完成！已创建 ext_board_heat_daily 表和相关配置项';
END $$;
