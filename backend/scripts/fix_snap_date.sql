-- 修复 ext_board_daily_snap 中非交易日的快照日期
-- 将 2025-12-13（周六）的快照改为 2025-12-12（周五，最近交易日）

-- 1. 查看当前快照日期分布
SELECT date, COUNT(*) as cnt 
FROM ext_board_daily_snap 
GROUP BY date 
ORDER BY date DESC;

-- 2. 修复：将 12-13 改为 12-12
UPDATE ext_board_daily_snap 
SET date = '2025-12-12'::date 
WHERE date = '2025-12-13'::date;

-- 3. 验证修复结果
SELECT date, COUNT(*) as cnt 
FROM ext_board_daily_snap 
GROUP BY date 
ORDER BY date DESC;
