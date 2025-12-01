-- =====================================================
-- 用户认证相关表
-- v0.4.0 新增
-- =====================================================

-- 用户表
CREATE TABLE IF NOT EXISTS users (
    id SERIAL PRIMARY KEY,
    username VARCHAR(50) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    user_key_encrypted TEXT NOT NULL,
    
    -- 用户信息
    role VARCHAR(20) DEFAULT 'user',
    is_active BOOLEAN DEFAULT TRUE,
    
    -- 时间戳
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_login TIMESTAMP,
    
    -- 设备和离线配置
    allowed_devices INT DEFAULT 3,
    offline_enabled BOOLEAN DEFAULT TRUE,
    offline_days INT DEFAULT 7
);

-- 用户名索引
CREATE INDEX IF NOT EXISTS idx_users_username ON users(username);

-- 用户会话表
CREATE TABLE IF NOT EXISTS user_sessions (
    id SERIAL PRIMARY KEY,
    user_id INT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    device_id VARCHAR(100) NOT NULL,
    device_name VARCHAR(100),
    
    -- 会话信息
    session_key_encrypted TEXT NOT NULL,
    refresh_token VARCHAR(500),
    
    -- 时间
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP NOT NULL,
    last_active TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    -- 唯一约束：同一用户同一设备只能有一个会话
    UNIQUE(user_id, device_id)
);

-- 会话索引
CREATE INDEX IF NOT EXISTS idx_sessions_user ON user_sessions(user_id);
CREATE INDEX IF NOT EXISTS idx_sessions_expires ON user_sessions(expires_at);

-- =====================================================
-- 注释说明
-- =====================================================
COMMENT ON TABLE users IS '用户表 - 存储用户认证信息';
COMMENT ON COLUMN users.username IS '用户名，唯一';
COMMENT ON COLUMN users.password_hash IS '密码哈希(bcrypt)';
COMMENT ON COLUMN users.user_key_encrypted IS '用户密钥(主密钥加密)';
COMMENT ON COLUMN users.role IS '角色: admin/user';
COMMENT ON COLUMN users.is_active IS '是否启用';
COMMENT ON COLUMN users.allowed_devices IS '允许同时登录设备数';
COMMENT ON COLUMN users.offline_enabled IS '是否允许离线使用';
COMMENT ON COLUMN users.offline_days IS '离线数据保留天数';

COMMENT ON TABLE user_sessions IS '用户会话表 - 管理多设备登录';
COMMENT ON COLUMN user_sessions.device_id IS '设备唯一标识';
COMMENT ON COLUMN user_sessions.session_key_encrypted IS '会话密钥(用户密钥加密)';
COMMENT ON COLUMN user_sessions.refresh_token IS '刷新令牌';
