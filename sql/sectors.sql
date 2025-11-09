/*
-- ===================================================================
-- 数据库扩展脚本 (2025-11-07) - [最终规范化版]
-- 新增: 创建 sectors 和 daily_sector_data 表
-- 目的: 高效存储 500+ 板块的每日指标数据
-- 
-- [重要说明]
-- 1. 板块数据与股票数据完全独立，无关联关系
-- 2. 股票数据 → main.sql (stocks + daily_stock_data)
-- 3. 板块数据 → sectors.sql (sectors + daily_sector_data)
-- 4. 股票Excel中的'行业'字段（如：退货、食品、建材）是板块分类
-- 5. 板块Excel中的'代码'列存储的是板块名称（如：工程建设、社区团购）
-- ===================================================================
*/

/* -- 步骤 1: 创建 sectors 表 (板块主表)
   -- 数据源：*_allbk_sma_feature_color.xlsx (板块数据Excel，约300KB)
   -- 目的：存储 500+ 板块的基本信息，消除冗余，支持模糊查询
   -- Excel列映射：
   --   Excel'代码'列 (如: 工程建设)  → sector_name 
   --   Excel'名称'列 (固定值: none)  → 不导入（无意义字段）
*/
CREATE TABLE IF NOT EXISTS sectors (
    id BIGSERIAL PRIMARY KEY,           -- 自动递增的数字ID (例如 1)
    sector_name VARCHAR(100) NOT NULL,  -- Excel'代码'列 (板块名称，如：工程建设、社区团购、转基因)
    
    -- 索引：确保板块名称不重复，并加速按名称查找
    CONSTRAINT uq_sector_name UNIQUE (sector_name)
);

/* -- 索引：为板块名称创建模糊查询索引 (pg_trgm)
   -- (请确保你已执行过 CREATE EXTENSION IF NOT EXISTS pg_trgm;)
*/
CREATE INDEX IF NOT EXISTS idx_sectors_name_trgm 
    ON sectors USING gin (sector_name gin_trgm_ops);


/* -- 步骤 2: 创建 daily_sector_data 表 (全量每日板块数据)
   -- 数据源：*_allbk_sma_feature_color.xlsx (板块数据Excel，约300KB)
   -- 目的：存储板块Excel中的所有81个技术指标，通过 sector_id 关联
   -- [注意] 相比股票数据，去掉了'jump'字段和'总市值(亿)'字段
   -- Excel列与数据库字段完全对应，详见下方注释
*/
CREATE TABLE IF NOT EXISTS daily_sector_data (
    id BIGSERIAL PRIMARY KEY,  -- 自动递增ID
    
    -- === 关键关联字段 ===
    sector_id BIGINT NOT NULL REFERENCES sectors(id) ON DELETE CASCADE, -- 关联到 sectors 表的数字ID
    date DATE NOT NULL,              -- 日期
    rank INTEGER NOT NULL,           -- 排名 (来自Excel行号 1, 2, 3...)

    -- === Excel 中所有列 (已转换SQL列名, DECIMAL(30, 10) 保持一致) ===
    total_score DECIMAL(30, 10),      -- '总分'
    open_price DECIMAL(30, 10),       -- '开盘'
    high_price DECIMAL(30, 10),       -- '最高'
    low_price DECIMAL(30, 10),        -- '最低'
    close_price DECIMAL(30, 10),      -- 'close'
    
    /* -- 'jump' 和 '总市值(亿)' 已根据你的板块数据移除 -- */
    
    price_change DECIMAL(30, 10),     -- '涨跌幅'
    turnover_rate_percent DECIMAL(30, 10), -- '换手率%'
    volume_days DECIMAL(30, 10),      -- '放量天数'
    avg_volume_ratio_50 DECIMAL(30, 10), -- '平均量比_50天'
    volume BIGINT,                    -- '成交量'
    volume_days_volume DECIMAL(30, 10), -- '放量天数_volume'
    avg_volume_ratio_50_volume DECIMAL(30, 10), -- '平均量比_50天_volume'
    volatility DECIMAL(30, 10),       -- '波动率'
    volatile_consec INTEGER,          -- 'volatile_consec'
    beta DECIMAL(30, 10),             -- 'BETA'
    beta_consec INTEGER,              -- 'BETA_consec'
    correlation DECIMAL(30, 10),      -- '相关性'
    long_term DECIMAL(30, 10),        -- '长期'
    short_term INTEGER,               -- '短期'
    overbought INTEGER,               -- '超买'
    oversold INTEGER,                 -- '超卖'
    macd_signal DECIMAL(30, 10),      -- 'macd_signal'
    slowkdj_signal DECIMAL(30, 10),   -- 'slowkdj_signal'
    lon_lonma DECIMAL(30, 10),        -- 'lon_lonma'
    lon_consec INTEGER,               -- 'lon_consec'
    lon_0 DECIMAL(30, 10),            -- 'lon_0'
    loncons_consec INTEGER,           -- 'loncons_consec'
    lonma_0 DECIMAL(30, 10),          -- 'lonma_0'
    lonmacons_consec INTEGER,         -- 'lonmacons_consec'
    dma DECIMAL(30, 10),              -- 'dma'
    dma_consec INTEGER,               -- 'dma_consec'
    dif_dem DECIMAL(30, 10),          -- 'dif_dem'
    macd_consec INTEGER,              -- 'macd_consec'
    dif_0 DECIMAL(30, 10),            -- 'dif_0'
    macdcons_consec INTEGER,          -- 'macdcons_consec'
    dem_0 DECIMAL(30, 10),            -- 'dem_0'
    demcons_consec INTEGER,           -- 'demcons_consec'
    pdi_adx DECIMAL(30, 10),          -- 'pdi_adx'
    dmiadx_consec INTEGER,            -- 'dmiadx_consec'
    pdi_ndi DECIMAL(30, 10),          -- 'pdi_ndi'
    dmi_consec INTEGER,               -- 'dmi_consec'
    obv BIGINT,                       -- 'obv'
    obv_consec INTEGER,               -- 'obv_consec'
    k_kdj DECIMAL(30, 10),            -- 'k_kdj'
    slowkdj_consec INTEGER,           -- 'slowkdj_consec'
    rsi DECIMAL(30, 10),              -- 'rsi'
    rsi_consec INTEGER,               -- 'rsi_consec'
    cci_neg_90 DECIMAL(30, 10),       -- 'cci_-90'
    cci_lower_consec INTEGER,         -- 'cci_lower_consec'
    cci_pos_90 DECIMAL(30, 10),       -- 'cci_90'
    cci_upper_consec INTEGER,         -- 'cci_upper_consec'
    bands_lower DECIMAL(30, 10),      -- 'bands_lower'
    bands_lower_consec INTEGER,       -- 'bands_lower_consec'
    bands_middle DECIMAL(30, 10),     -- 'bands_middle'
    bands_middle_consec INTEGER,      -- 'bands_middle_consec'
    bands_upper DECIMAL(30, 10),      -- 'bands_upper'
    bands_upper_consec INTEGER,       -- 'bands_upper_consec'
    lon_lonma_diff DECIMAL(30, 10),   -- 'lon_lonma_diff'
    lon DECIMAL(30, 10),              -- 'lon'
    lonma DECIMAL(30, 10),            -- 'lonma'
    histgram DECIMAL(30, 10),         -- 'histgram'
    dif DECIMAL(30, 10),              -- 'dif'
    dem DECIMAL(30, 10),              -- 'dem'
    adx DECIMAL(30, 10),              -- 'ADX'
    plus_di DECIMAL(30, 10),          -- 'PLUS_DI'
    obv_2 BIGINT,                     -- 'OBV' (重复列名)
    slowk DECIMAL(30, 10),            -- 'slowk'
    rsi_2 DECIMAL(30, 10),            -- 'RSI' (重复列名)
    cci_neg_90_2 DECIMAL(30, 10),     -- 'CCI_-90' (重复列名)
    cci_pos_90_2 DECIMAL(30, 10),     -- 'CCI_90' (重复列名)
    lower_band DECIMAL(30, 10),       -- 'lower'
    middle_band DECIMAL(30, 10),      -- 'middle'
    upper_band DECIMAL(30, 10),       -- 'upper'
    lst_close DECIMAL(30, 10),        -- 'lst_close'
    code2 VARCHAR(20),                -- 'code2'
    name2 VARCHAR(50),                -- 'name2'
    zhangdiefu2 DECIMAL(30, 10),      -- 'zhangdiefu2'
    volume_consec2 DECIMAL(30, 10),   -- 'volume_consec2'
    volume_50_consec2 DECIMAL(30, 10) -- 'volume_50_consec2'
);

/* -- 步骤 3: 为新表创建性能索引
*/

/* -- 索引 1: 优化「查询单个板块历史」
   -- 并且【防止】 (板块ID, 日期) 的数据被重复导入
*/
CREATE UNIQUE INDEX IF NOT EXISTS idx_daily_sector_date_unique 
    ON daily_sector_data (sector_id, date);

/* -- 索引 2: 优化「查询每日板块排名」
   -- 极大加速按日期和排名的查询
*/
CREATE INDEX IF NOT EXISTS idx_daily_sector_date_rank 
    ON daily_sector_data (date, rank);

/*
-- ===================================================================
-- 脚本执行完毕
-- ===================================================================
*/