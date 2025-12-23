-- ============================================================
-- 系统管理模块 - 完整表结构（全新安装用）
-- 版本: v1.1.0
-- 日期: 2025-12-05
-- 说明: 包含用户、会话、日志、配置、角色权限等所有系统管理表
-- 
-- 文件组织:
--   users.sql - 本文件，全新安装使用
--   upgrade_users_v1.1.sql - 从旧版本升级使用
-- ============================================================

-- ============================================================
-- 1. Users 表（完整版）
-- ============================================================
CREATE TABLE IF NOT EXISTS users (
    id SERIAL PRIMARY KEY,
    username VARCHAR(50) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    user_key_encrypted TEXT NOT NULL,
    
    -- 用户信息
    email VARCHAR(255),
    phone VARCHAR(20),
    nickname VARCHAR(50),
    avatar_url VARCHAR(500),
    remark TEXT,
    
    -- 角色和状态
    role VARCHAR(20) DEFAULT 'user',
    is_active BOOLEAN DEFAULT TRUE,
    
    -- 时间戳
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_login TIMESTAMP,
    
    -- 账号有效期
    expires_at TIMESTAMP,
    
    -- 登录安全
    failed_attempts INT DEFAULT 0,
    locked_until TIMESTAMP,
    password_changed_at TIMESTAMP,
    
    -- 设备和离线配置
    allowed_devices INT DEFAULT 3,
    offline_enabled BOOLEAN DEFAULT TRUE,
    offline_days INT DEFAULT 7,
    
    -- 审计字段
    created_by INT,
    deleted_at TIMESTAMP,
    
    -- 强制下线用
    token_version INT DEFAULT 1
);

-- Users 表索引
CREATE INDEX IF NOT EXISTS idx_users_username ON users(username);
CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);
CREATE INDEX IF NOT EXISTS idx_users_is_active ON users(is_active);
CREATE INDEX IF NOT EXISTS idx_users_role ON users(role);
CREATE INDEX IF NOT EXISTS idx_users_deleted_at ON users(deleted_at);

-- ============================================================
-- 2. UserSessions 表（完整版）
-- ============================================================
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
    
    -- 设备详情
    ip_address VARCHAR(45),
    user_agent VARCHAR(500),
    platform VARCHAR(50),
    app_version VARCHAR(20),
    location VARCHAR(100),
    device_info JSONB,
    
    -- 状态
    current_status VARCHAR(20) DEFAULT 'online',
    
    -- 撤销/强制下线
    is_revoked BOOLEAN DEFAULT FALSE,
    revoked_at TIMESTAMP,
    revoked_by INT,
    
    -- 唯一约束
    CONSTRAINT idx_user_device_unique UNIQUE (user_id, device_id)
);

-- UserSessions 表索引
CREATE INDEX IF NOT EXISTS idx_sessions_user_id ON user_sessions(user_id);
CREATE INDEX IF NOT EXISTS idx_sessions_is_revoked ON user_sessions(is_revoked);
CREATE INDEX IF NOT EXISTS idx_sessions_last_active ON user_sessions(last_active);
CREATE INDEX IF NOT EXISTS idx_sessions_current_status ON user_sessions(current_status);
CREATE INDEX IF NOT EXISTS idx_sessions_expires_at ON user_sessions(expires_at);

-- ============================================================
-- 3. OperationLogs 表（操作日志）
-- ============================================================
CREATE TABLE IF NOT EXISTS operation_logs (
    id SERIAL PRIMARY KEY,
    log_type VARCHAR(20) NOT NULL,           -- LOGIN/USER/SESSION/SECURITY/SYSTEM
    action VARCHAR(50) NOT NULL,             -- login_success/user_create/...
    
    operator_id INT,                         -- 操作者ID（null=系统）
    operator_name VARCHAR(50),               -- 操作者用户名
    
    target_type VARCHAR(20),                 -- user/session/config
    target_id INT,
    target_name VARCHAR(100),
    
    ip_address VARCHAR(45),
    user_agent VARCHAR(500),
    
    detail JSONB,                            -- 详细信息
    old_value JSONB,                         -- 修改前的值（变更审计）
    new_value JSONB,                         -- 修改后的值（变更审计）
    status VARCHAR(20) DEFAULT 'success',    -- success/failed
    error_message TEXT,
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- OperationLogs 表索引
CREATE INDEX IF NOT EXISTS idx_logs_log_type ON operation_logs(log_type);
CREATE INDEX IF NOT EXISTS idx_logs_action ON operation_logs(action);
CREATE INDEX IF NOT EXISTS idx_logs_operator_id ON operation_logs(operator_id);
CREATE INDEX IF NOT EXISTS idx_logs_target ON operation_logs(target_type, target_id);
CREATE INDEX IF NOT EXISTS idx_logs_created_at ON operation_logs(created_at);
CREATE INDEX IF NOT EXISTS idx_logs_status ON operation_logs(status);

-- ============================================================
-- 4. SystemConfigs 表（系统配置）
-- ============================================================
CREATE TABLE IF NOT EXISTS system_configs (
    id SERIAL PRIMARY KEY,
    config_key VARCHAR(100) UNIQUE NOT NULL,
    config_value TEXT NOT NULL,
    config_type VARCHAR(20) DEFAULT 'string',  -- string/int/bool/json
    category VARCHAR(50) NOT NULL,             -- password/login/session/system
    description VARCHAR(255),
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_by INT
);

-- 初始化默认配置
INSERT INTO system_configs (config_key, config_value, config_type, category, description) VALUES
-- 密码策略
('password_min_length', '6', 'int', 'password', '密码最小长度'),
('password_max_length', '100', 'int', 'password', '密码最大长度'),
('password_require_digit', 'false', 'bool', 'password', '要求包含数字'),
('password_require_upper', 'false', 'bool', 'password', '要求包含大写字母'),
('password_require_lower', 'false', 'bool', 'password', '要求包含小写字母'),
('password_require_special', 'false', 'bool', 'password', '要求包含特殊字符'),
('password_expire_days', '0', 'int', 'password', '密码过期天数，0=不过期'),

-- 登录策略
('login_max_attempts', '5', 'int', 'login', '最大失败尝试次数'),
('login_lockout_minutes', '30', 'int', 'login', '锁定时长（分钟）'),
('login_attempt_reset_minutes', '60', 'int', 'login', '失败计数重置时间'),
('login_captcha_enabled', 'false', 'bool', 'login', '启用验证码'),
('login_captcha_threshold', '3', 'int', 'login', '验证码触发次数'),

-- 会话策略
('session_access_token_hours', '24', 'int', 'session', 'Access Token有效期（小时）'),
('session_refresh_token_days', '7', 'int', 'session', 'Refresh Token有效期（天）'),
('session_max_devices', '3', 'int', 'session', '默认最大设备数'),
('session_idle_timeout_minutes', '30', 'int', 'session', '空闲超时（分钟）'),
('session_single_device', 'false', 'bool', 'session', '单设备登录限制')
ON CONFLICT (config_key) DO NOTHING;

-- ============================================================
-- 5. Roles 表（角色）
-- ============================================================
CREATE TABLE IF NOT EXISTS roles (
    id SERIAL PRIMARY KEY,
    name VARCHAR(50) UNIQUE NOT NULL,           -- 角色代码 (admin/user/readonly)
    display_name VARCHAR(100) NOT NULL,         -- 显示名称
    description VARCHAR(255),                   -- 描述
    permissions JSONB NOT NULL DEFAULT '[]',    -- 权限列表
    is_system BOOLEAN DEFAULT FALSE,            -- 是否系统预设（不可删除）
    is_active BOOLEAN DEFAULT TRUE,             -- 是否启用
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Roles 表索引
CREATE INDEX IF NOT EXISTS idx_roles_name ON roles(name);
CREATE INDEX IF NOT EXISTS idx_roles_is_active ON roles(is_active);

-- ============================================================
-- 6. UserRoles 表（用户角色关联，多对多）
-- ============================================================
CREATE TABLE IF NOT EXISTS user_roles (
    user_id INT REFERENCES users(id) ON DELETE CASCADE,
    role_id INT REFERENCES roles(id) ON DELETE CASCADE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (user_id, role_id)
);

-- UserRoles 表索引
CREATE INDEX IF NOT EXISTS idx_user_roles_user_id ON user_roles(user_id);
CREATE INDEX IF NOT EXISTS idx_user_roles_role_id ON user_roles(role_id);

-- 初始化预设角色
INSERT INTO roles (name, display_name, description, permissions, is_system) VALUES
(
    'super_admin',
    '超级管理员',
    '拥有所有权限，不可删除',
    '["*"]',
    true
),
(
    'admin',
    '管理员',
    '用户管理、系统管理、数据分析',
    '["user:*", "session:*", "log:*", "config:*", "analysis:*", "query:*", "data:view", "data:import"]',
    true
),
(
    'user',
    '普通用户',
    '数据分析功能',
    '["analysis:*", "query:*"]',
    true
),
(
    'readonly',
    '只读用户',
    '仅查看权限',
    '["analysis:hotspot", "analysis:industry", "query:stock"]',
    true
)
ON CONFLICT (name) DO UPDATE SET
    display_name = EXCLUDED.display_name,
    description = EXCLUDED.description,
    permissions = EXCLUDED.permissions;

-- ============================================================
-- 注释说明
-- ============================================================
COMMENT ON TABLE users IS '用户表 - 存储用户认证信息 (v1.1.0)';
COMMENT ON COLUMN users.username IS '用户名，唯一';
COMMENT ON COLUMN users.password_hash IS '密码哈希(bcrypt)';
COMMENT ON COLUMN users.user_key_encrypted IS '用户密钥(主密钥加密)';
COMMENT ON COLUMN users.role IS '角色: admin/user (兼容旧版，新版使用 user_roles)';
COMMENT ON COLUMN users.is_active IS '是否启用';
COMMENT ON COLUMN users.token_version IS '令牌版本号，强制下线时递增';
COMMENT ON COLUMN users.failed_attempts IS '连续登录失败次数';
COMMENT ON COLUMN users.locked_until IS '账号锁定截止时间';

COMMENT ON TABLE user_sessions IS '用户会话表 - 管理多设备登录 (v1.1.0)';
COMMENT ON COLUMN user_sessions.device_id IS '设备唯一标识';
COMMENT ON COLUMN user_sessions.session_key_encrypted IS '会话密钥(用户密钥加密)';
COMMENT ON COLUMN user_sessions.current_status IS '当前状态: online/offline/idle';
COMMENT ON COLUMN user_sessions.is_revoked IS '是否已撤销（强制下线）';

COMMENT ON TABLE operation_logs IS '操作日志表 - 记录所有操作';
COMMENT ON TABLE system_configs IS '系统配置表 - 存储系统参数';
COMMENT ON TABLE roles IS '角色表 - 定义角色和权限';
COMMENT ON TABLE user_roles IS '用户角色关联表 - 多对多关系';

-- ============================================================
-- 完成
-- ============================================================
-- 执行完成后，请验证：
-- SELECT COUNT(*) FROM users;
-- SELECT COUNT(*) FROM user_sessions;
-- SELECT COUNT(*) FROM operation_logs;
-- SELECT COUNT(*) FROM system_configs;
-- SELECT COUNT(*) FROM roles;
-- SELECT COUNT(*) FROM user_roles;
