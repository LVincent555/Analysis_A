-- ==========================================
-- Stock Analysis Database Initialization
-- ==========================================

-- 设置客户端编码
SET client_encoding = 'UTF8';

-- 创建数据库（如果不存在）
-- 注意：这个脚本由docker-entrypoint执行时数据库已存在

-- 创建表的SQL由SQLAlchemy自动管理
-- 这里只做一些初始化配置

-- 配置数据库参数
ALTER DATABASE stock_analysis SET timezone TO 'Asia/Shanghai';

-- 授予权限
GRANT ALL PRIVILEGES ON DATABASE stock_analysis TO stock_user;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO stock_user;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO stock_user;

-- 创建扩展（如果需要）
-- CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- 打印初始化信息
DO $$
BEGIN
    RAISE NOTICE '✅ 数据库初始化完成';
    RAISE NOTICE '📊 数据库名称: stock_analysis';
    RAISE NOTICE '👤 用户: stock_user';
    RAISE NOTICE '🌏 时区: Asia/Shanghai';
END $$;
