#!/bin/bash
# ============================================================
# V0.6.0 多对多数据迁移脚本 - 本地导出
# ============================================================
# 
# 使用方法：在本地虚拟机(192.168.182.128)上执行
# bash export_ext_boards_data.sh
#
# 导出后会生成：ext_boards_data.sql
# 然后传输到服务器执行导入
# ============================================================

set -e

# 配置（根据实际情况修改）
DB_HOST="localhost"     # 本地数据库地址
DB_PORT="5432"
DB_NAME="db_20251106_analysis_a"
DB_USER="postgres"

OUTPUT_FILE="ext_boards_data.sql"

echo "============================================================"
echo "📦 V0.6.0 多对多数据导出"
echo "============================================================"
echo ""
echo "📍 数据库: $DB_HOST:$DB_PORT/$DB_NAME"
echo "📄 输出文件: $OUTPUT_FILE"
echo ""

# 检查表数据量
echo "📊 当前数据量："
psql -h $DB_HOST -p $DB_PORT -U $DB_USER -d $DB_NAME -t -c "
SELECT 'ext_providers' AS t, COUNT(*) FROM ext_providers
UNION ALL SELECT 'ext_board_list', COUNT(*) FROM ext_board_list
UNION ALL SELECT 'ext_board_daily_snap', COUNT(*) FROM ext_board_daily_snap
UNION ALL SELECT 'ext_board_heat_daily', COUNT(*) FROM ext_board_heat_daily
UNION ALL SELECT 'ext_board_local_map', COUNT(*) FROM ext_board_local_map
UNION ALL SELECT 'board_blacklist', COUNT(*) FROM board_blacklist
UNION ALL SELECT 'cache_stock_board_signal', COUNT(*) FROM cache_stock_board_signal
ORDER BY t;
"
echo ""

# 导出数据（只导出数据，不含表结构）
echo "🔄 正在导出数据..."
pg_dump -h $DB_HOST -p $DB_PORT -U $DB_USER -d $DB_NAME \
    --data-only \
    --no-owner \
    --no-privileges \
    --disable-triggers \
    --table=ext_providers \
    --table=ext_board_list \
    --table=ext_board_daily_snap \
    --table=ext_board_heat_daily \
    --table=ext_board_local_map \
    --table=board_blacklist \
    --table=cache_stock_board_signal \
    > $OUTPUT_FILE

# 添加序列重置命令到文件末尾
echo "" >> $OUTPUT_FILE
echo "-- 重置序列值" >> $OUTPUT_FILE
echo "SELECT setval('ext_providers_id_seq', COALESCE((SELECT MAX(id) FROM ext_providers), 1));" >> $OUTPUT_FILE
echo "SELECT setval('ext_board_list_id_seq', COALESCE((SELECT MAX(id) FROM ext_board_list), 1));" >> $OUTPUT_FILE
echo "SELECT setval('board_blacklist_id_seq', COALESCE((SELECT MAX(id) FROM board_blacklist), 1));" >> $OUTPUT_FILE

# 显示结果
FILE_SIZE=$(du -h $OUTPUT_FILE | cut -f1)
LINE_COUNT=$(wc -l < $OUTPUT_FILE)

echo ""
echo "✅ 导出完成！"
echo "   文件: $OUTPUT_FILE"
echo "   大小: $FILE_SIZE"
echo "   行数: $LINE_COUNT"
echo ""
echo "============================================================"
echo "📋 下一步操作："
echo "============================================================"
echo ""
echo "1. 传输文件到服务器："
echo "   scp $OUTPUT_FILE user@服务器IP:/tmp/"
echo ""
echo "2. 在服务器上导入数据："
echo "   psql -U postgres -d $DB_NAME -f /tmp/$OUTPUT_FILE"
echo ""
echo "3. 验证数据："
echo "   psql -U postgres -d $DB_NAME -c \"SELECT 'ext_board_list', COUNT(*) FROM ext_board_list;\""
echo ""
