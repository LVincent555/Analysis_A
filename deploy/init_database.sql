-- ==========================================
-- 股票分析系统 - 数据库初始化脚本
-- 适用于Linux本地PostgreSQL部署
-- ==========================================

-- 以postgres用户身份运行此脚本：
-- sudo -u postgres psql < init_database.sql

-- 创建数据库
CREATE DATABASE stock_analysis
    WITH 
    OWNER = postgres
    ENCODING = 'UTF8'
    LC_COLLATE = 'en_US.UTF-8'
    LC_CTYPE = 'en_US.UTF-8'
    TABLESPACE = pg_default
    CONNECTION LIMIT = -1;

-- 连接到新数据库
\c stock_analysis

-- 设置时区
ALTER DATABASE stock_analysis SET timezone TO 'Asia/Shanghai';

-- 创建用户
CREATE USER stock_user WITH PASSWORD 'your_strong_password';

-- 授予权限
GRANT ALL PRIVILEGES ON DATABASE stock_analysis TO stock_user;
GRANT ALL PRIVILEGES ON SCHEMA public TO stock_user;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON TABLES TO stock_user;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON SEQUENCES TO stock_user;

-- 创建扩展（可选）
-- CREATE EXTENSION IF NOT EXISTS "pg_stat_statements";

-- 打印信息
\echo '=========================================='
\echo '✅ 数据库初始化完成'
\echo '=========================================='
\echo '数据库名称: stock_analysis'
\echo '用户名称: stock_user'
\echo '时区: Asia/Shanghai'
\echo ''
\echo '下一步:'
\echo '1. 修改backend/.env配置文件'
\echo '2. 运行: python scripts/import_data_robust.py'
\echo '=========================================='
