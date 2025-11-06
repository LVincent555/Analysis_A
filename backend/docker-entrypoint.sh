#!/bin/bash
set -e

echo "==========================================="
echo "Stock Analysis Backend - Starting..."
echo "==========================================="

# 等待数据库就绪
echo "Waiting for PostgreSQL to be ready..."
until PGPASSWORD=$DATABASE_PASSWORD psql -h "$DATABASE_HOST" -U "$DATABASE_USER" -d "$DATABASE_NAME" -c '\q' 2>/dev/null; do
  echo "PostgreSQL is unavailable - sleeping"
  sleep 2
done

echo "PostgreSQL is ready!"

# 检查是否需要导入数据
if [ -z "$(ls -A /app/data/*.xlsx 2>/dev/null)" ]; then
    echo "⚠️  Warning: No Excel files found in /app/data directory"
    echo "Please upload Excel files to /app/data before importing"
else
    echo "📂 Found Excel files in /app/data"
    
    # 检查数据库是否为空
    ROW_COUNT=$(PGPASSWORD=$DATABASE_PASSWORD psql -h "$DATABASE_HOST" -U "$DATABASE_USER" -d "$DATABASE_NAME" -t -c "SELECT COUNT(*) FROM daily_stock_data;" 2>/dev/null || echo "0")
    
    if [ "$ROW_COUNT" -eq "0" ]; then
        echo "🔄 Database is empty. Starting data import..."
        python scripts/import_data_robust.py
        echo "✅ Data import completed"
    else
        echo "✅ Database already contains $ROW_COUNT records"
        echo "Skipping initial import"
    fi
fi

# 清除旧缓存
echo "🧹 Clearing old cache..."
python clear_cache.py || echo "No cache to clear"

echo "🚀 Starting application..."
echo "==========================================="

# 执行传入的命令
exec "$@"
