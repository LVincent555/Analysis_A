#!/bin/bash
# ==========================================
# Stock Analysis App - 数据备份脚本
# ==========================================

set -e

BACKUP_DIR="./backups"
DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="stock_analysis_backup_${DATE}.sql"

echo "==========================================="
echo "💾 Stock Analysis App - 数据库备份"
echo "==========================================="

# 创建备份目录
mkdir -p $BACKUP_DIR

# 检查容器是否运行
if ! docker-compose ps | grep -q "stock_db.*Up"; then
    echo "❌ 数据库容器未运行！"
    exit 1
fi

echo "📦 开始备份数据库..."
echo "备份文件: ${BACKUP_DIR}/${BACKUP_FILE}"

# 执行备份
docker-compose exec -T postgres pg_dump -U stock_user stock_analysis > "${BACKUP_DIR}/${BACKUP_FILE}"

# 检查备份是否成功
if [ -f "${BACKUP_DIR}/${BACKUP_FILE}" ]; then
    BACKUP_SIZE=$(du -h "${BACKUP_DIR}/${BACKUP_FILE}" | cut -f1)
    echo "✅ 备份成功！"
    echo "   文件大小: ${BACKUP_SIZE}"
    echo "   保存位置: ${BACKUP_DIR}/${BACKUP_FILE}"
    
    # 压缩备份文件
    echo "🗜️  压缩备份文件..."
    gzip "${BACKUP_DIR}/${BACKUP_FILE}"
    COMPRESSED_SIZE=$(du -h "${BACKUP_DIR}/${BACKUP_FILE}.gz" | cut -f1)
    echo "✅ 压缩完成！压缩后大小: ${COMPRESSED_SIZE}"
    
    # 清理旧备份（保留最近5个）
    echo "🧹 清理旧备份（保留最近5个）..."
    ls -t ${BACKUP_DIR}/stock_analysis_backup_*.sql.gz | tail -n +6 | xargs -r rm
    
    echo ""
    echo "==========================================="
    echo "📊 当前备份列表："
    ls -lh ${BACKUP_DIR}/stock_analysis_backup_*.sql.gz 2>/dev/null || echo "无备份文件"
    echo "==========================================="
else
    echo "❌ 备份失败！"
    exit 1
fi

echo ""
echo "💡 恢复备份命令："
echo "   gunzip -c ${BACKUP_DIR}/${BACKUP_FILE}.gz | docker-compose exec -T postgres psql -U stock_user stock_analysis"
