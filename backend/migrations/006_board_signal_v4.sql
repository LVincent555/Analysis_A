-- 006_board_signal_v4.sql
-- V4.0 深度数据挖掘与可视化 - 数据库变更
-- 包含：黑/灰名单表、贡献分物理存储、DNA数据预缓存、全市场分位字段

-- 1. 新建 board_blacklist 表 (黑/灰名单)
CREATE TABLE IF NOT EXISTS board_blacklist (
    id SERIAL PRIMARY KEY,
    keyword VARCHAR(50) NOT NULL UNIQUE,
    level VARCHAR(20) DEFAULT 'BLACK', -- 'BLACK' (权重0) or 'GREY' (权重0.1)
    reason VARCHAR(100),
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 初始化黑名单/灰名单数据
INSERT INTO board_blacklist (keyword, level, reason) VALUES
('融资融券', 'BLACK', '资金通道类，对个股分析无意义'),
('转融通', 'BLACK', '资金通道类'),
('深股通', 'BLACK', '资金通道类'),
('沪股通', 'BLACK', '资金通道类'),
('港股通', 'BLACK', '资金通道类'),
('富时罗素', 'GREY', '指数成分类'),
('标准普尔', 'GREY', '指数成分类'),
('MSCI', 'GREY', '指数成分类'),
('证金持股', 'GREY', '机构持仓类'),
('基金重仓', 'GREY', '机构持仓类'),
('社保重仓', 'GREY', '机构持仓类'),
('QFII重仓', 'GREY', '机构持仓类'),
('险资重仓', 'GREY', '机构持仓类'),
('大盘股', 'GREY', '市值分类'),
('中盘股', 'GREY', '市值分类'),
('小盘股', 'GREY', '市值分类'),
('微盘股', 'GREY', '市值分类'),
('创业板综', 'GREY', '指数成分类'),
('上证180', 'GREY', '指数成分类'),
('上证380', 'GREY', '指数成分类'),
('HS300', 'GREY', '指数成分类'),
('沪深300', 'GREY', '指数成分类'),
('中证500', 'GREY', '指数成分类'),
('中证1000', 'GREY', '指数成分类'),
('预盈预增', 'BLACK', '业绩相关'),
('预亏预减', 'BLACK', '业绩相关'),
('业绩预告', 'BLACK', '业绩相关'),
('ST股', 'BLACK', '其他无效'),
('*ST', 'BLACK', '其他无效'),
('次新股', 'BLACK', '其他无效')
ON CONFLICT (keyword) DO UPDATE SET level = EXCLUDED.level;

-- 2. ext_board_daily_snap 表增强 (物理存储贡献分)
ALTER TABLE ext_board_daily_snap ADD COLUMN IF NOT EXISTS contribution_score DECIMAL(20,8);
-- 建立索引加速排序查询
CREATE INDEX IF NOT EXISTS idx_snap_contrib ON ext_board_daily_snap(board_id, date, contribution_score DESC);

-- 3. cache_stock_board_signal 表增强 (预缓存DNA和分位)
ALTER TABLE cache_stock_board_signal ADD COLUMN IF NOT EXISTS dna_json TEXT;
ALTER TABLE cache_stock_board_signal ADD COLUMN IF NOT EXISTS final_score_pct DECIMAL(10,8);
ALTER TABLE cache_stock_board_signal ADD COLUMN IF NOT EXISTS fallback_reason VARCHAR(100);

-- 4. ext_board_heat_daily 表增强 (分歧监测)
ALTER TABLE ext_board_heat_daily ADD COLUMN IF NOT EXISTS score_stddev DECIMAL(10,4);

-- 5. 更新系统配置权重 (根据 V3.5 建议)
-- 个股自身分权重提高，板块共振权重降低
UPDATE system_configs SET config_value = '1.5' WHERE config_key = 'board_w_stock';
UPDATE system_configs SET config_value = '0.5' WHERE config_key = 'board_w_exposure';
UPDATE system_configs SET config_value = '0.3' WHERE config_key = 'board_w_max_concept';

-- 6. ext_board_list 增加标记列 (方便前端过滤)
ALTER TABLE ext_board_list ADD COLUMN IF NOT EXISTS is_broad_index BOOLEAN DEFAULT FALSE;
