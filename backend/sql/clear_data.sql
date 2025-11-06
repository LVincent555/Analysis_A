/*
清空数据库所有数据并重置序列
保留表结构
*/

-- 方式1：清空所有数据并重置自增序列（推荐）
TRUNCATE TABLE daily_stock_data RESTART IDENTITY CASCADE;
TRUNCATE TABLE stocks RESTART IDENTITY CASCADE;

-- 方式2：手动重置序列（备选）
-- ALTER SEQUENCE daily_stock_data_id_seq RESTART WITH 1;

-- 方式3：删除所有数据（慢，不推荐）
-- DELETE FROM daily_stock_data;
-- DELETE FROM stocks;
-- ALTER SEQUENCE daily_stock_data_id_seq RESTART WITH 1;

-- 验证清空结果
SELECT 
    'stocks' as table_name, 
    COUNT(*) as row_count 
FROM stocks
UNION ALL
SELECT 
    'daily_stock_data' as table_name, 
    COUNT(*) as row_count 
FROM daily_stock_data;
