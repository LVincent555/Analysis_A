/*
-- ===================================================================
-- 股票分析系统 - 数据库初始化脚本 (PostgreSQL)
-- [最终合并版]
--
-- 1. 启用 pg_trgm 扩展
-- 2. 创建 stocks 主表
-- 3. 创建 daily_stock_data 表 (已使用 DECIMAL(30, 10) 修复)
-- 4. 创建所有性能索引
--
-- [重要说明]
-- 1. 股票数据与板块数据完全独立，无关联关系
-- 2. 股票数据 → main.sql (stocks + daily_stock_data)
-- 3. 板块数据 → sectors.sql (sectors + daily_sector_data)
-- 4. 股票的'行业'字段（如：退货、食品、建材）是板块分类，可用于分组分析
-- 5. 但无法与独立的板块数据（工程建设、社区团购等）直接关联
-- ===================================================================
*/

/* -- 步骤 1: 启用 pg_trgm 扩展 (用于高效模糊查询) -- */
CREATE EXTENSION IF NOT EXISTS pg_trgm;

/* -- 步骤 2: 创建 stocks 表 (股票主表)
   -- 数据源：*_data_sma_feature_color.xlsx (股票数据Excel，约3MB)
   -- 目的：存储股票基本信息，消除冗余，支持模糊查询
   -- Excel列映射：
   --   Excel'代码'列 (如: S00161)      → stock_code
   --   Excel'名称'列 (如: 浙元股份)    → stock_name
   --   Excel'行业'列 (如: 退货/食品)   → industry (⚠️ 这是板块分类)
*/
CREATE TABLE IF NOT EXISTS stocks (
    stock_code VARCHAR(10) PRIMARY KEY, -- Excel'代码'列 (股票代码)
    stock_name VARCHAR(50) NOT NULL,   -- Excel'名称'列 (股票名称)
    industry VARCHAR(100),            -- Excel'行业'列 (板块分类，如：退货、食品、建材)
    last_updated TIMESTAMP             -- 股票信息最后更新时间
);

/* -- 步骤 3: 创建 daily_stock_data 表 (全量每日数据表)
   -- 数据源：*_data_sma_feature_color.xlsx (股票数据Excel，约3MB)
   -- 目的：存储 Excel 中的所有83个每日技术指标
   -- [注意] 所有 DECIMAL 类型已设置为 (30, 10) 以防止溢出
   -- Excel列与数据库字段完全对应，详见下方注释
*/
CREATE TABLE IF NOT EXISTS daily_stock_data (
    id BIGSERIAL PRIMARY KEY,  -- 自动递增ID
    
    -- === 关键关联字段 ===
    stock_code VARCHAR(10) NOT NULL REFERENCES stocks(stock_code) ON DELETE CASCADE, -- '代码' (外键)
    date DATE NOT NULL,              -- '日期' (从文件名或'日期'列提取)
    rank INTEGER NOT NULL,           -- 排名 (由 import 脚本的 Excel 行号 'idx + 1' 生成)

    -- === Excel 中所有列 (已转换SQL列名) ===
    total_score DECIMAL(30, 10),      -- '总分'
    open_price DECIMAL(30, 10),       -- '开盘'
    high_price DECIMAL(30, 10),       -- '最高'
    low_price DECIMAL(30, 10),        -- '最低'
    close_price DECIMAL(30, 10),      -- 'close'
    jump DECIMAL(30, 10),             -- 'jump'
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
    market_cap_billions DECIMAL(30, 10), -- '总市值(亿)'
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

/* -- 步骤 4: 创建所有性能索引
*/

/* -- 索引 1: 优化「查询单个股票历史」 (例如 /api/stock/{stock_code}) 
   -- 并且【防止】 (股票代码, 日期) 的数据被重复导入
   -- 这是你的核心约束之一
*/
CREATE UNIQUE INDEX IF NOT EXISTS idx_daily_stock_date_unique 
    ON daily_stock_data (stock_code, date);

/* -- 索引 2: 优化「周期分析」和「行业分析」 (例如 /api/analyze/{period}) 
   -- 极大加速按日期和排名的查询
*/
CREATE INDEX IF NOT EXISTS idx_daily_date_rank 
    ON daily_stock_data (date, rank);

/* -- 索引 3 & 4: 优化 `stocks` 表的模糊查询 (Trigram)
*/
CREATE INDEX IF NOT EXISTS idx_stocks_name_trgm 
    ON stocks USING gin (stock_name gin_trgm_ops);

CREATE INDEX IF NOT EXISTS idx_stocks_code_trgm 
    ON stocks USING gin (stock_code gin_trgm_ops);

/*
-- ===================================================================
-- 脚本执行完毕
-- ===================================================================
*/