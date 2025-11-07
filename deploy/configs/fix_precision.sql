/*
修复字段精度问题
某些字段的值超过了 DECIMAL(18,10) 的范围
需要调整为 DECIMAL(20,6) 或更大
*/

-- 修改容易溢出的大数值字段
ALTER TABLE daily_stock_data 
    ALTER COLUMN volume_days TYPE DECIMAL(20, 6),
    ALTER COLUMN volume_days_volume TYPE DECIMAL(25, 6),
    ALTER COLUMN avg_volume_ratio_50_volume TYPE DECIMAL(25, 6),
    ALTER COLUMN lon_0 TYPE DECIMAL(20, 6),
    ALTER COLUMN lonma_0 TYPE DECIMAL(20, 6),
    ALTER COLUMN lon_lonma TYPE DECIMAL(20, 6),
    ALTER COLUMN lon_lonma_diff TYPE DECIMAL(20, 6),
    ALTER COLUMN lon TYPE DECIMAL(20, 6),
    ALTER COLUMN lonma TYPE DECIMAL(20, 6),
    ALTER COLUMN volume_consec2 TYPE DECIMAL(25, 6),
    ALTER COLUMN volume_50_consec2 TYPE DECIMAL(25, 6);

-- 验证修改
SELECT column_name, data_type, numeric_precision, numeric_scale
FROM information_schema.columns
WHERE table_name = 'daily_stock_data' 
  AND column_name IN ('volume_days_volume', 'lon_0', 'lonma_0')
ORDER BY column_name;
